"""
MediScanAI — Phase 3.2: Standalone Neo4j Graph Retriever.

Provides standalone, read-only graph retrieval for drug products, active ingredients,
disease profiles, and symptoms using the existing Neo4j driver and schema.

Operates independently of FAISS/BM25 and gracefully handles disabled, offline,
or timed-out database states.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from neo4j import Driver, exceptions as neo4j_exceptions

from backend.core.config import Settings, get_settings
from app.graph.driver import get_neo4j_driver

logger = logging.getLogger("mediscanai.graph.retriever")


# ==============================================================================
# Data Transfer Objects (DTOs)
# ==============================================================================

@dataclass(frozen=True)
class DiseaseChunkProvenance:
    """Atomic pairing of chunk identifier and its source JSONL line index."""
    chunk_id: str
    source_id: int


@dataclass(frozen=True)
class DrugGraphResult:
    """Represents a drug product and its active ingredients with source provenance."""
    source_id: int
    brand_name: Optional[str]
    generic_name: Optional[str]
    active_ingredients: List[str]
    indications_text: Optional[str]
    warnings_text: Optional[str]
    dosage_text: Optional[str]
    adverse_reactions_text: Optional[str]
    match_field: str  # "brand_name" | "generic_name" | "ingredient"
    provenance: Dict[str, Any]


@dataclass(frozen=True)
class DiseaseGraphResult:
    """Represents a disease entity with symptom overlap and paired chunk provenance."""
    disease_name: str
    matched_symptoms: List[str]
    all_symptoms: List[str]
    overlap_count: int
    chunks: List[DiseaseChunkProvenance]
    provenance: Dict[str, Any]


@dataclass
class GraphRetrievalResponse:
    """Standardized response container for all graph retrieval calls."""
    drugs: List[DrugGraphResult] = field(default_factory=list)
    diseases: List[DiseaseGraphResult] = field(default_factory=list)
    status: str = "success"  # "success" | "empty" | "disabled" | "timeout" | "error"
    latency_ms: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ==============================================================================
# Input Normalization & Bounding Helpers
# ==============================================================================

def normalize_name_variants(name: str, max_chars: int = 256) -> List[str]:
    """
    Produces a bounded, deterministic list of casing variants for index seek lookups.
    Note: Multi-variant matching supports common variations (exact, upper, title, lower)
    without full table scans, but does not guarantee matching for irregular mixed-case
    drugs (e.g. 'Mucinex DM', 'pHisoHex') unless queried with the matching casing.
    """
    if not name or not isinstance(name, str):
        return []
    clean_name = " ".join(str(name).strip().split())[:max_chars]
    if not clean_name:
        return []

    return list(dict.fromkeys([
        clean_name,
        clean_name.upper(),
        clean_name.title(),
        clean_name.lower(),
    ]))


def normalize_ingredient_name(name: str, max_chars: int = 256) -> str:
    """Normalizes an ingredient name to uppercase matching ActiveIngredient.name convention."""
    if not name or not isinstance(name, str):
        return ""
    clean = " ".join(str(name).strip().split())[:max_chars]
    return clean.upper()


def normalize_symptoms(raw_symptoms: List[str], max_symptoms: int = 20, max_chars_per_item: int = 100) -> List[str]:
    """
    Normalizes symptoms strictly matching graph ingestion:
    lowercased, collapsed whitespace, deduplicated, and bounded.
    """
    if not raw_symptoms or not isinstance(raw_symptoms, (list, tuple)):
        return []

    cleaned: List[str] = []
    for s in raw_symptoms:
        if s is None:
            continue
        item = " ".join(str(s).strip().split()).lower()[:max_chars_per_item]
        if item and item not in cleaned:
            cleaned.append(item)
        if len(cleaned) >= max_symptoms:
            break

    return cleaned


def clamp_bound(val: Any, min_val: int, max_val: int, default: int) -> int:
    """Safely coerces and clamps integer bounds."""
    try:
        ival = int(val)
        return max(min_val, min(max_val, ival))
    except (ValueError, TypeError):
        return default


# ==============================================================================
# Parameterized Cypher Queries (Read-Only)
# ==============================================================================

CYPHER_FIND_DRUGS_BY_NAME = """
MATCH (d:DrugProduct)
WHERE d.brand_name IN $variants OR d.generic_name IN $variants
OPTIONAL MATCH (d)-[:CONTAINS_INGREDIENT]->(i:ActiveIngredient)
RETURN d.source_id AS source_id,
       d.brand_name AS brand_name,
       d.generic_name AS generic_name,
       d.indications_text AS indications_text,
       d.warnings_text AS warnings_text,
       d.dosage_text AS dosage_text,
       d.adverse_reactions_text AS adverse_reactions_text,
       collect(DISTINCT i.name) AS active_ingredients,
       CASE
           WHEN d.brand_name IN $variants THEN 'brand_name'
           ELSE 'generic_name'
       END AS match_field
