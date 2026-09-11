#!/usr/bin/env python3

import gzip
import json
import sqlite3
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FINAL_RAG = (
    PROJECT_ROOT
    / "entity_resolution"
    / "results"
    / "final"
    / "mediscanai_rag.jsonl.gz"
)

SQLITE_DB = (
    PROJECT_ROOT
    / "entity_resolution"
    / "results"
    / "final"
    / "document_dedup.sqlite"
)

EXPECTED = 3_064_937
BATCH_SIZE = 10_000


def main():

    start = time.time()

    print("=" * 72)
    print("MediScanAI 2.0 — REPAIR DOCUMENTS TABLE")
    print("=" * 72)

    print(f"\nRAG:")
    print(f"  {FINAL_RAG}")

    print(f"\nSQLite:")
    print(f"  {SQLITE_DB}")

    if not FINAL_RAG.exists():
        raise FileNotFoundError(FINAL_RAG)

    if not SQLITE_DB.exists():
        raise FileNotFoundError(SQLITE_DB)

    conn = sqlite3.connect(SQLITE_DB)

    # Safety: verify schema exists.
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    required = {"documents", "provenance", "file_stats"}

    if not required.issubset(tables):
        raise RuntimeError(
            f"Missing required tables. Found: {sorted(tables)}"
        )

    existing = conn.execute(
        "SELECT COUNT(*) FROM documents"
    ).fetchone()[0]

    print(f"\nExisting documents rows: {existing:,}")

    if existing != 0:
        raise RuntimeError(
            "Documents table is not empty. "
            "Refusing to modify it."
        )

    # We rebuild only the missing documents index.
    #
    # The final RAG has already been deduplicated by Cell 6.
    # rag_index is the deterministic output index assigned by Cell 6.

    insert_sql = """
        INSERT INTO documents (
            content_hash,
            source,
            document_id,
            output_index
        )
        VALUES (?, ?, ?, ?)
    """

    batch = []
    count = 0
    expected_index = 1

    print("\nRebuilding documents table...")

    with gzip.open(
        FINAL_RAG,
        "rt",
        encoding="utf-8",
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            content_hash = record.get("content_hash")
            source = record.get("source")
            document_id = record.get("document_id")
            rag_index = record.get("rag_index")

            if not content_hash:
                raise RuntimeError(
                    f"Missing content_hash at record {count + 1}"
                )

            if source not in (
                "fda",
                "dailymed",
                "clinical_trials",
            ):
                raise RuntimeError(
                    f"Invalid source at record {count + 1}: {source!r}"
                )

            if not document_id:
                raise RuntimeError(
                    f"Missing document_id at record {count + 1}"
                )

            if rag_index != expected_index:
                raise RuntimeError(
                    f"rag_index discontinuity: "
                    f"expected {expected_index}, "
                    f"got {rag_index}"
                )

            batch.append(
                (
                    content_hash,
                    source,
                    str(document_id),
                    rag_index,
                )
            )

            count += 1
            expected_index += 1

            if len(batch) >= BATCH_SIZE:

                conn.executemany(
                    insert_sql,
                    batch,
                )

                conn.commit()

                batch.clear()

                if count % 100_000 == 0:
                    print(
                        f"  Rebuilt {count:,} / "
                        f"{EXPECTED:,}"
                    )

    if batch:
        conn.executemany(
            insert_sql,
            batch,
        )

        conn.commit()

    final_count = conn.execute(
        "SELECT COUNT(*) FROM documents"
    ).fetchone()[0]

    provenance_count = conn.execute(
        "SELECT COUNT(*) FROM provenance"
    ).fetchone()[0]

    conn.close()

    elapsed = time.time() - start

    print("\n" + "=" * 72)
    print("REPAIR COMPLETE")
    print("=" * 72)

    print(f"\nDocuments inserted: {count:,}")
    print(f"Documents in DB:    {final_count:,}")
    print(f"Provenance rows:    {provenance_count:,}")
    print(f"Expected documents: {EXPECTED:,}")
    print(f"Runtime:            {elapsed / 60:.2f} minutes")

    if final_count != EXPECTED:
        raise RuntimeError(
            f"Document count mismatch: "
            f"{final_count:,} != {EXPECTED:,}"
        )

    if count != final_count:
        raise RuntimeError(
            f"Inserted count mismatch: "
            f"{count:,} != {final_count:,}"
        )

    print("\n✓ documents table successfully reconstructed")
    print("✓ Final RAG was NOT modified")
    print("✓ provenance was NOT modified")
    print("✓ file_stats was NOT modified")
    print("=" * 72)


if __name__ == "__main__":
    main()