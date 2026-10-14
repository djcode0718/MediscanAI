#!/usr/bin/env python3
"""
MediScanAI — Phase 2.2: Neo4j Schema Constraints and Indexes Application Script.

Applies idempotent uniqueness constraints and non-redundant lookup indexes
to Neo4j using centralized configuration and the application driver module.

Usage:
    python scripts/neo4j/apply_schema.py [--dry-run] [--verify-only]
"""

import sys
import os
import argparse
import logging
import time
from typing import List, Dict, Any, Optional

# Ensure repository root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.core.config import get_settings, Settings
from app.graph.driver import (
    get_neo4j_driver,
    create_neo4j_driver,
    verify_neo4j_connectivity,
    close_neo4j_driver,
)

logger = logging.getLogger("mediscanai.graph.schema")

# ==============================================================================
# Idempotent Schema Definitions (Neo4j 5.x Cypher)
# ==============================================================================

SCHEMA_CONSTRAINTS: List[Dict[str, str]] = [
    {
        "name": "drug_product_source_id_unique",
        "type": "CONSTRAINT",
        "target": "DrugProduct.source_id",
        "statement": (
            "CREATE CONSTRAINT drug_product_source_id_unique IF NOT EXISTS "
            "FOR (d:DrugProduct) REQUIRE d.source_id IS UNIQUE"
        ),
        "description": "Ensures 1:1 mapping with data/drugs_faiss_data.jsonl line offsets.",
    },
    {
        "name": "active_ingredient_name_unique",
        "type": "CONSTRAINT",
        "target": "ActiveIngredient.name",
        "statement": (
            "CREATE CONSTRAINT active_ingredient_name_unique IF NOT EXISTS "
            "FOR (i:ActiveIngredient) REQUIRE i.name IS UNIQUE"
        ),
        "description": "Prevents duplication of normalized chemical substances.",
    },
    {
        "name": "disease_name_unique",
        "type": "CONSTRAINT",
        "target": "Disease.name",
        "statement": (
            "CREATE CONSTRAINT disease_name_unique IF NOT EXISTS "
            "FOR (d:Disease) REQUIRE d.name IS UNIQUE"
        ),
        "description": "Consolidates disease records across multiple chunk passages.",
    },
    {
        "name": "disease_chunk_id_unique",
        "type": "CONSTRAINT",
        "target": "DiseaseChunk.chunk_id",
        "statement": (
            "CREATE CONSTRAINT disease_chunk_id_unique IF NOT EXISTS "
            "FOR (c:DiseaseChunk) REQUIRE c.chunk_id IS UNIQUE"
        ),
        "description": "Ensures unique identification for individual disease chunks (chunk_1..chunk_3411).",
    },
    {
        "name": "symptom_name_unique",
        "type": "CONSTRAINT",
        "target": "Symptom.name",
        "statement": (
            "CREATE CONSTRAINT symptom_name_unique IF NOT EXISTS "
            "FOR (s:Symptom) REQUIRE s.name IS UNIQUE"
        ),
        "description": "Ensures clean shared entities for clinical symptoms across diseases.",
    },
]

SCHEMA_INDEXES: List[Dict[str, str]] = [
    {
        "name": "drug_product_brand_name_idx",
        "type": "INDEX",
        "target": "DrugProduct.brand_name",
        "statement": (
            "CREATE INDEX drug_product_brand_name_idx IF NOT EXISTS "
            "FOR (d:DrugProduct) ON (d.brand_name)"
        ),
        "description": "Accelerates non-unique brand name lookups during multi-modal drug identification.",
    },
    {
        "name": "drug_product_generic_name_idx",
        "type": "INDEX",
        "target": "DrugProduct.generic_name",
        "statement": (
            "CREATE INDEX drug_product_generic_name_idx IF NOT EXISTS "
            "FOR (d:DrugProduct) ON (d.generic_name)"
        ),
        "description": "Accelerates non-unique generic name queries across multiple drug product lines.",
    },
]


def get_all_schema_definitions() -> List[Dict[str, str]]:
    """Return all schema constraints and indexes in execution order."""
    return SCHEMA_CONSTRAINTS + SCHEMA_INDEXES