ORDER BY d.source_id ASC
LIMIT $limit
"""

CYPHER_FIND_DRUGS_BY_INGREDIENT = """
MATCH (i:ActiveIngredient {name: $ingredient_name})
MATCH (d:DrugProduct)-[:CONTAINS_INGREDIENT]->(i)
OPTIONAL MATCH (d)-[:CONTAINS_INGREDIENT]->(all_i:ActiveIngredient)
RETURN d.source_id AS source_id,
       d.brand_name AS brand_name,
       d.generic_name AS generic_name,
       d.indications_text AS indications_text,
       d.warnings_text AS warnings_text,
       d.dosage_text AS dosage_text,
       d.adverse_reactions_text AS adverse_reactions_text,
       collect(DISTINCT all_i.name) AS active_ingredients,
       'ingredient' AS match_field
ORDER BY d.source_id ASC
LIMIT $limit
"""

CYPHER_FIND_DISEASES_BY_SYMPTOMS = """
MATCH (s:Symptom)
WHERE s.name IN $normalized_symptoms
MATCH (d:Disease)-[:PRESENTS_SYMPTOM]->(s)
WITH d, count(DISTINCT s.name) AS overlap_count, collect(DISTINCT s.name) AS matched_symptoms
ORDER BY overlap_count DESC, d.name ASC
LIMIT $limit

OPTIONAL MATCH (c:DiseaseChunk)-[:DESCRIBES_DISEASE]->(d)
WITH d, overlap_count, matched_symptoms, c
ORDER BY c.source_id ASC, c.chunk_id ASC
WITH d, overlap_count, matched_symptoms,
     [chunk IN collect(DISTINCT CASE WHEN c IS NOT NULL THEN {chunk_id: c.chunk_id, source_id: c.source_id} END) WHERE chunk IS NOT NULL][0..$max_chunks] AS chunks
OPTIONAL MATCH (d)-[:PRESENTS_SYMPTOM]->(all_s:Symptom)
RETURN d.name AS disease_name,
       overlap_count,
       matched_symptoms,
       collect(DISTINCT all_s.name) AS all_symptoms,
       chunks
ORDER BY overlap_count DESC, d.name ASC
"""

CYPHER_GET_DISEASE_NEIGHBORHOOD = """
MATCH (d:Disease)
WHERE d.name IN $variants
OPTIONAL MATCH (c:DiseaseChunk)-[:DESCRIBES_DISEASE]->(d)
WITH d, c
ORDER BY c.source_id ASC, c.chunk_id ASC
WITH d,
     [chunk IN collect(DISTINCT CASE WHEN c IS NOT NULL THEN {chunk_id: c.chunk_id, source_id: c.source_id} END) WHERE chunk IS NOT NULL][0..$max_chunks] AS chunks
OPTIONAL MATCH (d)-[:PRESENTS_SYMPTOM]->(all_s:Symptom)
RETURN d.name AS disease_name,
       collect(DISTINCT all_s.name) AS all_symptoms,
       chunks
