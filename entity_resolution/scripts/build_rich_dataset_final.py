#!/usr/bin/env python3

"""
MediScanAI 2.0
FINAL RICH DATASET BUILDER

Input:
    results/final_v2/tmp_rich_hash_buckets/
    results/final_v2/dataset/

Output:
    results/final_v2/dataset_rich/

Properties:
    - 9 parallel workers
    - one independent hash bucket per worker
    - bounded RAM
    - disk-backed provenance index
    - exact SHA-256 identity
    - no re-chunking
    - no truncation
    - no semantic deduplication
    - complete structured provenance preservation
    - restart-safe bucket checkpoints

IMPORTANT:
    worker_shards/ is NEVER modified.
    tmp_rich_hash_buckets/ is NEVER deleted until
    the entire final dataset passes validation.
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
import zlib

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

WORKERS = 9
BUCKETS = 9

EXPECTED_CANONICAL = 3_338_170
EXPECTED_OCCURRENCES = 5_578_588

OUTPUT_RECORDS_PER_FILE = 75_000

SQL_INSERT_BATCH = 20_000

# Number of canonical hashes queried at once.
# Keeps memory tiny while avoiding millions of individual
# SQLite queries.
SQL_LOOKUP_BATCH = 500

GZIP_LEVEL = 3

ZLIB_LEVEL = 1

ENCODING = "utf-8"


# ============================================================
# PATHS
# ============================================================

DEFAULT_TEMP = Path(
    "results/final_v2/tmp_rich_hash_buckets"
)

DEFAULT_CANONICAL = Path(
    "results/final_v2/dataset"
)

DEFAULT_OUTPUT = Path(
    "results/final_v2/dataset_rich"
)

DEFAULT_DB = Path(
    "results/final_v2/rich_provenance_db"
)


# ============================================================
# JSONL HELPERS
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


def iter_gzip_jsonl(path: Path):

    with gzip.open(
        path,
        "rt",
        encoding=ENCODING,
    ) as f:

        for line in f:

            line = line.strip()

            if line:

                yield json.loads(line)


# ============================================================
# HASH / RECORD HELPERS
# ============================================================

def get_record(wrapper: dict) -> dict:

    record = wrapper.get("record")

    if not isinstance(record, dict):

        raise RuntimeError(
            "Worker/canonical record missing "
            "nested 'record'."
        )

    return record


def get_hash(wrapper: dict) -> str:

    record = get_record(wrapper)

    h = record.get("content_hash")

    if not h:

        raise RuntimeError(
            "Record missing content_hash."
        )

    return str(h)


# ============================================================
# RICH PROVENANCE
# ============================================================

def build_provenance(wrapper: dict) -> dict:
    """
    Preserve all useful occurrence-level information.

    We deliberately DO NOT duplicate the full text or hash.

    The canonical record already contains the text once.

    Everything else in the occurrence's record is retained,
    including structured medical metadata and enrichment.
    """

    record = get_record(wrapper)

    provenance = {
        # ----------------------------------------------------
        # Wrapper-level provenance
        # ----------------------------------------------------

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

        "chunk_index": wrapper.get(
            "chunk_index",
            record.get("chunk_index"),
        ),

        "chunk_count": wrapper.get(
            "chunk_count",
            record.get("chunk_count"),
        ),
    }

    # --------------------------------------------------------
    # Preserve the complete structured record metadata.
    #
    # Only text and content_hash are omitted because:
    #
    #   - text is identical by definition
    #   - content_hash is already the dictionary key
    #
    # Everything else stays.
    # --------------------------------------------------------

    metadata = {}

    for key, value in record.items():

        if key in {
            "text",
            "content_hash",
        }:

            continue

        metadata[key] = value

    provenance["record_metadata"] = metadata

    return provenance


# ============================================================
# SQLITE
# ============================================================

def open_provenance_db(path: Path):

    conn = sqlite3.connect(
        path,
        timeout=120,
    )

    # --------------------------------------------------------
    # This DB is disposable temporary working data.
    #
    # Source data remains untouched, so we optimize for speed
    # and disk usage rather than crash durability.
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
        "PRAGMA cache_size=-32768"
    )

    conn.execute(
        "PRAGMA mmap_size=268435456"
    )

    conn.execute(
        """
        CREATE TABLE occurrence (
            hash BLOB NOT NULL,
            seq INTEGER NOT NULL,
            provenance BLOB NOT NULL,
            PRIMARY KEY(hash, seq)
        ) WITHOUT ROWID
        """
    )

    conn.commit()

    return conn


# ============================================================
# DATABASE BUILD
# ============================================================

def build_bucket_database(
    bucket: int,
    temp_dir: Path,
    db_path: Path,
):

    started = time.time()

    fragments = sorted(
        temp_dir.glob(
            f"*/bucket_{bucket:02d}.jsonl"
        )
    )

    if not fragments:

        raise RuntimeError(
            f"No Stage-1 fragments found "
            f"for bucket {bucket:02d}."
        )

    if db_path.exists():

        db_path.unlink()

    conn = open_provenance_db(
        db_path
    )

    total = 0
    sequence = 0

    batch = []

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

                    h_hex = get_hash(
                        wrapper
                    )

                    h = bytes.fromhex(
                        h_hex
                    )

                    provenance = (
                        build_provenance(
                            wrapper
                        )
                    )

                    provenance_bytes = (
                        json.dumps(
                            provenance,
                            ensure_ascii=False,
                            separators=(
                                ",",
                                ":",
                            ),
                        ).encode(
                            ENCODING
                        )
                    )

                    # Low-level compression keeps the temporary
                    # DB substantially smaller.
                    compressed = zlib.compress(
                        provenance_bytes,
                        ZLIB_LEVEL,
                    )

                    batch.append(
                        (
                            h,
                            sequence,
                            compressed,
                        )
                    )

                    sequence += 1
                    total += 1

                    if len(batch) >= SQL_INSERT_BATCH:

                        conn.executemany(
                            """
                            INSERT INTO occurrence
                            (hash, seq, provenance)
                            VALUES (?, ?, ?)
                            """,
                            batch,
                        )

                        conn.commit()

                        batch.clear()

        if batch:

            conn.executemany(
                """
                INSERT INTO occurrence
                (hash, seq, provenance)
                VALUES (?, ?, ?)
                """,
                batch,
            )

            conn.commit()

            batch.clear()

        # ----------------------------------------------------
        # WITHOUT ROWID primary key is already ordered by
        # (hash, seq), so hash lookup is indexed naturally.
        # ----------------------------------------------------

        conn.execute(
            "ANALYZE"
        )

        conn.commit()

    finally:

        conn.close()

    return {
        "bucket": bucket,
        "records": total,
        "fragments": len(fragments),
        "runtime_sec": (
            time.time() - started
        ),
    }


# ============================================================
# CANONICAL FILE DISCOVERY
# ============================================================

def canonical_files(
    canonical_dir: Path,
    bucket: int,
):

    files = sorted(
        canonical_dir.glob(
            f"dataset-b{bucket:02d}-*.jsonl.gz"
        )
    )

    if not files:

        raise RuntimeError(
            f"No canonical files for "
            f"bucket {bucket:02d}."
        )

    return files


# ============================================================
# PROVENANCE LOOKUP
# ============================================================

def lookup_provenance_batch(
    conn,
    hashes: list[bytes],
):
    """
    Fetch provenance for a batch of canonical hashes.

    Only up to SQL_LOOKUP_BATCH hashes are held here.
    """

    if not hashes:

        return {}

    placeholders = ",".join(
        "?"
        for _ in hashes
    )

    cursor = conn.execute(
        f"""
        SELECT hash, provenance
        FROM occurrence
        WHERE hash IN ({placeholders})
        ORDER BY hash, seq
        """,
        hashes,
    )

    result = {}

    for h, compressed in cursor:

        provenance_bytes = (
            zlib.decompress(
                compressed
            )
        )

        provenance = json.loads(
            provenance_bytes.decode(
                ENCODING
            )
        )

        result.setdefault(
            h,
            [],
        ).append(
            provenance
        )

    return result


# ============================================================
# OUTPUT
# ============================================================

def write_bucket_output(
    bucket: int,
    canonical_dir: Path,
    db_path: Path,
    output_dir: Path,
):

    started = time.time()

    files = canonical_files(
        canonical_dir,
        bucket,
    )

    conn = sqlite3.connect(
        db_path,
        timeout=120,
    )

    # Read-only workload.
    conn.execute(
        "PRAGMA query_only=ON"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_files = []

    output_handle = None

    output_index = 0
    records_in_current = 0

    canonical_count = 0
    provenance_count = 0

    def open_output():

        nonlocal output_handle

        path = (
            output_dir
            /
            f"dataset-b{bucket:02d}-"
            f"{output_index:06d}.jsonl.gz"
        )

        output_handle = gzip.open(
            path,
            "wt",
            encoding=ENCODING,
            compresslevel=GZIP_LEVEL,
        )

        output_files.append(
            path
        )

    def close_output():

        nonlocal output_handle

        if output_handle is not None:

            output_handle.close()

            output_handle = None

    try:

        for canonical_path in files:

            canonical_batch = []

            for wrapper in iter_gzip_jsonl(
                canonical_path
            ):

                canonical_batch.append(
                    wrapper
                )

                if (
                    len(canonical_batch)
                    >= SQL_LOOKUP_BATCH
                ):

                    # --------------------------------------------
                    # Extract hashes.
                    # --------------------------------------------

                    hash_list = [
                        bytes.fromhex(
                            get_hash(w)
                        )
                        for w
                        in canonical_batch
                    ]

                    provenance_map = (
                        lookup_provenance_batch(
                            conn,
                            hash_list,
                        )
                    )

                    # --------------------------------------------
                    # Attach provenance and write.
                    # --------------------------------------------

                    for wrapper, h in zip(
                        canonical_batch,
                        hash_list,
                    ):

                        if h not in provenance_map:

                            raise RuntimeError(
                                "Canonical record has "
                                "no provenance."
                            )

                        provenance = (
                            provenance_map[h]
                        )

                        record = get_record(
                            wrapper
                        )

                        # ----------------------------------------
                        # Make a copy of the wrapper so that the
                        # source canonical object is never modified.
                        # ----------------------------------------

                        output_wrapper = dict(
                            wrapper
                        )

                        output_record = dict(
                            record
                        )

                        output_record[
                            "provenance"
                        ] = provenance

                        output_wrapper[
                            "record"
                        ] = output_record

                        if output_handle is None:

                            open_output()

                        output_handle.write(
                            json.dumps(
                                output_wrapper,
                                ensure_ascii=False,
                                separators=(
                                    ",",
                                    ":",
                                ),
                            )
                        )

                        output_handle.write(
                            "\n"
                        )

                        canonical_count += 1

                        provenance_count += (
                            len(provenance)
                        )

                        records_in_current += 1

                        if (
                            records_in_current
                            >= OUTPUT_RECORDS_PER_FILE
                        ):

                            close_output()

                            output_index += 1
                            records_in_current = 0

                    canonical_batch.clear()

            # ----------------------------------------------------
            # Flush final partial batch from this file.
            # ----------------------------------------------------

            if canonical_batch:

                hash_list = [
                    bytes.fromhex(
                        get_hash(w)
                    )
                    for w
                    in canonical_batch
                ]

                provenance_map = (
                    lookup_provenance_batch(
                        conn,
                        hash_list,
                    )
                )

                for wrapper, h in zip(
                    canonical_batch,
                    hash_list,
                ):

                    if h not in provenance_map:

                        raise RuntimeError(
                            "Canonical record has "
                            "no provenance."
                        )

                    provenance = (
                        provenance_map[h]
                    )

                    record = get_record(
                        wrapper
                    )

                    output_wrapper = dict(
                        wrapper
                    )

                    output_record = dict(
                        record
                    )

                    output_record[
                        "provenance"
                    ] = provenance

                    output_wrapper[
                        "record"
                    ] = output_record

                    if output_handle is None:

                        open_output()

                    output_handle.write(
                        json.dumps(
                            output_wrapper,
                            ensure_ascii=False,
                            separators=(
                                ",",
                                ":",
                            ),
                        )
                    )

                    output_handle.write(
                        "\n"
                    )

                    canonical_count += 1

                    provenance_count += (
                        len(provenance)
                    )

                    records_in_current += 1

                    if (
                        records_in_current
                        >= OUTPUT_RECORDS_PER_FILE
                    ):

                        close_output()

                        output_index += 1
                        records_in_current = 0

                canonical_batch.clear()

    finally:

        close_output()
        conn.close()

    return {
        "bucket": bucket,
        "canonical_records": canonical_count,
        "provenance_records": provenance_count,
        "output_files": [
            str(p)
            for p in output_files
        ],
        "runtime_sec": (
            time.time() - started
        ),
    }


# ============================================================
# COMPLETE BUCKET
# ============================================================

def process_bucket(
    bucket: int,
    temp_dir: str,
    canonical_dir: str,
    db_dir: str,
    output_dir: str,
):

    temp_dir = Path(temp_dir)
    canonical_dir = Path(canonical_dir)
    db_dir = Path(db_dir)
    output_dir = Path(output_dir)

    db_path = (
        db_dir /
        f"bucket_{bucket:02d}.sqlite"
    )

    marker = (
        db_dir /
        f"bucket_{bucket:02d}.complete"
    )

    bucket_output_prefix = (
        output_dir /
        f"dataset-b{bucket:02d}-"
    )

    # --------------------------------------------------------
    # Restart support.
    # --------------------------------------------------------

    if marker.exists():

        return {
            "bucket": bucket,
            "skipped": True,
        }

    # --------------------------------------------------------
    # Remove partial output/DB from a previously interrupted
    # bucket.
    # --------------------------------------------------------

    for path in output_dir.glob(
        f"dataset-b{bucket:02d}-*.jsonl.gz"
    ):

        path.unlink()

    if db_path.exists():

        db_path.unlink()

    # --------------------------------------------------------
    # Stage A — build disk-backed provenance DB.
    # --------------------------------------------------------

    db_result = build_bucket_database(
        bucket,
        temp_dir,
        db_path,
    )

    # --------------------------------------------------------
    # Stage B — stream canonical records and attach provenance.
    # --------------------------------------------------------

    output_result = write_bucket_output(
        bucket,
        canonical_dir,
        db_path,
        output_dir,
    )

    # --------------------------------------------------------
    # Local bucket validation.
    # --------------------------------------------------------

    expected_bucket_occurrences = (
        db_result["records"]
    )

    if (
        output_result[
            "provenance_records"
        ]
        != expected_bucket_occurrences
    ):

        raise RuntimeError(
            f"Bucket {bucket:02d} provenance "
            f"mismatch.\n"
            f"Expected: "
            f"{expected_bucket_occurrences:,}\n"
            f"Actual: "
            f"{output_result['provenance_records']:,}"
        )

    # --------------------------------------------------------
    # Completion marker.
    # --------------------------------------------------------

    marker_data = {
        "bucket": bucket,
        "input_records": (
            db_result["records"]
        ),
        "canonical_records": (
            output_result[
                "canonical_records"
            ]
        ),
        "provenance_records": (
            output_result[
                "provenance_records"
            ]
        ),
        "output_files": (
            output_result[
                "output_files"
            ]
        ),
    }

    with open(
        marker,
        "w",
        encoding=ENCODING,
    ) as f:

        json.dump(
            marker_data,
            f,
            indent=2,
        )

    return {
        "bucket": bucket,
        "skipped": False,
        **db_result,
        **output_result,
    }


# ============================================================
# FINAL VALIDATION
# ============================================================

def validate_final(
    output_dir: Path,
):

    print()
    print("=" * 72)
    print(
        "FINAL RICH DATASET VALIDATION"
    )
    print("=" * 72)

    files = sorted(
        output_dir.glob(
            "dataset-*.jsonl.gz"
        )
    )

    total_canonical = 0
    total_provenance = 0

    bad_hash = 0
    missing_hash = 0
    empty_text = 0
    bad_provenance = 0

    source_distribution = {}

    # --------------------------------------------------------
    # Each bucket should have exactly the expected number
    # of canonical records.
    # --------------------------------------------------------

    bucket_counts = {}

    for path in files:

        bucket = int(
            path.name.split("-")[1][1:]
        )

        for wrapper in iter_gzip_jsonl(
            path
        ):

            total_canonical += 1

            bucket_counts[bucket] = (
                bucket_counts.get(
                    bucket,
                    0,
                )
                + 1
            )

            record = get_record(
                wrapper
            )

            text = record.get(
                "text",
                "",
            )

            h = record.get(
                "content_hash"
            )

            if not text:

                empty_text += 1

            if not h:

                missing_hash += 1

            else:

                expected = hashlib.sha256(
                    text.encode(
                        ENCODING
                    )
                ).hexdigest()

                if expected != h:

                    bad_hash += 1

            provenance = record.get(
                "provenance"
            )

            if not isinstance(
                provenance,
                list,
            ) or not provenance:

                bad_provenance += 1

                continue

            total_provenance += len(
                provenance
            )

            for item in provenance:

                source = item.get(
                    "source",
                    "UNKNOWN",
                )

                source_distribution[
                    source
                ] = (
                    source_distribution.get(
                        source,
                        0,
                    )
                    + 1
                )

    print()
    print(
        f"Canonical chunks:      "
        f"{total_canonical:,}"
    )

    print(
        f"Expected canonical:    "
        f"{EXPECTED_CANONICAL:,}"
    )

    print(
        f"Provenance occurrences:"
        f" {total_provenance:,}"
    )

    print(
        f"Expected occurrences:  "
        f"{EXPECTED_OCCURRENCES:,}"
    )

    print(
        f"Bad SHA-256:           "
        f"{bad_hash:,}"
    )

    print(
        f"Missing hash:          "
        f"{missing_hash:,}"
    )

    print(
        f"Empty text:            "
        f"{empty_text:,}"
    )

    print(
        f"Bad provenance:        "
        f"{bad_provenance:,}"
    )

    print()
    print("Bucket counts:")

    for bucket in range(BUCKETS):

        print(
            f"  b{bucket:02d}: "
            f"{bucket_counts.get(bucket, 0):,}"
        )

    print()
    print(
        "Source provenance distribution:"
    )

    for source, count in sorted(
        source_distribution.items(),
        key=lambda x: x[1],
        reverse=True,
    ):

        print(
            f"  {source:<25}"
            f"{count:,}"
        )

    # --------------------------------------------------------
    # HARD VALIDATION
    # --------------------------------------------------------

    if (
        total_canonical
        != EXPECTED_CANONICAL
    ):

        raise RuntimeError(
            "CANONICAL COUNT MISMATCH"
        )

    if (
        total_provenance
        != EXPECTED_OCCURRENCES
    ):

        raise RuntimeError(
            "PROVENANCE COUNT MISMATCH"
        )

    if bad_hash:

        raise RuntimeError(
            "HASH VALIDATION FAILED"
        )

    if missing_hash:

        raise RuntimeError(
            "MISSING HASH FOUND"
        )

    if empty_text:

        raise RuntimeError(
            "EMPTY TEXT FOUND"
        )

    if bad_provenance:

        raise RuntimeError(
            "BAD PROVENANCE FOUND"
        )

    print()
    print(
        "ALL FINAL RICH DATASET "
        "VALIDATION CHECKS PASSED"
    )

    return {
        "canonical_records": total_canonical,
        "provenance_records": total_provenance,
        "files": len(files),
        "source_distribution": (
            source_distribution
        ),
        "bucket_counts": bucket_counts,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--workers",
        type=int,
        default=WORKERS,
    )

    parser.add_argument(
        "--temp",
        type=Path,
        default=DEFAULT_TEMP,
    )

    parser.add_argument(
        "--canonical",
        type=Path,
        default=DEFAULT_CANONICAL,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    workers = min(
        args.workers,
        BUCKETS,
        os.cpu_count() or args.workers,
    )

    print()
    print("=" * 72)
    print(
        "MEDISCANAI 2.0"
    )
    print(
        "FINAL MEMORY-SAFE RICH DATASET"
    )
    print("=" * 72)

    print(
        f"Workers:             {workers}"
    )

    print(
        f"Canonical chunks:    "
        f"{EXPECTED_CANONICAL:,}"
    )

    print(
        f"Input occurrences:   "
        f"{EXPECTED_OCCURRENCES:,}"
    )

    print(
        f"Stage-1 partitions:  "
        f"{args.temp}"
    )

    print(
        f"Canonical dataset:   "
        f"{args.canonical}"
    )

    print(
        f"Temporary DBs:       "
        f"{args.db}"
    )

    print(
        f"Final dataset:       "
        f"{args.output}"
    )

    # --------------------------------------------------------
    # SAFETY CHECKS
    # --------------------------------------------------------

    if not args.temp.exists():

        raise RuntimeError(
            "Stage-1 partitions are missing."
        )

    if not args.canonical.exists():

        raise RuntimeError(
            "Canonical dataset is missing."
        )

    # --------------------------------------------------------
    # --force NEVER touches worker_shards or Stage-1 data.
    # --------------------------------------------------------

    if args.force:

        if args.db.exists():

            shutil.rmtree(
                args.db
            )

        if args.output.exists():

            shutil.rmtree(
                args.output
            )

    args.db.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # 9 WORKERS
    # ========================================================

    print()
    print("=" * 72)
    print(
        "9-WORKER RICH DATASET BUILD"
    )
    print("=" * 72)

    started = time.time()

    futures = []

    with ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        for bucket in range(
            BUCKETS
        ):

            futures.append(
                executor.submit(
                    process_bucket,
                    bucket,
                    str(args.temp),
                    str(args.canonical),
                    str(args.db),
                    str(args.output),
                )
            )

        results = []

        for future in as_completed(
            futures
        ):

            result = future.result()

            results.append(
                result
            )

            if result.get(
                "skipped",
                False,
            ):

                print(
                    f"[bucket "
                    f"{result['bucket']:02d}] "
                    f"already complete"
                )

            else:

                print()
                print(
                    f"[bucket "
                    f"{result['bucket']:02d}] "
                    f"COMPLETE"
                )

                print(
                    f"  input:       "
                    f"{result['records']:,}"
                )

                print(
                    f"  canonical:   "
                    f"{result['canonical_records']:,}"
                )

                print(
                    f"  provenance:  "
                    f"{result['provenance_records']:,}"
                )

                print(
                    f"  time:        "
                    f"{result['runtime_sec']:.1f}s"
                )

    print()
    print(
        f"Build runtime: "
        f"{time.time() - started:.1f}s"
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    validation = validate_final(
        args.output
    )

    # ========================================================
    # MANIFEST
    # ========================================================

    output_files = sorted(
        args.output.glob(
            "dataset-*.jsonl.gz"
        )
    )

    manifest = {
        "dataset": "MediScanAI 2.0",

        "version": (
            "final_rag_v2_rich"
        ),

        "canonical_chunks": (
            validation[
                "canonical_records"
            ]
        ),

        "input_occurrences": (
            validation[
                "provenance_records"
            ]
        ),

        "duplicate_occurrences": (
            validation[
                "provenance_records"
            ]
            -
            validation[
                "canonical_records"
            ]
        ),

        "deduplication": {
            "type": "exact SHA-256 content",
            "semantic": False,
            "rechunking": False,
            "truncation": False,
        },

        "provenance": {
            "preserved": True,
            "structured_metadata": True,
            "text_duplicated": False,
        },

        "architecture": {
            "workers": workers,
            "bucket_count": BUCKETS,
            "memory_bounded": True,
            "disk_backed_provenance": True,
        },

        "source_distribution": (
            validation[
                "source_distribution"
            ]
        ),

        "files": [
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
            for path in output_files
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

    # ========================================================
    # ONLY NOW DELETE TEMPORARY DATA
    # ========================================================

    print()
    print(
        "Validation succeeded."
    )

    print(
        "Removing temporary provenance DBs..."
    )

    shutil.rmtree(
        args.db,
        ignore_errors=True,
    )

    print(
        "Removing Stage-1 temporary partitions..."
    )

    shutil.rmtree(
        args.temp,
        ignore_errors=True,
    )

    print()
    print("=" * 72)
    print(
        "FINAL RICH DATASET READY"
    )
    print("=" * 72)

    print(
        f"Canonical chunks: "
        f"{validation['canonical_records']:,}"
    )

    print(
        f"Occurrences preserved: "
        f"{validation['provenance_records']:,}"
    )

    print(
        f"Output files: "
        f"{len(output_files):,}"
    )

    print()
    print(
        "worker_shards/ was NOT modified."
    )

    print(
        "CPU DATASET BUILD COMPLETE."
    )


if __name__ == "__main__":
    main()