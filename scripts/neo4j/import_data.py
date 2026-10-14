#!/usr/bin/env python3
"""
MediScanAI — Phase 2.3: Batched, Idempotent Neo4j Importer.

Imports approved datasets:
  - data/drugs_faiss_data.jsonl    -> (:DrugProduct), (:ActiveIngredient), [:CONTAINS_INGREDIENT]
  - data/diseases_faiss_data.jsonl -> (:DiseaseChunk), (:Disease), (:Symptom),
                                      [:DESCRIBES_DISEASE], [:REPORTS_SYMPTOM], [:PRESENTS_SYMPTOM]

Exclusions:
  - data/drug_dict_faiss_data.jsonl is retained exclusively in FAISS/BM25 and is NOT imported.
  - entity_resolution/ is completely excluded.

Usage:
    python scripts/neo4j/import_data.py [--dry-run] [--batch-size 1000] [--target {all,drugs,diseases}]
"""

import sys
import os
import argparse
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Tuple

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.core.config import get_settings, Settings
from app.graph.driver import (
    get_neo4j_driver,
    verify_neo4j_connectivity,
    close_neo4j_driver,
)

logger = logging.getLogger("mediscanai.graph.importer")

DATA_DIR = BASE_DIR / "data"
DRUGS_FILE = DATA_DIR / "drugs_faiss_data.jsonl"
DISEASES_FILE = DATA_DIR / "diseases_faiss_data.jsonl"

PLACEHOLDERS_SET = {
    "none",
    "n/a",
    "not applicable",
    "not available",
    "unknown",
    "null",
    ".",
    "-",
}

# ==============================================================================
# Cypher Ingestion Templates (Idempotent UNWIND Batches)
# ==============================================================================

CYPHER_IMPORT_DRUGS = """
UNWIND $products AS row
MERGE (d:DrugProduct {source_id: row.source_id})
ON CREATE SET
    d.brand_name = row.brand_name,
    d.generic_name = row.generic_name,
    d.indications_text = row.indications_text,
    d.dosage_text = row.dosage_text,
    d.warnings_text = row.warnings_text,
    d.adverse_reactions_text = row.adverse_reactions_text
ON MATCH SET
    d.brand_name = coalesce(row.brand_name, d.brand_name),
    d.generic_name = coalesce(row.generic_name, d.generic_name),
    d.indications_text = coalesce(row.indications_text, d.indications_text),
    d.dosage_text = coalesce(row.dosage_text, d.dosage_text),
    d.warnings_text = coalesce(row.warnings_text, d.warnings_text),
    d.adverse_reactions_text = coalesce(row.adverse_reactions_text, d.adverse_reactions_text)
"""

CYPHER_IMPORT_DRUG_INGREDIENTS = """
UNWIND $links AS link
MATCH (d:DrugProduct {source_id: link.source_id})
MERGE (i:ActiveIngredient {name: link.ingredient_name})
MERGE (d)-[:CONTAINS_INGREDIENT]->(i)
"""

CYPHER_IMPORT_DISEASE_CHUNKS = """
UNWIND $chunks AS row
MERGE (c:DiseaseChunk {chunk_id: row.chunk_id})
ON CREATE SET c.source_id = row.source_id
ON MATCH SET c.source_id = coalesce(row.source_id, c.source_id)
MERGE (d:Disease {name: row.disease_name})
MERGE (c)-[:DESCRIBES_DISEASE]->(d)
"""

CYPHER_IMPORT_CHUNK_SYMPTOMS = """
UNWIND $links AS link
MATCH (c:DiseaseChunk {chunk_id: link.chunk_id})
MERGE (s:Symptom {name: link.symptom_name})
MERGE (c)-[:REPORTS_SYMPTOM]->(s)
"""

CYPHER_IMPORT_DISEASE_SYMPTOMS = """
UNWIND $links AS link
MATCH (d:Disease {name: link.disease_name})
MERGE (s:Symptom {name: link.symptom_name})
MERGE (d)-[:PRESENTS_SYMPTOM]->(s)
"""