ORDER BY d.name ASC
LIMIT 1
"""


# ==============================================================================
# Standalone Graph Retriever
# ==============================================================================

class GraphRetriever:
    """
    Standalone graph retriever executing read-only parameterized queries against Neo4j.
    Guarantees thread-isolated sessions, transaction timeouts, and graceful fallbacks.
    """

    def __init__(
        self,
        driver: Optional[Driver] = None,
        settings: Optional[Settings] = None,
        query_timeout_seconds: float = 2.0,
    ):
        self._custom_driver = driver
        self._settings = settings or get_settings()
        self.query_timeout_seconds = query_timeout_seconds

    def _get_driver(self) -> Optional[Driver]:
        """Returns the configured or global Neo4j driver, or None if disabled."""
        if self._custom_driver is not None:
            return self._custom_driver
        if not self._settings.NEO4J_ENABLED:
            return None
        return get_neo4j_driver(self._settings)

    def _execute_query(
        self,
        query: str,
        params: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], str, Optional[str], Optional[str], int]:
        """
        Executes a read query in an explicit, unmanaged single-attempt transaction with a timeout.
        Returns: (records, status, error_code, error_message, latency_ms)
        """
        driver = self._get_driver()
        if driver is None:
            return [], "disabled", None, None, 0

        t0 = time.perf_counter()
        session = None
        try:
            session = driver.session()
            with session.begin_transaction(timeout=self.query_timeout_seconds) as tx:
                result = tx.run(query, params)
                records: List[Dict[str, Any]] = []
                for record in result:
                    if hasattr(record, "data") and callable(record.data):
                        records.append(record.data())
                    elif isinstance(record, dict):
                        records.append(record)
                    else:
                        records.append(dict(record))

            latency_ms = int((time.perf_counter() - t0) * 1000)
            status = "success" if records else "empty"
            return records, status, None, None, latency_ms

        except neo4j_exceptions.AuthError as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("Neo4j authentication error: %s", exc)
            return [], "error", "AUTHENTICATION_FAILED", "Neo4j authentication failed.", latency_ms

        except neo4j_exceptions.ServiceUnavailable as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("Neo4j service unavailable (%dms): %s", latency_ms, exc)
            return [], "error", "DATABASE_UNAVAILABLE", "Neo4j service is unreachable.", latency_ms

        except neo4j_exceptions.ClientError as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            err_code_str = str(getattr(exc, "code", "") or "")
            if "Timeout" in err_code_str or "TransactionTimedOut" in str(exc):
                logger.warning("Neo4j transaction timed out (%dms): %s", latency_ms, exc)
                return [], "timeout", "QUERY_TIMEOUT", "Neo4j query execution exceeded transaction timeout.", latency_ms
            logger.warning("Neo4j client error (%dms): %s", latency_ms, exc)
            return [], "error", "DATABASE_ERROR", f"Database client error: {type(exc).__name__}", latency_ms

        except (neo4j_exceptions.DriverError, neo4j_exceptions.Neo4jError) as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("Neo4j database error (%dms): %s", latency_ms, exc)
            return [], "error", "DATABASE_ERROR", f"Database error: {type(exc).__name__}", latency_ms

        finally:
            if session is not None:
                try:
                    session.close()
                except Exception as close_exc:
                    logger.debug("Error closing session: %s", close_exc)

    def find_drugs_by_name(self, name: str, limit: int = 5) -> GraphRetrievalResponse:
        """Looks up DrugProduct nodes matching brand_name or generic_name using index seeks."""
        variants = normalize_name_variants(name)
        if not variants:
            return GraphRetrievalResponse(status="empty")

        clamped_limit = clamp_bound(limit, min_val=1, max_val=20, default=5)
        params = {"variants": variants, "limit": clamped_limit}

        records, status, err_code, err_msg, latency_ms = self._execute_query(
            CYPHER_FIND_DRUGS_BY_NAME, params
        )

        if status not in ("success", "empty"):
            return GraphRetrievalResponse(
                status=status,
                latency_ms=latency_ms,
                error_code=err_code,
                error_message=err_msg,
            )

        drugs: List[DrugGraphResult] = []
        for r in records:
            drugs.append(
                DrugGraphResult(
                    source_id=int(r["source_id"]),
                    brand_name=r.get("brand_name"),
                    generic_name=r.get("generic_name"),
                    active_ingredients=list(r.get("active_ingredients") or []),
                    indications_text=r.get("indications_text"),
                    warnings_text=r.get("warnings_text"),
                    dosage_text=r.get("dosage_text"),
                    adverse_reactions_text=r.get("adverse_reactions_text"),
                    match_field=str(r.get("match_field", "brand_name")),
                    provenance={"entity": "DrugProduct", "source_id": int(r["source_id"])},
                )
            )

        final_status = "success" if drugs else "empty"
        return GraphRetrievalResponse(
            drugs=drugs,
            status=final_status,
            latency_ms=latency_ms,
        )

    def find_drugs_by_ingredient(self, ingredient_name: str, limit: int = 5) -> GraphRetrievalResponse:
        """Looks up DrugProduct nodes containing a normalized active ingredient."""
        clean_ingredient = normalize_ingredient_name(ingredient_name)
        if not clean_ingredient:
            return GraphRetrievalResponse(status="empty")

        clamped_limit = clamp_bound(limit, min_val=1, max_val=20, default=5)
        params = {"ingredient_name": clean_ingredient, "limit": clamped_limit}

        records, status, err_code, err_msg, latency_ms = self._execute_query(
            CYPHER_FIND_DRUGS_BY_INGREDIENT, params
        )

        if status not in ("success", "empty"):
            return GraphRetrievalResponse(
                status=status,
                latency_ms=latency_ms,
                error_code=err_code,
                error_message=err_msg,
            )

        drugs: List[DrugGraphResult] = []
        for r in records:
            drugs.append(
                DrugGraphResult(
                    source_id=int(r["source_id"]),
                    brand_name=r.get("brand_name"),
                    generic_name=r.get("generic_name"),
                    active_ingredients=list(r.get("active_ingredients") or []),
                    indications_text=r.get("indications_text"),
                    warnings_text=r.get("warnings_text"),
                    dosage_text=r.get("dosage_text"),
                    adverse_reactions_text=r.get("adverse_reactions_text"),
                    match_field="ingredient",
                    provenance={"entity": "DrugProduct", "source_id": int(r["source_id"])},
                )
            )

        final_status = "success" if drugs else "empty"
        return GraphRetrievalResponse(
            drugs=drugs,
            status=final_status,
            latency_ms=latency_ms,
        )

    def find_diseases_by_symptoms(
        self,
        symptoms: List[str],
        limit: int = 5,
        max_chunks_per_disease: int = 3,
    ) -> GraphRetrievalResponse:
        """Finds candidate diseases matching normalized symptoms, ranked by overlap count."""
        normalized = normalize_symptoms(symptoms, max_symptoms=20)
        if not normalized:
            return GraphRetrievalResponse(status="empty")

        clamped_limit = clamp_bound(limit, min_val=1, max_val=20, default=5)
        clamped_chunks = clamp_bound(max_chunks_per_disease, min_val=1, max_val=5, default=3)

        params = {
            "normalized_symptoms": normalized,
            "limit": clamped_limit,
            "max_chunks": clamped_chunks,
        }

        records, status, err_code, err_msg, latency_ms = self._execute_query(
            CYPHER_FIND_DISEASES_BY_SYMPTOMS, params
        )

        if status not in ("success", "empty"):
            return GraphRetrievalResponse(
                status=status,
                latency_ms=latency_ms,
                error_code=err_code,
                error_message=err_msg,
            )

        diseases: List[DiseaseGraphResult] = []
        for r in records:
            raw_chunks = r.get("chunks") or []
            chunks: List[DiseaseChunkProvenance] = []
            for c in raw_chunks:
                if isinstance(c, dict) and c.get("chunk_id") is not None and c.get("source_id") is not None:
                    chunks.append(
                        DiseaseChunkProvenance(
                            chunk_id=str(c["chunk_id"]),
                            source_id=int(c["source_id"]),
                        )
                    )

            disease_name = str(r["disease_name"])
            diseases.append(
                DiseaseGraphResult(
                    disease_name=disease_name,
                    matched_symptoms=list(r.get("matched_symptoms") or []),
                    all_symptoms=list(r.get("all_symptoms") or []),
                    overlap_count=int(r.get("overlap_count", 0)),
                    chunks=chunks,
                    provenance={"entity": "Disease", "disease_name": disease_name, "chunk_count": len(chunks)},
                )
            )

        final_status = "success" if diseases else "empty"
        return GraphRetrievalResponse(
            diseases=diseases,
            status=final_status,
            latency_ms=latency_ms,
        )

    def get_disease_neighborhood(
        self,
        disease_name: str,
        max_chunks: int = 3,
    ) -> GraphRetrievalResponse:
        """Retrieves canonical disease profile, all presenting symptoms, and paired chunk IDs."""
        variants = normalize_name_variants(disease_name)
        if not variants:
            return GraphRetrievalResponse(status="empty")

        clamped_chunks = clamp_bound(max_chunks, min_val=1, max_val=5, default=3)
        params = {"variants": variants, "max_chunks": clamped_chunks}

        records, status, err_code, err_msg, latency_ms = self._execute_query(
            CYPHER_GET_DISEASE_NEIGHBORHOOD, params
        )

        if status not in ("success", "empty"):
            return GraphRetrievalResponse(
                status=status,
                latency_ms=latency_ms,
                error_code=err_code,
                error_message=err_msg,
            )

        if not records:
            return GraphRetrievalResponse(status="empty", latency_ms=latency_ms)

        r = records[0]
        raw_chunks = r.get("chunks") or []
        chunks: List[DiseaseChunkProvenance] = []
        for c in raw_chunks:
            if isinstance(c, dict) and c.get("chunk_id") is not None and c.get("source_id") is not None:
                chunks.append(
                    DiseaseChunkProvenance(
                        chunk_id=str(c["chunk_id"]),
                        source_id=int(c["source_id"]),
                    )
                )

        d_name = str(r["disease_name"])
        disease = DiseaseGraphResult(
            disease_name=d_name,
            matched_symptoms=[],
            all_symptoms=list(r.get("all_symptoms") or []),
            overlap_count=0,
            chunks=chunks,
            provenance={"entity": "Disease", "disease_name": d_name, "chunk_count": len(chunks)},
        )

        return GraphRetrievalResponse(
            diseases=[disease],
            status="success",
            latency_ms=latency_ms,
        )
