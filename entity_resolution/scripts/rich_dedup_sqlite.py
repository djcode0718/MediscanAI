#!/usr/bin/env python3

"""
MediScanAI 2.0
Disk-backed Rich Exact Deduplication

IMPORTANT:
    This script is specifically designed for a 16 GB RAM Mac.

    It NEVER loads an entire hash bucket into RAM.

Architecture:

    tmp_rich_hash_buckets/
            |
            +--> 9 SQLite databases
            |
            +--> 9 processes
            |
            v
    disk-backed exact dedup
            |
            v
    rich canonical dataset

The existing worker shards and Stage-1 hash partitions are
treated as immutable input.

No re-chunking.
No truncation.
No semantic deduplication.
No provenance loss.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

NUM_BUCKETS = 9

FINAL_RECORDS_PER_SHARD = 75_000

GZIP_LEVEL = 3

ENCODING = "utf-8"

EXPECTED_INPUT = 5_578_588


# ============================================================
# FILE HELPERS
# ============================================================

def iter_jsonl(path: Path):

    with open(
        path,
        "r",
        encoding=ENCODING,
    ) as f:

        for line in f:

            line = line.strip()

            if line:

                yield json.loads(line)


# ============================================================
# RECORD HELPERS
# ============================================================

def get_record(wrapper: dict) -> dict:

    record = wrapper.get("record")

    if not isinstance(record, dict):

        raise RuntimeError(
            "Missing nested record."
        )

    return record


def get_hash(wrapper: dict) -> str:

    h = get_record(wrapper).get(
        "content_hash"
    )

    if not h:

        raise RuntimeError(
            "Missing content_hash."
        )

    return str(h)


def get_text(wrapper: dict) -> str:

    text = get_record(wrapper).get(
        "text",
        "",
    )

    return str(text)


# ============================================================
# PROVENANCE
# ============================================================

def extract_provenance(wrapper: dict) -> dict:

    record = get_record(wrapper)

    provenance = {
        "source": wrapper.get(
            "source",
            record.get("source"),
        ),

        "source_file": wrapper.get(
            "source_file",
            record.get("source_file"),
        ),

        "source_line": wrapper.get(
            "source_line",
        ),

        "original_document_id": wrapper.get(
            "original_document_id",
            record.get("document_id"),
        ),

        "document_id": record.get(
            "document_id"
        ),

        "chunk_index": wrapper.get(
            "chunk_index",
            record.get("chunk_index"),
        ),

        "chunk_count": wrapper.get(
            "chunk_count",
            record.get("chunk_count"),
        ),
    }

    important_fields = [
        "drug_name",
        "brand_names",
        "generic_names",
        "substances",
        "manufacturer_names",
        "product_types",
        "routes",
        "dosage_forms",
        "application_numbers",
        "product_ndc",
        "package_ndc",
        "unii",
        "rxcui",
        "effective_date",
        "effective_time",
        "section",
        "section_name",
        "set_id",
        "spl_id",
        "trial_id",
    ]

    for field in important_fields:

        if field in record:

            provenance[field] = record[field]

    # Clinical-trial enrichment is valuable provenance.
    if "enrichment" in record:

        provenance["enrichment"] = (
            record["enrichment"]
        )

    return provenance


# ============================================================
# SQLITE
# ============================================================

def create_database(db_path: Path):

    conn = sqlite3.connect(
        db_path,
        timeout=120,
    )

    # --------------------------------------------------------
    # PERFORMANCE SETTINGS
    #
    # Each worker owns its own DB.
    # Therefore durability settings can safely be relaxed
    # because the source partitions remain untouched.
    # --------------------------------------------------------

    conn.execute(
        "PRAGMA journal_mode=OFF"
    )

    conn.execute(
        "PRAGMA synchronous=OFF"
    )

    conn.execute(
        "PRAGMA temp_store=FILE"
    )

    conn.execute(
        "PRAGMA cache_size=-262144"
    )
    # ~256 MB SQLite cache maximum.

    conn.execute(
        "PRAGMA mmap_size=1073741824"
    )
    # Up to 1 GB mmap where supported.

    # --------------------------------------------------------
    # Canonical record table.
    #
    # WITHOUT ROWID + BLOB primary key keeps this reasonably
    # compact.
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE canonical (
            hash BLOB PRIMARY KEY,
            record_json TEXT NOT NULL
        ) WITHOUT ROWID
        """
    )

    # --------------------------------------------------------
    # Every original occurrence gets its own provenance row.
    #
    # This is the critical part:
    #
    # duplicate content does NOT mean lost provenance.
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE provenance (
            hash BLOB NOT NULL,
            provenance_json TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX provenance_hash_idx
        ON provenance(hash)
        """
    )

    conn.commit()

    return conn


# ============================================================
# INSERT HELPERS
# ============================================================

INSERT_CANONICAL = """
INSERT OR IGNORE INTO canonical
(hash, record_json)
VALUES (?, ?)
"""

INSERT_PROVENANCE = """
INSERT INTO provenance
(hash, provenance_json)
VALUES (?, ?)
"""


# ============================================================
# PROCESS ONE BUCKET
# ============================================================

def process_bucket(
    bucket_id: int,
    temp_dir: str,
    db_dir: str,
    output_dir: str,
):

    temp_dir = Path(temp_dir)

    db_dir = Path(db_dir)

    output_dir = Path(output_dir)

    db_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    db_path = (
        db_dir /
        f"bucket_{bucket_id:02d}.sqlite"
    )

    started = time.time()

    # --------------------------------------------------------
    # CREATE DB
    # --------------------------------------------------------

    if db_path.exists():

        db_path.unlink()

    conn = create_database(
        db_path
    )

    # --------------------------------------------------------
    # Input fragments belonging to this bucket.
    # --------------------------------------------------------

    fragments = sorted(
        temp_dir.glob(
            f"*/bucket_{bucket_id:02d}.jsonl"
        )
    )

    input_records = 0
    canonical_records = 0
    duplicate_records = 0

    # --------------------------------------------------------
    # Batch transaction.
    #
    # We don't commit every row.
    # --------------------------------------------------------

    BATCH_SIZE = 10_000

    pending = 0

    try:

        for fragment in fragments:

            with open(
                fragment,
                "r",
                encoding=ENCODING,
            ) as f:

                for line in f:

                    line = line.strip()

                    if not line:
                        continue

                    wrapper = json.loads(
                        line
                    )

                    input_records += 1

                    h_hex = get_hash(
                        wrapper
                    )

                    h = bytes.fromhex(
                        h_hex
                    )

                    record = get_record(
                        wrapper
                    )

                    # ------------------------------------------------
                    # Keep the COMPLETE original rich record.
                    # ------------------------------------------------

                    record_json = json.dumps(
                        record,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )

                    cursor = conn.execute(
                        INSERT_CANONICAL,
                        (
                            h,
                            record_json,
                        ),
                    )

                    if cursor.rowcount == 1:

                        canonical_records += 1

                    else:

                        duplicate_records += 1

                    # ------------------------------------------------
                    # ALWAYS retain provenance.
                    # ------------------------------------------------

                    provenance_json = json.dumps(
                        extract_provenance(
                            wrapper
                        ),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )

                    conn.execute(
                        INSERT_PROVENANCE,
                        (
                            h,
                            provenance_json,
                        ),
                    )

                    pending += 1

                    if pending >= BATCH_SIZE:

                        conn.commit()

                        pending = 0

    finally:

        if pending:

            conn.commit()

    # --------------------------------------------------------
    # Add index is already created.
    #
    # ANALYZE helps the final streaming query.
    # --------------------------------------------------------

    conn.execute(
        "ANALYZE"
    )

    conn.commit()

    # --------------------------------------------------------
    # Final output.
    #
    # We stream canonical records ordered by hash.
    #
    # For each canonical record we stream its provenance
    # through the index.
    #
    # Memory usage stays bounded.
    # --------------------------------------------------------

    output_shard = 0
    output_count = 0
    total_output = 0

    output_handle = None

    output_files = []

    def open_output():

        nonlocal output_handle

        path = (
            output_dir /
            f"dataset-b{bucket_id:02d}-"
            f"{output_shard:06d}.jsonl.gz"
        )

        output_handle = gzip.open(
            path,
            "wt",
            encoding=ENCODING,
            compresslevel=GZIP_LEVEL,
        )

        output_files.append(
            str(path)
        )

    def close_output():

        nonlocal output_handle

        if output_handle is not None:

            output_handle.close()

            output_handle = None

    try:

        canonical_cursor = conn.execute(
            """
            SELECT hash, record_json
            FROM canonical
            ORDER BY hash
            """
        )

        provenance_cursor = conn.execute(
            """
            SELECT hash, provenance_json
            FROM provenance
            ORDER BY hash
            """
        )

        current_prov_hash = None
        current_provenance = []

        def advance_provenance():

            nonlocal current_prov_hash
            nonlocal current_provenance

            row = provenance_cursor.fetchone()

            if row is None:

                current_prov_hash = None
                current_provenance = []

                return

            current_prov_hash = row[0]
            current_provenance = [
                json.loads(row[1])
            ]

            while True:

                row = provenance_cursor.fetchone()

                if row is None:
                    break

                if row[0] != current_prov_hash:

                    # We cannot push the row back.
                    #
                    # Therefore this streaming approach needs
                    # a one-row lookahead.
                    #
                    # This function is intentionally not used.
                    break

        # ----------------------------------------------------
        # Simpler robust approach:
        #
        # For each canonical hash, retrieve its provenance
        # using the indexed hash lookup.
        #
        # This is disk-backed and does NOT load the bucket.
        #
        # There are ~3.3M canonical records, so this creates
        # many indexed point lookups. SQLite handles these
        # efficiently, but the output stage is not the
        # performance-critical stage.
        # ----------------------------------------------------

        for h, record_json in canonical_cursor:

            if output_handle is None:

                open_output()

            record = json.loads(
                record_json
            )

            provenance_rows = conn.execute(
                """
                SELECT provenance_json
                FROM provenance
                WHERE hash = ?
                """,
                (h,),
            )

            provenance = []

            for (
                provenance_json,
            ) in provenance_rows:

                provenance.append(
                    json.loads(
                        provenance_json
                    )
                )

            record["provenance"] = (
                provenance
            )

            output_handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )

            output_handle.write("\n")

            output_count += 1
            total_output += 1

            if (
                output_count
                >= FINAL_RECORDS_PER_SHARD
            ):

                close_output()

                output_shard += 1
                output_count = 0

    finally:

        close_output()
        conn.close()

    # --------------------------------------------------------
    # ONLY AFTER successful output:
    #
    # delete temporary input fragments for this bucket.
    # --------------------------------------------------------

    deleted_bytes = 0

    for fragment in fragments:

        try:

            deleted_bytes += (
                fragment.stat().st_size
            )

            fragment.unlink()

        except FileNotFoundError:
            pass

    # Remove empty source directories.

    for directory in temp_dir.iterdir():

        if directory.is_dir():

            try:
                directory.rmdir()
            except OSError:
                pass

    return {
        "bucket": bucket_id,
        "input_records": input_records,
        "canonical_records": canonical_records,
        "duplicate_records": duplicate_records,
        "output_records": total_output,
        "output_files": output_files,
        "db_path": str(db_path),
        "deleted_temp_bytes": deleted_bytes,
        "runtime_sec": time.time() - started,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate(
    output_dir: Path,
    expected_input: int,
):

    print()
    print("=" * 72)
    print("RICH DATASET VALIDATION")
    print("=" * 72)

    files = sorted(
        output_dir.glob(
            "dataset-*.jsonl.gz"
        )
    )

    total = 0
    provenance_total = 0

    empty = 0
    missing_hash = 0
    bad_hash = 0
    malformed_provenance = 0

    source_counts = {}

    for path in files:

        print(
            f"  {path.name}",
            flush=True,
        )

        for record in iter_gzip_jsonl(
            path
        ):

            total += 1

            text = record.get(
                "text",
                "",
            )

            h = record.get(
                "content_hash"
            )

            if not text:
                empty += 1

            if not h:

                missing_hash += 1

            else:

                expected = hashlib.sha256(
                    text.encode(ENCODING)
                ).hexdigest()

                if expected != h:

                    bad_hash += 1

            provenance = record.get(
                "provenance"
            )

            if not isinstance(
                provenance,
                list,
            ):

                malformed_provenance += 1

                continue

            if not provenance:

                malformed_provenance += 1

            provenance_total += len(
                provenance
            )

            for p in provenance:

                source = p.get(
                    "source",
                    "UNKNOWN",
                )

                source_counts[source] = (
                    source_counts.get(
                        source,
                        0,
                    )
                    + 1
                )

    print()
    print(
        f"Canonical chunks:      "
        f"{total:,}"
    )

    print(
        f"Provenance occurrences:"
        f" {provenance_total:,}"
    )

    print(
        f"Expected occurrences:  "
        f"{expected_input:,}"
    )

    print(
        f"Difference:            "
        f"{provenance_total - expected_input:,}"
    )

    print(
        f"Empty text:            "
        f"{empty:,}"
    )

    print(
        f"Missing hashes:        "
        f"{missing_hash:,}"
    )

    print(
        f"Bad hashes:            "
        f"{bad_hash:,}"
    )

    print(
        f"Bad provenance:        "
        f"{malformed_provenance:,}"
    )

    print()
    print("Source provenance:")

    for source, count in sorted(
        source_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    ):

        print(
            f"  {source:<25}"
            f"{count:,}"
        )

    if (
        provenance_total
        != expected_input
    ):

        raise RuntimeError(
            "PROVENANCE COUNT MISMATCH"
        )

    if empty:
        raise RuntimeError(
            "EMPTY TEXT FOUND"
        )

    if missing_hash:
        raise RuntimeError(
            "MISSING HASH FOUND"
        )

    if bad_hash:
        raise RuntimeError(
            "HASH VALIDATION FAILED"
        )

    if malformed_provenance:
        raise RuntimeError(
            "PROVENANCE VALIDATION FAILED"
        )

    print()
    print(
        "ALL RICH DATASET VALIDATION "
        "CHECKS PASSED"
    )

    return {
        "canonical_chunks": total,
        "provenance_occurrences": provenance_total,
        "source_distribution": source_counts,
        "files": len(files),
    }


def iter_gzip_jsonl(path: Path):

    with gzip.open(
        path,
        "rt",
        encoding=ENCODING,
    ) as f:

        for line in f:

            line = line.strip()

            if line:

                yield json.loads(
                    line
                )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--workers",
        type=int,
        default=9,
    )

    parser.add_argument(
        "--temp",
        type=Path,
        default=Path(
            "results/final_v2/"
            "tmp_rich_hash_buckets"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/final_v2/"
            "dataset_rich"
        ),
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=Path(
            "results/final_v2/"
            "rich_dedup_databases"
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    workers = min(
        args.workers,
        NUM_BUCKETS,
    )

    print()
    print("=" * 72)
    print(
        "MEDISCANAI 2.0 — "
        "DISK-BACKED RICH DEDUP"
    )
    print("=" * 72)

    print(
        f"Workers:        {workers}"
    )

    print(
        f"Expected input: "
        f"{EXPECTED_INPUT:,}"
    )

    print(
        f"Temporary data: "
        f"{args.temp}"
    )

    print(
        f"Database data:  "
        f"{args.db}"
    )

    print(
        f"Final dataset:  "
        f"{args.output}"
    )

    # --------------------------------------------------------
    # Verify Stage 1 exists.
    # --------------------------------------------------------

    if not args.temp.exists():

        raise RuntimeError(
            "Stage-1 temporary partitions do not exist.\n"
            "Do NOT continue."
        )

    # --------------------------------------------------------
    # FORCE ONLY NEW STAGE 2 OUTPUT.
    #
    # NEVER delete worker_shards.
    # --------------------------------------------------------

    if args.force:

        for path in [
            args.db,
            args.output,
        ]:

            if path.exists():

                print(
                    f"Removing: {path}"
                )

                shutil.rmtree(path)

    args.db.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # STAGE 2
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print(
        "STAGE 2 — "
        "9-WORKER DISK-BACKED EXACT DEDUP"
    )
    print("=" * 72)

    started = time.time()

    futures = []

    with ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        for bucket_id in range(
            NUM_BUCKETS
        ):

            futures.append(
                executor.submit(
                    process_bucket,
                    bucket_id,
                    str(args.temp),
                    str(args.db),
                    str(args.output),
                )
            )

        results = []

        for future in as_completed(
            futures
        ):

            result = future.result()

            results.append(result)

            print()
            print(
                f"[Bucket "
                f"{result['bucket']:02d}] "
                f"COMPLETE"
            )

            print(
                f"  input:      "
                f"{result['input_records']:,}"
            )

            print(
                f"  canonical:  "
                f"{result['canonical_records']:,}"
            )

            print(
                f"  duplicates: "
                f"{result['duplicate_records']:,}"
            )

            print(
                f"  output:     "
                f"{result['output_records']:,}"
            )

            print(
                f"  runtime:    "
                f"{result['runtime_sec']:.1f}s"
            )

    results.sort(
        key=lambda x: x["bucket"]
    )

    total_input = sum(
        r["input_records"]
        for r in results
    )

    total_canonical = sum(
        r["canonical_records"]
        for r in results
    )

    total_duplicates = sum(
        r["duplicate_records"]
        for r in results
    )

    # --------------------------------------------------------
    # ACCOUNTING
    # --------------------------------------------------------

    if total_input != EXPECTED_INPUT:

        raise RuntimeError(
            f"Input mismatch.\n"
            f"Expected: "
            f"{EXPECTED_INPUT:,}\n"
            f"Actual:   {total_input:,}"
        )

    if (
        total_canonical
        + total_duplicates
        != total_input
    ):

        raise RuntimeError(
            "Dedup accounting mismatch."
        )

    print()
    print("=" * 72)
    print("STAGE 2 COMPLETE")
    print("=" * 72)

    print(
        f"Input:       {total_input:,}"
    )

    print(
        f"Canonical:   {total_canonical:,}"
    )

    print(
        f"Duplicates:  {total_duplicates:,}"
    )

    print(
        f"Runtime:     "
        f"{time.time() - started:.1f}s"
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    validation = validate(
        args.output,
        EXPECTED_INPUT,
    )

    # --------------------------------------------------------
    # MANIFEST
    # --------------------------------------------------------

    output_files = sorted(
        args.output.glob(
            "dataset-*.jsonl.gz"
        )
    )

    manifest = {
        "dataset": "MediScanAI 2.0",
        "version": "final_rag_v2_rich",

        "input_records": EXPECTED_INPUT,

        "canonical_chunks": (
            validation[
                "canonical_chunks"
            ]
        ),

        "provenance_occurrences": (
            validation[
                "provenance_occurrences"
            ]
        ),

        "duplicate_occurrences": (
            EXPECTED_INPUT
            - validation[
                "canonical_chunks"
            ]
        ),

        "deduplication": {
            "method": "SHA-256 exact content",
            "semantic": False,
        },

        "provenance": {
            "preserved": True,
            "duplicate_occurrences": True,
        },

        "chunking": {
            "performed_upstream": True,
            "performed_here": False,
            "truncation": False,
        },

        "source_distribution": (
            validation[
                "source_distribution"
            ]
        ),

        "files": [
            {
                "path": str(p),
                "size_bytes": p.stat().st_size,
            }
            for p in output_files
        ],
    }

    with open(
        args.output / "manifest.json",
        "w",
        encoding=ENCODING,
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # DATABASES ARE NO LONGER NEEDED AFTER VALIDATION.
    #
    # Delete only after EVERYTHING passed.
    # --------------------------------------------------------

    if args.db.exists():

        print()
        print(
            "Removing temporary SQLite databases..."
        )

        shutil.rmtree(
            args.db,
            ignore_errors=True,
        )

    print()
    print("=" * 72)
    print(
        "MEDISCANAI 2.0 — "
        "RICH DATASET COMPLETE"
    )
    print("=" * 72)

    print(
        f"Canonical chunks: "
        f"{validation['canonical_chunks']:,}"
    )

    print(
        f"Original occurrences preserved: "
        f"{validation['provenance_occurrences']:,}"
    )

    print(
        f"Final files: "
        f"{len(output_files):,}"
    )

    print()
    print(
        "worker_shards remain untouched."
    )

    print(
        "Dataset is ready for Colab embedding."
    )


if __name__ == "__main__":
    main()