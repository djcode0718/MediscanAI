#!/usr/bin/env python3
"""
MediScanAI — Phase 2.4: Standalone Data Reconciliation and Validation Script.

Reconciles the Neo4j graph against the approved source datasets:
  - data/drugs_faiss_data.jsonl
  - data/diseases_faiss_data.jsonl
(Excludes data/drug_dict_faiss_data.jsonl which is strictly FAISS/BM25-only).

Features:
  - Derives dynamic ground truth directly from source files (no hardcoded counts).
  - Validates node counts, relationship counts, and endpoint referential integrity.
  - Detects duplicate logical relationships, orphan endpoints, and unnormalized placeholders.
  - Spot-checks typo handling (adverse reaction fallback for ID 2305).
  - Strictly non-destructive (never deletes or repairs data automatically).
  - Explicitly separates static dataset invariant checks from live database verification.

Usage:
    python scripts/neo4j/validate_data.py [--static-only] [--json]
"""

import sys
import os
import argparse
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

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
from scripts.neo4j.import_data import (
    DRUGS_FILE,
    DISEASES_FILE,
    build_canonical_disease_map,
    parse_drug_row,
    parse_disease_row,
)

logger = logging.getLogger("mediscanai.graph.validator")

# ==============================================================================
# 1. Source Data Ground-Truth Derivation
# ==============================================================================