def apply_schema(driver: Any, dry_run: bool = False) -> Dict[str, Any]:
    """
    Executes all schema definitions idempotently against Neo4j.
    Returns a summary dictionary of executed operations.
    """
    statements = get_all_schema_definitions()
    results: List[Dict[str, Any]] = []
    applied_count = 0
    failed_count = 0

    print("\n" + "=" * 70)
    print(f"Applying MediScanAI Neo4j Schema ({len(statements)} statements)...")
    print("=" * 70)

    if dry_run:
        print("🔍 DRY-RUN MODE: Statements will be validated but NOT sent to the database.\n")
        for idx, item in enumerate(statements, 1):
            print(f"[{idx}/{len(statements)}] {item['type']}: {item['name']}")
            print(f"  Target:      {item['target']}")
            print(f"  Statement:   {item['statement']}")
            print(f"  Description: {item['description']}\n")
            results.append({
                "name": item["name"],
                "type": item["type"],
                "status": "dry_run_skipped",
                "statement": item["statement"],
            })
        return {
            "total": len(statements),
            "applied": 0,
            "failed": 0,
            "dry_run": True,
            "details": results,
        }

    with driver.session() as session:
        for idx, item in enumerate(statements, 1):
            t0 = time.perf_counter()
            print(f"[{idx}/{len(statements)}] Applying {item['type']} '{item['name']}'...", end=" ")
            try:
                session.run(item["statement"])
                elapsed_ms = (time.perf_counter() - t0) * 1000
                print(f"✅ OK ({elapsed_ms:.1f}ms)")
                results.append({
                    "name": item["name"],
                    "type": item["type"],
                    "status": "success",
                    "elapsed_ms": elapsed_ms,
                })
                applied_count += 1
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                print(f"❌ FAILED ({elapsed_ms:.1f}ms): {exc}")
                logger.error("Failed to apply schema statement '%s': %s", item["name"], exc)
                results.append({
                    "name": item["name"],
                    "type": item["type"],
                    "status": "failed",
                    "error": str(exc),
                    "elapsed_ms": elapsed_ms,
                })
                failed_count += 1

    print("\n" + "-" * 70)
    print(f"Schema Application Complete: {applied_count} applied, {failed_count} failed out of {len(statements)} total.")
    print("-" * 70 + "\n")

    return {
        "total": len(statements),
        "applied": applied_count,
        "failed": failed_count,
        "dry_run": False,
        "details": results,
    }


def verify_active_schema(driver: Any) -> Dict[str, Any]:
    """
    Queries Neo4j catalog to list current constraints and indexes.
    """
    print("\n--- Current Neo4j Catalog Status ---")
    constraints_found = []
    indexes_found = []

    try:
        with driver.session() as session:
            # Query constraints
            c_records = session.run("SHOW CONSTRAINTS")
            for rec in c_records:
                c_name = rec.get("name", "unknown")
                c_type = rec.get("type", "unknown")
                constraints_found.append({"name": c_name, "type": c_type})

            # Query indexes
            i_records = session.run("SHOW INDEXES")
            for rec in i_records:
                i_name = rec.get("name", "unknown")
                i_type = rec.get("type", "unknown")
                indexes_found.append({"name": i_name, "type": i_type})

        print(f"Constraints detected in database: {len(constraints_found)}")
        for c in constraints_found:
            print(f"  - [CONSTRAINT] {c['name']} ({c['type']})")
        print(f"Indexes detected in database:     {len(indexes_found)}")
        for i in indexes_found:
            print(f"  - [INDEX]      {i['name']} ({i['type']})")

        return {
            "constraints": constraints_found,
            "indexes": indexes_found,
        }
    except Exception as exc:
        print(f"⚠️ Could not inspect catalog via SHOW commands: {exc}")
        return {"error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply idempotent Neo4j constraints and indexes for MediScanAI."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Cypher statements without connecting to Neo4j or executing.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Inspect and print currently registered Neo4j constraints and indexes without changes.",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = get_settings()

    # Dry-run does not require a live Neo4j connection
    if args.dry_run:
        apply_schema(driver=None, dry_run=True)
        return 0

    # 1. Check configuration enablement
    if not settings.NEO4J_ENABLED:
        print("\n❌ Neo4j is currently disabled in application configuration.")
        print("   Set NEO4J_ENABLED=true in .env to enable graph operations.")
        print("   To inspect the planned Cypher statements without Neo4j, run with --dry-run.\n")
        return 1

    # 2. Check server connectivity
    driver = None
    try:
        driver = get_neo4j_driver(settings)
        if driver is None:
            print(f"\n❌ Neo4j driver could not be created for URI: {settings.NEO4J_URI}")
            return 1

        is_connected = verify_neo4j_connectivity(driver)
        if not is_connected:
            print(f"\n❌ Neo4j server is unreachable at: {settings.NEO4J_URI}")
            print("   Please ensure the Neo4j Docker container or local service is running.")
            print("   Check credentials and connection timeout in .env.\n")
            return 1

        print(f"✅ Successfully connected to Neo4j instance at {settings.NEO4J_URI}")

        # 3. Execute requested operation
        if args.verify_only:
            verify_active_schema(driver)
            return 0

        summary = apply_schema(driver, dry_run=False)
        if summary["failed"] > 0:
            print("⚠️ Some schema operations failed. Please inspect logs above.")
            return 1

        # Print catalog verification
        verify_active_schema(driver)
        return 0

    except Exception as exc:
        print(f"\n💥 Unexpected error during schema execution: {exc}")
        logger.exception("Unexpected error in apply_schema main")
        return 1
    finally:
        if driver is not None:
            close_neo4j_driver(driver)
            logger.debug("Neo4j driver connection closed.")


if __name__ == "__main__":
    sys.exit(main())