# ==============================================================================
# Record Normalization & Cleaning Helpers
# ==============================================================================

def normalize_text_property(val: Any) -> Optional[str]:
    """
    Normalizes a text property value:
    - Strips whitespace.
    - Converts placeholder tokens ('none', 'n/a', etc.) and empty strings to None (null in Cypher).
    - Preserves approved source text without mutations.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in PLACEHOLDERS_SET:
        return None
    return s


def parse_drug_row(line_no: int, line: str) -> Dict[str, Any]:
    """
    Parses a single JSONL row from data/drugs_faiss_data.jsonl.
    Validates identifiers and extracts normalized drug fields and active ingredients.
    """
    try:
        row = json.loads(line)
    except Exception as exc:
        raise ValueError(f"Malformed JSON on line {line_no} of drugs dataset: {exc}")

    source_id = row.get("id")
    if source_id is None:
        raise ValueError(f"Missing required 'id' on line {line_no} of drugs dataset")

    # Adverse reactions with fallback for observed corrupted key 'adréactions'
    adverse_raw = row.get("adverse_reactions")
    if adverse_raw is None:
        adverse_raw = row.get("adréactions")

    # Substance name normalization (uppercase, stripped, collapsed whitespace)
    raw_substances = row.get("substance_name", [])
    if isinstance(raw_substances, str):
        raw_substances = [raw_substances]
    ingredients: List[str] = []
    for sub in raw_substances:
        cleaned = " ".join(str(sub).strip().split()).upper()
        if cleaned and cleaned not in ingredients:
            ingredients.append(cleaned)

    return {
        "source_id": int(source_id),
        "brand_name": normalize_text_property(row.get("brand_name")),
        "generic_name": normalize_text_property(row.get("generic_name")),
        "indications_text": normalize_text_property(row.get("indications_and_usage")),
        "dosage_text": normalize_text_property(row.get("dosage_and_administration")),
        "warnings_text": normalize_text_property(row.get("warnings_and_cautions")),
        "adverse_reactions_text": normalize_text_property(adverse_raw),
        "ingredients": ingredients,
    }


def build_canonical_disease_map(file_path: Path) -> Dict[str, str]:
    """
    Scans the disease dataset to build a case-consistent canonical disease name map.
    Preserves acronyms (e.g. 'ADHD', 'GERD') and preferred capitalized forms.
    """
    variants: Dict[str, Dict[str, int]] = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                raw_disease = row.get("chunk", {}).get("disease", "")
                cleaned = " ".join(str(raw_disease).strip().split())
                if cleaned:
                    low = cleaned.lower()
                    if low not in variants:
                        variants[low] = {}
                    variants[low][cleaned] = variants[low].get(cleaned, 0) + 1
            except Exception:
                continue

    canonical: Dict[str, str] = {}
    for low, counts in variants.items():
        # Prefer non-lowercased variant, then most frequent
        sorted_candidates = sorted(
            counts.items(),
            key=lambda x: (not x[0].islower(), x[1]),
            reverse=True,
        )
        canonical[low] = sorted_candidates[0][0]
    return canonical


def parse_disease_row(
    line_no: int,
    line: str,
    canonical_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Parses a single JSONL row from data/diseases_faiss_data.jsonl.
    Excludes symptoms[0] when identical to disease name and normalizes symptom entities.
    """
    try:
        row = json.loads(line)
    except Exception as exc:
        raise ValueError(f"Malformed JSON on line {line_no} of diseases dataset: {exc}")

    source_id = row.get("id")
    chunk = row.get("chunk")
    if source_id is None or not isinstance(chunk, dict):
        raise ValueError(f"Missing required 'id' or 'chunk' on line {line_no} of diseases dataset")

    chunk_id = chunk.get("id")
    raw_disease = chunk.get("disease")
    if not chunk_id or not raw_disease:
        raise ValueError(f"Missing required 'chunk.id' or 'chunk.disease' on line {line_no}")

    disease_cleaned = " ".join(str(raw_disease).strip().split())
    if canonical_map and disease_cleaned.lower() in canonical_map:
        disease_name = canonical_map[disease_cleaned.lower()]
    else:
        disease_name = disease_cleaned

    raw_symptoms = chunk.get("symptoms", [])
    first_symptom_cleaned = (
        " ".join(str(raw_symptoms[0]).strip().split()).lower()
        if raw_symptoms
        else ""
    )

    # Exclude first symptom if identical to disease name (source convention)
    if raw_symptoms and first_symptom_cleaned == disease_cleaned.lower():
        candidate_symptoms = raw_symptoms[1:]
    else:
        candidate_symptoms = raw_symptoms

    symptoms: List[str] = []
    for s in candidate_symptoms:
        cleaned_s = " ".join(str(s).strip().split()).lower()
        if cleaned_s and cleaned_s not in symptoms:
            symptoms.append(cleaned_s)

    return {
        "source_id": int(source_id),
        "chunk_id": str(chunk_id).strip(),
        "disease_name": disease_name,
        "symptoms": symptoms,
    }