def compute_source_ground_truth(
    drugs_path: Path,
    diseases_path: Path,
) -> Dict[str, Any]:
    """
    Scans the approved JSONL datasets to compute ground-truth entity and relationship counts.
    Streams line-by-line using bounded memory.
    """
    t0 = time.perf_counter()

    # --- 1. Process Drugs Dataset ---
    total_drugs = 0
    drug_ids_seen: Set[int] = set()
    unique_ingredients: Set[str] = set()
    total_contains_ingredient_edges = 0
    cinzan_record: Optional[Dict[str, Any]] = None

    with open(drugs_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = parse_drug_row(line_no, line)
            total_drugs += 1
            drug_ids_seen.add(row["source_id"])

            for ing in row["ingredients"]:
                unique_ingredients.add(ing)
                total_contains_ingredient_edges += 1

            if row["source_id"] == 2305:
                cinzan_record = row

    drug_ids_unique = len(drug_ids_seen) == total_drugs

    # --- 2. Process Diseases Dataset ---
    canonical_disease_map = build_canonical_disease_map(diseases_path)
    total_chunks = 0
    chunk_ids_seen: Set[str] = set()
    unique_diseases: Set[str] = set()
    unique_symptoms: Set[str] = set()
    total_reports_symptom_edges = 0
    distinct_presents_symptom_pairs: Set[Tuple[str, str]] = set()

    with open(diseases_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = parse_disease_row(line_no, line, canonical_disease_map)
            total_chunks += 1
            chunk_ids_seen.add(row["chunk_id"])
            unique_diseases.add(row["disease_name"])

            for sym in row["symptoms"]:
                unique_symptoms.add(sym)
                total_reports_symptom_edges += 1
                distinct_presents_symptom_pairs.add((row["disease_name"], sym))

    chunk_ids_unique = len(chunk_ids_seen) == total_chunks
    total_presents_symptom_edges = len(distinct_presents_symptom_pairs)

    elapsed = time.perf_counter() - t0

    return {
        "computation_time_seconds": elapsed,
        "nodes": {
            "DrugProduct": total_drugs,
            "ActiveIngredient": len(unique_ingredients),
            "DiseaseChunk": total_chunks,
            "Disease": len(unique_diseases),
            "Symptom": len(unique_symptoms),
        },
        "relationships": {
            "CONTAINS_INGREDIENT": total_contains_ingredient_edges,
            "DESCRIBES_DISEASE": total_chunks,
            "REPORTS_SYMPTOM": total_reports_symptom_edges,
            "PRESENTS_SYMPTOM": total_presents_symptom_edges,
        },
        "invariants": {
            "drug_source_ids_unique": drug_ids_unique,
            "chunk_ids_unique": chunk_ids_unique,
            "cinzan_adverse_recovered": (
                cinzan_record is not None
                and cinzan_record.get("adverse_reactions_text") is not None
            ),
        },
    }


# ==============================================================================
# 2. Live Neo4j Graph Inspection Queries
# ==============================================================================

CYPHER_NODE_COUNTS = """
RETURN {
    DrugProduct: count { MATCH (:DrugProduct) },
    ActiveIngredient: count { MATCH (:ActiveIngredient) },
    DiseaseChunk: count { MATCH (:DiseaseChunk) },
    Disease: count { MATCH (:Disease) },
    Symptom: count { MATCH (:Symptom) }
} AS counts
"""

CYPHER_RELATIONSHIP_COUNTS = """
RETURN {
    CONTAINS_INGREDIENT: count { MATCH ()-[:CONTAINS_INGREDIENT]->() },
    DESCRIBES_DISEASE: count { MATCH ()-[:DESCRIBES_DISEASE]->() },
    REPORTS_SYMPTOM: count { MATCH ()-[:REPORTS_SYMPTOM]->() },
    PRESENTS_SYMPTOM: count { MATCH ()-[:PRESENTS_SYMPTOM]->() }
} AS counts
"""

CYPHER_DUPLICATE_RELATIONSHIPS = """
RETURN {
    duplicate_contains_ingredient: count {
        MATCH (d:DrugProduct)-[r:CONTAINS_INGREDIENT]->(i:ActiveIngredient)
        WITH d, i, count(r) AS cnt WHERE cnt > 1 RETURN d
    },
    duplicate_describes_disease: count {
        MATCH (c:DiseaseChunk)-[r:DESCRIBES_DISEASE]->(d:Disease)
        WITH c, d, count(r) AS cnt WHERE cnt > 1 RETURN c
    },
    duplicate_reports_symptom: count {
        MATCH (c:DiseaseChunk)-[r:REPORTS_SYMPTOM]->(s:Symptom)
        WITH c, s, count(r) AS cnt WHERE cnt > 1 RETURN c
    },
    duplicate_presents_symptom: count {
        MATCH (d:Disease)-[r:PRESENTS_SYMPTOM]->(s:Symptom)
        WITH d, s, count(r) AS cnt WHERE cnt > 1 RETURN d
    }
} AS counts
"""

CYPHER_ORPHAN_NODES = """
RETURN {
    orphan_ingredients: count {
        MATCH (i:ActiveIngredient) WHERE NOT (:DrugProduct)-[:CONTAINS_INGREDIENT]->(i) RETURN i
    },
    orphan_chunks: count {
        MATCH (c:DiseaseChunk) WHERE NOT (c)-[:DESCRIBES_DISEASE]->(:Disease) RETURN c
    },
    orphan_symptoms: count {
        MATCH (s:Symptom) WHERE NOT (:DiseaseChunk)-[:REPORTS_SYMPTOM]->(s)
                            AND NOT (:Disease)-[:PRESENTS_SYMPTOM]->(s) RETURN s
    }
} AS counts
"""

CYPHER_IDENTIFIER_INTEGRITY = """
RETURN {
    duplicate_drug_source_ids: count {
        MATCH (d:DrugProduct) WITH d.source_id AS id, count(*) AS cnt WHERE cnt > 1 RETURN id
    },
    duplicate_chunk_ids: count {
        MATCH (c:DiseaseChunk) WITH c.chunk_id AS id, count(*) AS cnt WHERE cnt > 1 RETURN id
    },
    unsanitized_placeholders: count {
        MATCH (d:DrugProduct)
        WHERE toLower(coalesce(d.warnings_text, '')) IN ['none', 'n/a', 'unknown', 'null']
           OR toLower(coalesce(d.adverse_reactions_text, '')) IN ['none', 'n/a', 'unknown', 'null']
        RETURN d
    },
    ocr_dictionary_nodes: count {
        MATCH (n) WHERE 'OcrTerm' IN labels(n) OR 'DrugDict' IN labels(n) OR 'DrugDictEntry' IN labels(n)
        RETURN n
    }
} AS counts
"""

CYPHER_SPOT_CHECK_CINZAN = """
MATCH (d:DrugProduct {source_id: 2305})
RETURN d.brand_name AS brand, d.adverse_reactions_text AS adverse
"""


def query_live_database_metrics(driver: Any) -> Dict[str, Any]:
    """
    Executes targeted diagnostic queries against Neo4j to collect actual graph metrics.
    """
    with driver.session() as session:
        node_counts = session.run(CYPHER_NODE_COUNTS).single()["counts"]
        rel_counts = session.run(CYPHER_RELATIONSHIP_COUNTS).single()["counts"]
        dup_rels = session.run(CYPHER_DUPLICATE_RELATIONSHIPS).single()["counts"]
        orphans = session.run(CYPHER_ORPHAN_NODES).single()["counts"]
        integrity = session.run(CYPHER_IDENTIFIER_INTEGRITY).single()["counts"]

        # Spot-check Cinzan (ID 2305)
        cinzan_res = session.run(CYPHER_SPOT_CHECK_CINZAN).single()
        cinzan_adverse = cinzan_res["adverse"] if cinzan_res else None

    return {
        "nodes": node_counts,
        "relationships": rel_counts,
        "duplicate_relationships": dup_rels,
        "orphans": orphans,
        "integrity": integrity,
        "cinzan_adverse_recovered": cinzan_adverse is not None and len(cinzan_adverse.strip()) > 0,
    }


# ==============================================================================
# 3. Reconciliation & Comparison Engine
# ==============================================================================

def reconcile_metrics(
    ground_truth: Dict[str, Any],
    live_metrics: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compares ground truth from source files against live database numbers.
    Produces pass/fail evaluation records.
    """
    checks: List[Dict[str, Any]] = []

    # --- Static Invariant Checks ---
    checks.append({
        "check": "Source Drug Product IDs Unique",
        "category": "Static / Source Invariant",
        "expected": True,
        "actual": ground_truth["invariants"]["drug_source_ids_unique"],
        "passed": ground_truth["invariants"]["drug_source_ids_unique"] is True,
    })
    checks.append({
        "check": "Source Disease Chunk IDs Unique",
        "category": "Static / Source Invariant",
        "expected": True,
        "actual": ground_truth["invariants"]["chunk_ids_unique"],
        "passed": ground_truth["invariants"]["chunk_ids_unique"] is True,
    })
    checks.append({
        "check": "Corrupted Adverse Key Fallback (ID 2305)",
        "category": "Static / Source Invariant",
        "expected": True,
        "actual": ground_truth["invariants"]["cinzan_adverse_recovered"],
        "passed": ground_truth["invariants"]["cinzan_adverse_recovered"] is True,
    })

    # --- Database Live Checks ---
    if live_metrics is None:
        return {
            "all_passed": all(c["passed"] for c in checks),
            "database_checked": False,
            "checks": checks,
        }

    # Node count checks
    for label, exp_count in ground_truth["nodes"].items():
        act_count = live_metrics["nodes"].get(label, 0)
        checks.append({
            "check": f"Node Count: (:{label})",
            "category": "Graph Node Counts",
            "expected": exp_count,
            "actual": act_count,
            "passed": exp_count == act_count,
        })

    # Relationship count checks
    for rtype, exp_count in ground_truth["relationships"].items():
        act_count = live_metrics["relationships"].get(rtype, 0)
        checks.append({
            "check": f"Relationship Count: [:{rtype}]",
            "category": "Graph Relationship Counts",
            "expected": exp_count,
            "actual": act_count,
            "passed": exp_count == act_count,
        })

    # Duplicate relationship checks
    for dup_key, act_count in live_metrics["duplicate_relationships"].items():
        checks.append({
            "check": f"No Duplicate Relationships: {dup_key}",
            "category": "Graph Structure Integrity",
            "expected": 0,
            "actual": act_count,
            "passed": act_count == 0,
        })

    # Orphan checks
    for orph_key, act_count in live_metrics["orphans"].items():
        checks.append({
            "check": f"No Orphan Endpoints: {orph_key}",
            "category": "Graph Structure Integrity",
            "expected": 0,
            "actual": act_count,
            "passed": act_count == 0,
        })

    # ID uniqueness & placeholder checks in DB
    checks.append({
        "check": "Database Drug source_id Unique",
        "category": "Graph Property Integrity",
        "expected": 0,
        "actual": live_metrics["integrity"]["duplicate_drug_source_ids"],
        "passed": live_metrics["integrity"]["duplicate_drug_source_ids"] == 0,
    })
    checks.append({
        "check": "Database Disease chunk_id Unique",
        "category": "Graph Property Integrity",
        "expected": 0,
        "actual": live_metrics["integrity"]["duplicate_chunk_ids"],
        "passed": live_metrics["integrity"]["duplicate_chunk_ids"] == 0,
    })
    checks.append({
        "check": "Unsanitized Placeholder Strings in Graph",
        "category": "Graph Property Integrity",
        "expected": 0,
        "actual": live_metrics["integrity"]["unsanitized_placeholders"],
        "passed": live_metrics["integrity"]["unsanitized_placeholders"] == 0,
    })
    checks.append({
        "check": "OCR Dictionary Nodes Excluded From Graph",
        "category": "Graph Property Integrity",
        "expected": 0,
        "actual": live_metrics["integrity"]["ocr_dictionary_nodes"],
        "passed": live_metrics["integrity"]["ocr_dictionary_nodes"] == 0,
    })
    checks.append({
        "check": "Cinzan (ID 2305) Adverse Text Preserved in DB",
        "category": "Graph Property Integrity",
        "expected": True,
        "actual": live_metrics["cinzan_adverse_recovered"],
        "passed": live_metrics["cinzan_adverse_recovered"] is True,
    })

    return {
        "all_passed": all(c["passed"] for c in checks),
        "database_checked": True,
        "checks": checks,
    }


# ==============================================================================
# 4. Formatted Reporting
# ==============================================================================

def print_validation_report(
    reconciliation: Dict[str, Any],
    ground_truth: Dict[str, Any],
    live_metrics: Optional[Dict[str, Any]],
) -> None:
    """Prints a formatted console report with clear sections and status badges."""
    print("\n" + "=" * 78)
    print("MediScanAI — Data Reconciliation and Graph Validation Report")
    print("=" * 78)

    print("\n[SECTION 1: SOURCE DATA GROUND TRUTH (Approved Datasets)]")
    print(f"Computed dynamically in {ground_truth['computation_time_seconds']:.2f}s:")
    for label, count in ground_truth["nodes"].items():
        print(f"  • Expected {label:<20} nodes: {count:>8,}")
    for rtype, count in ground_truth["relationships"].items():
        print(f"  • Expected [:{rtype}] edges: {count:>8,}")

    print("\n[SECTION 2: DATABASE RECONCILIATION & INTEGRITY CHECKS]")
    if not reconciliation["database_checked"]:
        print("⚠️  LIVE NEO4J INSTANCE STATUS: OFFLINE / DISCONNECTED")
        print("   Database runtime queries were skipped. Static dataset invariants evaluated below.\n")
    else:
        print("✅ LIVE NEO4J INSTANCE STATUS: CONNECTED AND EVALUATED\n")

    # Table format
    header = f"{'Category':<28} | {'Validation Check':<34} | {'Status':<7} | Expected vs Actual"
    print(header)
    print("-" * 78)

    for item in reconciliation["checks"]:
        badge = "✅ PASS" if item["passed"] else "❌ FAIL"
        exp_act = f"Exp: {item['expected']} | Act: {item['actual']}"
        print(f"{item['category']:<28} | {item['check']:<34} | {badge:<7} | {exp_act}")

    print("-" * 78)
    if reconciliation["all_passed"]:
        if reconciliation["database_checked"]:
            print("🎉 OVERALL VERDICT: ALL STATIC AND LIVE DATABASE CHECKS PASSED PERFECTLY.")
        else:
            print("🎉 OVERALL VERDICT: ALL STATIC SOURCE DATA INVARIANT CHECKS PASSED.")
    else:
        print("❌ OVERALL VERDICT: VALIDATION FAILED — INVARIANTS OR COUNTS MISMATCHED.")
    print("=" * 78 + "\n")


# ==============================================================================
# 5. CLI Entrypoint
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standalone data reconciliation and validation tool for MediScanAI Neo4j."
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Run static ground truth derivation and dataset invariant checks without connecting to Neo4j.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw reconciliation results in JSON format.",
    )
    args = parser.parse_args()

    # Logging setup
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not DRUGS_FILE.exists():
        print(f"❌ Missing dataset: {DRUGS_FILE}")
        return 1
    if not DISEASES_FILE.exists():
        print(f"❌ Missing dataset: {DISEASES_FILE}")
        return 1

    # 1. Compute ground truth from source files
    ground_truth = compute_source_ground_truth(DRUGS_FILE, DISEASES_FILE)

    # 2. Check if live database validation is requested
    live_metrics = None
    if not args.static_only:
        settings = get_settings()
        if settings.NEO4J_ENABLED:
            driver = None
            try:
                driver = get_neo4j_driver(settings)
                if driver and verify_neo4j_connectivity(driver):
                    live_metrics = query_live_database_metrics(driver)
            except Exception as exc:
                logger.warning("Could not collect live Neo4j metrics: %s", exc)
            finally:
                if driver:
                    close_neo4j_driver(driver)

    # 3. Reconcile
    reconciliation = reconcile_metrics(ground_truth, live_metrics)

    # 4. Report
    if args.json:
        output_payload = {
            "ground_truth": ground_truth,
            "live_metrics": live_metrics,
            "reconciliation": reconciliation,
        }
        print(json.dumps(output_payload, indent=2))
    else:
        print_validation_report(reconciliation, ground_truth, live_metrics)

    return 0 if reconciliation["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