# ==============================================================================
# Streaming Batch Generators
# ==============================================================================

def stream_drug_batches(
    file_path: Path,
    batch_size: int = 1000,
    limit: Optional[int] = None,
) -> Iterator[List[Dict[str, Any]]]:
    """Streams drug records in bounded batches without loading entire file into memory."""
    batch: List[Dict[str, Any]] = []
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            parsed = parse_drug_row(line_no, line)
            batch.append(parsed)
            count += 1
            if len(batch) >= batch_size:
                yield batch
                batch = []
            if limit and count >= limit:
                break
    if batch:
        yield batch


def stream_disease_batches(
    file_path: Path,
    canonical_map: Dict[str, str],
    batch_size: int = 1000,
    limit: Optional[int] = None,
) -> Iterator[List[Dict[str, Any]]]:
    """Streams disease records in bounded batches."""
    batch: List[Dict[str, Any]] = []
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            parsed = parse_disease_row(line_no, line, canonical_map=canonical_map)
            batch.append(parsed)
            count += 1
            if len(batch) >= batch_size:
                yield batch
                batch = []
            if limit and count >= limit:
                break
    if batch:
        yield batch


# ==============================================================================
# Ingestion Workers
# ==============================================================================

def import_drugs_dataset(
    driver: Any,
    file_path: Path,
    batch_size: int = 1000,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Executes batched, idempotent import of data/drugs_faiss_data.jsonl.
    """
    print(f"\n📦 Starting Drug Graph Ingestion from: {file_path}")
    print(f"   Batch size: {batch_size} | Dry-run: {dry_run} | Limit: {limit or 'Full file'}")

    total_products = 0
    total_ingredient_links = 0
    unique_ingredients_seen = set()
    batches_processed = 0
    t_start = time.perf_counter()

    for batch in stream_drug_batches(file_path, batch_size=batch_size, limit=limit):
        batches_processed += 1
        t_batch_start = time.perf_counter()

        # Prepare parameters
        products_params = []
        ingredient_links_params = []

        for item in batch:
            products_params.append({
                "source_id": item["source_id"],
                "brand_name": item["brand_name"],
                "generic_name": item["generic_name"],
                "indications_text": item["indications_text"],
                "dosage_text": item["dosage_text"],
                "warnings_text": item["warnings_text"],
                "adverse_reactions_text": item["adverse_reactions_text"],
            })
            for ing in item["ingredients"]:
                ingredient_links_params.append({
                    "source_id": item["source_id"],
                    "ingredient_name": ing,
                })
                unique_ingredients_seen.add(ing)

        total_products += len(products_params)
        total_ingredient_links += len(ingredient_links_params)

        if not dry_run:
            with driver.session() as session:
                # 1. Merge DrugProduct nodes
                session.run(CYPHER_IMPORT_DRUGS, {"products": products_params})
                # 2. Merge ActiveIngredient nodes and CONTAINS_INGREDIENT edges
                if ingredient_links_params:
                    session.run(CYPHER_IMPORT_DRUG_INGREDIENTS, {"links": ingredient_links_params})

        elapsed_batch = (time.perf_counter() - t_batch_start) * 1000
        print(
            f"   ↳ Batch #{batches_processed:03d}: {len(products_params)} products, "
            f"{len(ingredient_links_params)} ingredient links ({elapsed_batch:.1f}ms) "
            f"[Total products: {total_products}]"
        )

    total_elapsed = time.perf_counter() - t_start
    print(
        f"✅ Drug Ingestion Complete: {total_products} DrugProducts, "
        f"{len(unique_ingredients_seen)} unique ActiveIngredients, "
        f"{total_ingredient_links} CONTAINS_INGREDIENT edges ({total_elapsed:.2f}s)"
    )

    return {
        "dataset": "drugs",
        "products_count": total_products,
        "unique_ingredients_count": len(unique_ingredients_seen),
        "ingredient_links_count": total_ingredient_links,
        "batches_count": batches_processed,
        "elapsed_seconds": total_elapsed,
    }


def import_diseases_dataset(
    driver: Any,
    file_path: Path,
    batch_size: int = 1000,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Executes batched, idempotent import of data/diseases_faiss_data.jsonl.
    """
    print(f"\n📦 Starting Disease Graph Ingestion from: {file_path}")
    print(f"   Batch size: {batch_size} | Dry-run: {dry_run} | Limit: {limit or 'Full file'}")

    t_canonical = time.perf_counter()
    canonical_map = build_canonical_disease_map(file_path)
    print(f"   ↳ Canonical disease names resolved: {len(canonical_map)} in {(time.perf_counter()-t_canonical)*1000:.1f}ms")

    total_chunks = 0
    total_chunk_symptom_links = 0
    total_disease_symptom_links = 0
    unique_diseases_seen = set()
    unique_symptoms_seen = set()
    batches_processed = 0
    t_start = time.perf_counter()

    for batch in stream_disease_batches(file_path, canonical_map, batch_size=batch_size, limit=limit):
        batches_processed += 1
        t_batch_start = time.perf_counter()

        chunks_params = []
        chunk_symptoms_params = []
        disease_symptoms_params = []

        for item in batch:
            chunks_params.append({
                "source_id": item["source_id"],
                "chunk_id": item["chunk_id"],
                "disease_name": item["disease_name"],
            })
            unique_diseases_seen.add(item["disease_name"])

            for sym in item["symptoms"]:
                chunk_symptoms_params.append({
                    "chunk_id": item["chunk_id"],
                    "symptom_name": sym,
                })
                disease_symptoms_params.append({
                    "disease_name": item["disease_name"],
                    "symptom_name": sym,
                })
                unique_symptoms_seen.add(sym)

        total_chunks += len(chunks_params)
        total_chunk_symptom_links += len(chunk_symptoms_params)
        total_disease_symptom_links += len(disease_symptoms_params)

        if not dry_run:
            with driver.session() as session:
                # 1. Merge DiseaseChunk and Disease nodes + DESCRIBES_DISEASE
                session.run(CYPHER_IMPORT_DISEASE_CHUNKS, {"chunks": chunks_params})
                # 2. Merge Symptom nodes and REPORTS_SYMPTOM
                if chunk_symptoms_params:
                    session.run(CYPHER_IMPORT_CHUNK_SYMPTOMS, {"links": chunk_symptoms_params})
                # 3. Merge PRESENTS_SYMPTOM edges
                if disease_symptoms_params:
                    session.run(CYPHER_IMPORT_DISEASE_SYMPTOMS, {"links": disease_symptoms_params})

        elapsed_batch = (time.perf_counter() - t_batch_start) * 1000
        print(
            f"   ↳ Batch #{batches_processed:03d}: {len(chunks_params)} chunks, "
            f"{len(chunk_symptoms_params)} symptom links ({elapsed_batch:.1f}ms) "
            f"[Total chunks: {total_chunks}]"
        )

    total_elapsed = time.perf_counter() - t_start
    print(
        f"✅ Disease Ingestion Complete: {total_chunks} DiseaseChunks, "
        f"{len(unique_diseases_seen)} Diseases, {len(unique_symptoms_seen)} Symptoms, "
        f"{total_chunk_symptom_links} chunk symptom links ({total_elapsed:.2f}s)"
    )

    return {
        "dataset": "diseases",
        "chunks_count": total_chunks,
        "unique_diseases_count": len(unique_diseases_seen),
        "unique_symptoms_count": len(unique_symptoms_seen),
        "chunk_symptom_links_count": total_chunk_symptom_links,
        "batches_count": batches_processed,
        "elapsed_seconds": total_elapsed,
    }


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batched idempotent Neo4j importer for MediScanAI approved datasets."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse datasets and simulate ingestion batches without connecting to Neo4j.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for UNWIND parameterized transactions (default: 1000).",
    )
    parser.add_argument(
        "--target",
        choices=["all", "drugs", "diseases"],
        default="all",
        help="Target datasets to import (default: all).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of rows to import per dataset (for testing).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("\n" + "=" * 70)
    print("MediScanAI Neo4j Data Importer — Phase 2.3")
    print("=" * 70)

    # Validate dataset existence
    if not DRUGS_FILE.exists():
        print(f"❌ Required drugs dataset not found: {DRUGS_FILE}")
        return 1
    if not DISEASES_FILE.exists():
        print(f"❌ Required diseases dataset not found: {DISEASES_FILE}")
        return 1

    settings = get_settings()

    # Dry-run execution
    if args.dry_run:
        print("\n🔍 DRY-RUN MODE: Parsing datasets and computing batch statistics without database connection.\n")
        if args.target in ("all", "drugs"):
            import_drugs_dataset(None, DRUGS_FILE, batch_size=args.batch_size, limit=args.limit, dry_run=True)
        if args.target in ("all", "diseases"):
            import_diseases_dataset(None, DISEASES_FILE, batch_size=args.batch_size, limit=args.limit, dry_run=True)
        print("\n✅ Dry-run completed successfully.")
        return 0

    # Gate on configuration
    if not settings.NEO4J_ENABLED:
        print("\n❌ Neo4j is currently disabled in application configuration.")
        print("   Set NEO4J_ENABLED=true in .env to enable graph operations.")
        print("   To test dataset parsing and batching without Neo4j, use --dry-run.\n")
        return 1

    driver = None
    try:
        driver = get_neo4j_driver(settings)
        if driver is None or not verify_neo4j_connectivity(driver):
            print(f"\n❌ Neo4j server is unreachable at: {settings.NEO4J_URI}")
            print("   Please ensure the Neo4j Docker container or service is running.")
            print("   Check credentials and timeout in .env.\n")
            return 1

        print(f"✅ Connected to Neo4j instance at {settings.NEO4J_URI}")

        if args.target in ("all", "drugs"):
            import_drugs_dataset(driver, DRUGS_FILE, batch_size=args.batch_size, limit=args.limit, dry_run=False)

        if args.target in ("all", "diseases"):
            import_diseases_dataset(driver, DISEASES_FILE, batch_size=args.batch_size, limit=args.limit, dry_run=False)

        print("\n🎉 All requested imports completed successfully.")
        return 0

    except Exception as exc:
        print(f"\n💥 Ingestion failed with error: {exc}")
        logger.exception("Ingestion failed")
        return 1
    finally:
        if driver is not None:
            close_neo4j_driver(driver)
            logger.debug("Closed Neo4j driver connection.")


if __name__ == "__main__":
    sys.exit(main())
