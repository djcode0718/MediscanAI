#!/usr/bin/env python3

"""
MediScanAI 2.0
Parallel Final RAG V2 Merge

IMPORTANT
---------
This script REUSES the existing V2 worker shards.

It does NOT rerun:
    - input parsing
    - semantic chunking
    - normalization

Pipeline
--------
Existing worker shards
        |
        | 9 workers
        v
Hash partitioning
        |
        | 9 workers
        v
Exact per-bucket deduplication
        |
        v
Deterministic final merge
        |
        v
Final RAG JSONL

The expensive merge work is therefore actually parallelized.

Expected existing shards:
    results/final_v2/worker_shards/*.jsonl

Output:
    results/final_v2/parallel_merge/
        partitions/
        unique_buckets/
        final/
            mediscanai_rag_v2.jsonl
            document_dedup.sqlite
            rag_manifest.json

Usage
-----
python scripts/parallel_merge_final_rag_v2.py --workers 9

Optional gzip archive:
python scripts/parallel_merge_final_rag_v2.py --workers 9 --gzip-final

Force only the PARALLEL MERGE to rebuild:
python scripts/parallel_merge_final_rag_v2.py --workers 9 --force

NOTE:
    --force does NOT delete the original worker_shards.
"""


from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import heapq
import json
import os
import shutil
import sqlite3
import time

from pathlib import Path
from dataclasses import dataclass

from tqdm import tqdm


# ============================================================================
# PATHS
# ============================================================================

BASE = Path(
    "/Users/sj/Documents/mediscanai/entity_resolution"
)

V2_ROOT = BASE / "results" / "final_v2"

SHARD_ROOT = V2_ROOT / "worker_shards"

MERGE_ROOT = V2_ROOT / "parallel_merge"

PARTITION_ROOT = MERGE_ROOT / "partitions"

UNIQUE_ROOT = MERGE_ROOT / "unique_buckets"

FINAL_ROOT = MERGE_ROOT / "final"

FINAL_JSONL = (
    FINAL_ROOT / "mediscanai_rag_v2.jsonl"
)

FINAL_JSONL_GZ = (
    FINAL_ROOT / "mediscanai_rag_v2.jsonl.gz"
)

SQLITE_PATH = (
    FINAL_ROOT / "document_dedup.sqlite"
)

MANIFEST_PATH = (
    FINAL_ROOT / "rag_manifest.json"
)

COMPLETE_PATH = (
    FINAL_ROOT / "merge_complete.json"
)


# ============================================================================
# CONFIG
# ============================================================================

DEFAULT_WORKERS = 9

BUCKETS = 9

MAX_CHARS = 10000

MIN_CHARS = 40

SQLITE_BATCH = 10000


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def sha256_text(text: str) -> str:

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def clean_dirs_for_force():

    for path in (
        PARTITION_ROOT,
        UNIQUE_ROOT,
        FINAL_ROOT,
    ):

        if path.exists():
            shutil.rmtree(path)

    PARTITION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    UNIQUE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINAL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def ensure_dirs():

    PARTITION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    UNIQUE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINAL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================================
# SHARD DISCOVERY
# ============================================================================

def discover_shards() -> list[Path]:

    if not SHARD_ROOT.exists():
        raise FileNotFoundError(
            f"Worker shard directory does not exist:\n"
            f"{SHARD_ROOT}"
        )

    shards = sorted(
        p
        for p in SHARD_ROOT.glob("*.jsonl")
        if p.is_file()
    )

    if not shards:
        raise RuntimeError(
            f"No worker shards found in:\n"
            f"{SHARD_ROOT}"
        )

    return shards


# ============================================================================
# GLOBAL ORDER
# ============================================================================

def shard_worker_assignment(
    shards: list[Path],
    workers: int,
) -> list[list[tuple[int, Path]]]:
    """
    Divide shards into contiguous ranges.

    This guarantees that each worker reads its input
    in deterministic global file order.
    """

    groups = [[] for _ in range(workers)]

    n = len(shards)

    base = n // workers
    remainder = n % workers

    cursor = 0

    for worker_id in range(workers):

        count = (
            base + 1
            if worker_id < remainder
            else base
        )

        for _ in range(count):

            if cursor >= n:
                break

            groups[worker_id].append(
                (cursor, shards[cursor])
            )

            cursor += 1

    return groups


# ============================================================================
# STAGE 1
# PARALLEL HASH PARTITIONING
# ============================================================================

@dataclass
class PartitionResult:

    worker_id: int

    records: int

    buckets_written: int

    elapsed: float

    output_files: list[str]


def partition_worker(
    worker_id: int,
    shard_entries: list[tuple[int, str]],
) -> PartitionResult:

    start = time.time()

    worker_root = (
        PARTITION_ROOT
        / f"worker_{worker_id:02d}"
    )

    worker_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    # One output per hash bucket.
    handles = {}

    output_files = []

    try:

        for bucket in range(BUCKETS):

            path = (
                worker_root
                / f"bucket_{bucket:02d}.jsonl"
            )

            handles[bucket] = open(
                path,
                "w",
                encoding="utf-8",
            )

            output_files.append(
                str(path)
            )

        records = 0
        buckets_written = 0

        for global_file_index, shard_string in shard_entries:

            shard_path = Path(shard_string)

            with open(
                shard_path,
                "r",
                encoding="utf-8",
            ) as f:

                for local_line, line in enumerate(
                    f,
                    start=1,
                ):

                    wrapper = json.loads(line)

                    record = wrapper["record"]

                    content_hash = record.get(
                        "content_hash"
                    )

                    if not content_hash:

                        text = str(
                            record.get("text", "")
                        )

                        content_hash = sha256_text(
                            text
                        )

                        record["content_hash"] = (
                            content_hash
                        )

                    # Hash determines bucket.
                    #
                    # Identical hashes ALWAYS land in
                    # exactly the same bucket.
                    bucket = (
                        int(
                            content_hash[:16],
                            16,
                        )
                        % BUCKETS
                    )

                    # Global ordinal preserves exact
                    # original deterministic order.
                    #
                    # The shard itself corresponds to
                    # one input file and the line number
                    # is deterministic.
                    wrapper["_global_order"] = (
                        global_file_index,
                        local_line,
                    )

                    handles[bucket].write(
                        json.dumps(
                            wrapper,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )

                    records += 1

                    buckets_written += 1

        return PartitionResult(
            worker_id=worker_id,
            records=records,
            buckets_written=buckets_written,
            elapsed=time.time() - start,
            output_files=output_files,
        )

    finally:

        for handle in handles.values():
            handle.close()


# ============================================================================
# STAGE 2
# PARALLEL EXACT DEDUPLICATION
# ============================================================================

@dataclass
class BucketResult:

    bucket: int

    input_records: int

    unique_records: int

    duplicate_records: int

    elapsed: float

    output_path: str


def iter_partition_file(
    path: Path,
):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            wrapper = json.loads(line)

            order = tuple(
                wrapper["_global_order"]
            )

            yield (
                order,
                wrapper,
            )


def merge_sorted_streams(
    paths: list[Path],
):
    """
    K-way merge of partition streams.

    Each Stage-1 worker preserves global input order.
    """

    streams = []

    heap = []

    for stream_id, path in enumerate(paths):

        iterator = iter_partition_file(path)

        streams.append(iterator)

        try:
            order, wrapper = next(iterator)

            heapq.heappush(
                heap,
                (
                    order,
                    stream_id,
                    wrapper,
                ),
            )

        except StopIteration:
            pass

    while heap:

        order, stream_id, wrapper = heapq.heappop(
            heap
        )

        yield wrapper

        iterator = streams[stream_id]

        try:

            next_order, next_wrapper = next(
                iterator
            )

            heapq.heappush(
                heap,
                (
                    next_order,
                    stream_id,
                    next_wrapper,
                ),
            )

        except StopIteration:
            pass


def dedup_bucket_worker(
    bucket: int,
    partition_paths: list[str],
) -> BucketResult:

    start = time.time()

    output_path = (
        UNIQUE_ROOT
        / f"bucket_{bucket:02d}.jsonl"
    )

    seen = set()

    input_records = 0
    unique_records = 0
    duplicate_records = 0

    # IMPORTANT:
    #
    # All records with the same content hash are
    # guaranteed to be in this bucket.
    #
    # Therefore this set performs EXACT global
    # deduplication, not merely local deduplication.
    #
    # The bucket is only ~1/9 of the complete dataset.
    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as out:

        paths = [
            Path(x)
            for x in partition_paths
            if Path(x).exists()
            and Path(x).stat().st_size > 0
        ]

        for wrapper in merge_sorted_streams(
            paths
        ):

            input_records += 1

            record = wrapper["record"]

            content_hash = record.get(
                "content_hash"
            )

            if not content_hash:

                text = str(
                    record.get("text", "")
                )

                content_hash = sha256_text(
                    text
                )

                record["content_hash"] = (
                    content_hash
                )

            if content_hash in seen:

                duplicate_records += 1

                continue

            seen.add(content_hash)

            # We don't need internal routing metadata
            # in the final RAG document.
            wrapper.pop(
                "_global_order",
                None,
            )

            out.write(
                json.dumps(
                    wrapper,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

            unique_records += 1

    return BucketResult(
        bucket=bucket,
        input_records=input_records,
        unique_records=unique_records,
        duplicate_records=duplicate_records,
        elapsed=time.time() - start,
        output_path=str(output_path),
    )


# ============================================================================
# SQLITE
# ============================================================================

def initialize_sqlite():

    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()

    conn = sqlite3.connect(
        str(SQLITE_PATH)
    )

    conn.execute(
        "PRAGMA journal_mode=WAL"
    )

    conn.execute(
        "PRAGMA synchronous=NORMAL"
    )

    conn.execute(
        "PRAGMA temp_store=MEMORY"
    )

    conn.executescript(
        """
        CREATE TABLE documents (
            rag_index INTEGER PRIMARY KEY,
            content_hash TEXT NOT NULL UNIQUE,
            document_id TEXT,
            source TEXT NOT NULL,
            source_file TEXT,
            source_line INTEGER,
            chunk_index INTEGER,
            chunk_count INTEGER
        );

        CREATE INDEX idx_documents_hash
        ON documents(content_hash);

        CREATE INDEX idx_documents_document
        ON documents(document_id);

        CREATE INDEX idx_documents_source
        ON documents(source);

        CREATE TABLE provenance (
            content_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_line INTEGER NOT NULL,
            original_document_id TEXT,
            chunk_index INTEGER,
            chunk_count INTEGER
        );

        CREATE INDEX idx_provenance_hash
        ON provenance(content_hash);

        CREATE INDEX idx_provenance_document
        ON provenance(original_document_id);
        """
    )

    conn.commit()

    return conn


# ============================================================================
# FINAL DETERMINISTIC MERGE
# ============================================================================

def final_merge(
    bucket_results: list[BucketResult],
):

    print()
    print("=" * 78)
    print("FINAL DETERMINISTIC MERGE")
    print("=" * 78)

    start = time.time()

    # Each bucket is independently sorted by the
    # original global order.
    #
    # We now perform a 9-way merge.
    streams = []

    heap = []

    for bucket_index, result in enumerate(
        sorted(
            bucket_results,
            key=lambda x: x.bucket,
        )
    ):

        path = Path(
            result.output_path
        )

        f = open(
            path,
            "r",
            encoding="utf-8",
        )

        streams.append(f)

        try:

            wrapper = json.loads(
                f.readline()
            )

            order = tuple(
                wrapper["_global_order"]
                if "_global_order" in wrapper
                else (
                    10**12,
                    bucket_index,
                )
            )

            heapq.heappush(
                heap,
                (
                    order,
                    bucket_index,
                    wrapper,
                ),
            )

        except Exception:

            f.close()

    conn = initialize_sqlite()

    rag_index = 0
    provenance_count = 0

    with open(
        FINAL_JSONL,
        "w",
        encoding="utf-8",
    ) as final_out:

        while heap:

            order, bucket_index, wrapper = (
                heapq.heappop(heap)
            )

            record = wrapper["record"]

            content_hash = record.get(
                "content_hash"
            )

            source = wrapper["source"]

            source_file = wrapper[
                "source_file"
            ]

            source_line = int(
                wrapper["source_line"]
            )

            document_id = str(
                wrapper["original_document_id"]
            )

            chunk_index = int(
                wrapper["chunk_index"]
            )

            chunk_count = int(
                wrapper["chunk_count"]
            )

            text = str(
                record.get("text", "")
            )

            # --------------------------------------------------------------
            # Provenance
            # --------------------------------------------------------------

            conn.execute(
                """
                INSERT INTO provenance (
                    content_hash,
                    source,
                    source_file,
                    source_line,
                    original_document_id,
                    chunk_index,
                    chunk_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_hash,
                    source,
                    source_file,
                    source_line,
                    document_id,
                    chunk_index,
                    chunk_count,
                ),
            )

            provenance_count += 1

            # --------------------------------------------------------------
            # Final document
            # --------------------------------------------------------------

            record["rag_index"] = rag_index

            final_out.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

            conn.execute(
                """
                INSERT INTO documents (
                    rag_index,
                    content_hash,
                    document_id,
                    source,
                    source_file,
                    source_line,
                    chunk_index,
                    chunk_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rag_index,
                    content_hash,
                    document_id,
                    source,
                    source_file,
                    source_line,
                    chunk_index,
                    chunk_count,
                ),
            )

            rag_index += 1

            if (
                provenance_count
                % SQLITE_BATCH
                == 0
            ):
                conn.commit()

            # --------------------------------------------------------------
            # Advance that bucket's stream
            # --------------------------------------------------------------

            f = streams[bucket_index]

            line = f.readline()

            if line:

                next_wrapper = json.loads(
                    line
                )

                next_order = tuple(
                    next_wrapper["_global_order"]
                    if "_global_order"
                    in next_wrapper
                    else (
                        10**12,
                        bucket_index,
                    )
                )

                heapq.heappush(
                    heap,
                    (
                        next_order,
                        bucket_index,
                        next_wrapper,
                    ),
                )

    for f in streams:
        f.close()

    conn.commit()

    # Remove WAL into the main DB.
    conn.execute(
        "PRAGMA wal_checkpoint(TRUNCATE)"
    )

    conn.close()

    elapsed = time.time() - start

    return {
        "unique_documents": rag_index,
        "provenance": provenance_count,
        "elapsed_seconds": elapsed,
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate(
    expected_input: int,
    expected_unique: int,
    expected_duplicates: int,
    expected_provenance: int,
):

    print()
    print("=" * 78)
    print("FINAL VALIDATION")
    print("=" * 78)

    start = time.time()

    conn = sqlite3.connect(
        str(SQLITE_PATH)
    )

    sqlite_docs = conn.execute(
        "SELECT COUNT(*) FROM documents"
    ).fetchone()[0]

    sqlite_provenance = conn.execute(
        "SELECT COUNT(*) FROM provenance"
    ).fetchone()[0]

    conn.close()

    json_lines = 0

    unique_hashes = set()

    invalid_json = 0
    missing_text = 0
    oversized = 0
    bad_hash = 0
    missing_hash = 0

    last_index = -1

    with open(
        FINAL_JSONL,
        "r",
        encoding="utf-8",
    ) as f:

        for line in tqdm(
            f,
            desc="Validating final",
            unit=" docs",
        ):

            json_lines += 1

            try:
                record = json.loads(
                    line
                )

            except Exception:
                invalid_json += 1
                continue

            text = record.get(
                "text"
            )

            if not text:
                missing_text += 1
                continue

            if len(text) > MAX_CHARS:
                oversized += 1

            content_hash = record.get(
                "content_hash"
            )

            if not content_hash:

                missing_hash += 1

            else:

                unique_hashes.add(
                    content_hash
                )

                if (
                    sha256_text(text)
                    != content_hash
                ):
                    bad_hash += 1

            index = record.get(
                "rag_index"
            )

            if index != last_index + 1:
                raise RuntimeError(
                    "rag_index is not contiguous"
                )

            last_index = index

    elapsed = time.time() - start

    print()
    print(
        f"Input records       : {expected_input:,}"
    )

    print(
        f"Expected unique     : {expected_unique:,}"
    )

    print(
        f"Expected duplicates : {expected_duplicates:,}"
    )

    print(
        f"Final JSON records  : {json_lines:,}"
    )

    print(
        f"Unique hashes       : {len(unique_hashes):,}"
    )

    print(
        f"SQLite documents    : {sqlite_docs:,}"
    )

    print(
        f"SQLite provenance   : {sqlite_provenance:,}"
    )

    print(
        f"Invalid JSON        : {invalid_json:,}"
    )

    print(
        f"Missing text        : {missing_text:,}"
    )

    print(
        f"Oversized           : {oversized:,}"
    )

    print(
        f"Missing hash        : {missing_hash:,}"
    )

    print(
        f"Bad SHA-256         : {bad_hash:,}"
    )

    print(
        f"Validation time     : {elapsed:.1f}s"
    )

    failures = []

    if json_lines != expected_unique:
        failures.append(
            "JSON record count mismatch"
        )

    if len(unique_hashes) != expected_unique:
        failures.append(
            "duplicate final content hashes"
        )

    if sqlite_docs != expected_unique:
        failures.append(
            "SQLite document count mismatch"
        )

    if sqlite_provenance != expected_provenance:
        failures.append(
            "SQLite provenance mismatch"
        )

    if invalid_json:
        failures.append(
            "invalid JSON"
        )

    if missing_text:
        failures.append(
            "missing text"
        )

    if oversized:
        failures.append(
            "oversized text"
        )

    if missing_hash:
        failures.append(
            "missing content hash"
        )

    if bad_hash:
        failures.append(
            "bad SHA-256"
        )

    if failures:

        raise RuntimeError(
            "VALIDATION FAILED:\n"
            + "\n".join(
                f" - {x}"
                for x in failures
            )
        )

    print()
    print(
        "ALL PARALLEL RAG V2 VALIDATION CHECKS PASSED"
    )


# ============================================================================
# OPTIONAL GZIP
# ============================================================================

def gzip_final():

    print()
    print(
        "Creating optional final gzip archive..."
    )

    start = time.time()

    with open(
        FINAL_JSONL,
        "rb",
    ) as src:

        with gzip.open(
            FINAL_JSONL_GZ,
            "wb",
            compresslevel=6,
        ) as dst:

            shutil.copyfileobj(
                src,
                dst,
                length=8 * 1024 * 1024,
            )

    print(
        f"Gzip completed in "
        f"{time.time() - start:.1f}s"
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--workers",
        type=int,
        default=9,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    parser.add_argument(
        "--gzip-final",
        action="store_true",
    )

    args = parser.parse_args()

    workers = min(
        max(1, args.workers),
        BUCKETS,
    )

    print("=" * 78)
    print(
        "MEDISCANAI 2.0 — PARALLEL FINAL RAG MERGE"
    )
    print("=" * 78)

    print(
        f"Workers : {workers}"
    )

    print(
        f"Buckets : {BUCKETS}"
    )

    print(
        f"Shard root : {SHARD_ROOT}"
    )

    print(
        f"Merge root : {MERGE_ROOT}"
    )

    # ------------------------------------------------------------------
    # Discover existing shards
    # ------------------------------------------------------------------

    shards = discover_shards()

    print()
    print(
        f"Existing worker shards : {len(shards)}"
    )

    if len(shards) != 237:

        print(
            "WARNING: expected 237 shards, "
            f"found {len(shards)}"
        )

    # ------------------------------------------------------------------
    # Clean merge artifacts only
    # ------------------------------------------------------------------

    if args.force:

        print()
        print(
            "FORCE: clearing parallel merge artifacts..."
        )

        clean_dirs_for_force()

    else:

        ensure_dirs()

    # ------------------------------------------------------------------
    # STAGE 1
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print(
        "STAGE 1 — 9-WORKER HASH PARTITIONING"
    )
    print("=" * 78)

    assignments = shard_worker_assignment(
        shards,
        workers,
    )

    partition_start = time.time()

    partition_results = []

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = []

        for worker_id in range(workers):

            entries = [
                (
                    file_index,
                    str(path),
                )
                for file_index, path
                in assignments[worker_id]
            ]

            futures.append(
                executor.submit(
                    partition_worker,
                    worker_id,
                    entries,
                )
            )

        for future in tqdm(
            concurrent.futures.as_completed(
                futures
            ),
            total=len(futures),
            desc="Partition workers",
            unit="worker",
        ):

            result = future.result()

            partition_results.append(
                result
            )

            print(
                f"\n  Worker {result.worker_id}: "
                f"{result.records:,} records "
                f"in {result.elapsed:.1f}s"
            )

    total_partition_records = sum(
        x.records
        for x in partition_results
    )

    print()
    print(
        f"Partition records : "
        f"{total_partition_records:,}"
    )

    print(
        f"Partition time    : "
        f"{time.time() - partition_start:.1f}s"
    )

    # ------------------------------------------------------------------
    # Build bucket -> component paths
    # ------------------------------------------------------------------

    bucket_inputs = {
        bucket: []
        for bucket in range(BUCKETS)
    }

    for worker_id in range(workers):

        worker_dir = (
            PARTITION_ROOT
            / f"worker_{worker_id:02d}"
        )

        for bucket in range(BUCKETS):

            path = (
                worker_dir
                / f"bucket_{bucket:02d}.jsonl"
            )

            if path.exists():

                bucket_inputs[
                    bucket
                ].append(
                    str(path)
                )

    # ------------------------------------------------------------------
    # STAGE 2
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print(
        "STAGE 2 — 9-WORKER EXACT DEDUPLICATION"
    )
    print("=" * 78)

    print(
        "Every identical SHA-256 is routed to "
        "the same bucket."
    )

    print(
        "Therefore this is GLOBAL exact deduplication."
    )

    dedup_start = time.time()

    bucket_results = []

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        future_map = {}

        for bucket in range(BUCKETS):

            future = executor.submit(
                dedup_bucket_worker,
                bucket,
                bucket_inputs[bucket],
            )

            future_map[future] = bucket

        for future in tqdm(
            concurrent.futures.as_completed(
                future_map
            ),
            total=BUCKETS,
            desc="Dedup workers",
            unit="bucket",
        ):

            result = future.result()

            bucket_results.append(
                result
            )

            print(
                f"\n  Bucket {result.bucket}: "
                f"{result.input_records:,} → "
                f"{result.unique_records:,} "
                f"("
                f"{result.duplicate_records:,} dup)"
            )

    total_bucket_input = sum(
        x.input_records
        for x in bucket_results
    )

    total_unique = sum(
        x.unique_records
        for x in bucket_results
    )

    total_duplicates = sum(
        x.duplicate_records
        for x in bucket_results
    )

    print()
    print(
        f"Dedup input       : "
        f"{total_bucket_input:,}"
    )

    print(
        f"Unique documents  : "
        f"{total_unique:,}"
    )

    print(
        f"Duplicates        : "
        f"{total_duplicates:,}"
    )

    print(
        f"Dedup time        : "
        f"{time.time() - dedup_start:.1f}s"
    )

    # ------------------------------------------------------------------
    # SANITY CHECK
    # ------------------------------------------------------------------

    if total_bucket_input != total_partition_records:

        raise RuntimeError(
            "Partition → dedup record count mismatch"
        )

    if (
        total_unique
        + total_duplicates
        != total_partition_records
    ):

        raise RuntimeError(
            "Unique + duplicate != input"
        )

    # ------------------------------------------------------------------
    # STAGE 3
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print(
        "STAGE 3 — DETERMINISTIC 9-WAY FINAL MERGE"
    )
    print("=" * 78)

    final_stats = final_merge(
        bucket_results
    )

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    validate(
        expected_input=total_partition_records,
        expected_unique=total_unique,
        expected_duplicates=total_duplicates,
        expected_provenance=total_partition_records,
    )

    # ------------------------------------------------------------------
    # MANIFEST
    # ------------------------------------------------------------------

    manifest = {

        "dataset": "MediScanAI 2.0",

        "builder":
            "parallel_merge_final_rag_v2",

        "workers":
            workers,

        "hash_buckets":
            BUCKETS,

        "input": {
            "worker_shards":
                len(shards),

            "records":
                total_partition_records,
        },

        "dedup": {
            "unique_documents":
                total_unique,

            "duplicates":
                total_duplicates,
        },

        "final": {
            "jsonl":
                str(FINAL_JSONL),

            "sqlite":
                str(SQLITE_PATH),

            "gzip":
                (
                    str(FINAL_JSONL_GZ)
                    if args.gzip_final
                    else None
                ),
        },

        "timing": {
            "partition_seconds":
                time.time() - partition_start,

            "final_merge_seconds":
                final_stats[
                    "elapsed_seconds"
                ],
        },

        "created_at_unix":
            time.time(),
    }

    with open(
        MANIFEST_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
        )

    # ------------------------------------------------------------------
    # OPTIONAL GZIP
    # ------------------------------------------------------------------

    if args.gzip_final:
        gzip_final()

    # ------------------------------------------------------------------
    # COMPLETE
    # ------------------------------------------------------------------

    with open(
        COMPLETE_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "complete": True,
                "records":
                    total_partition_records,
                "unique":
                    total_unique,
                "duplicates":
                    total_duplicates,
                "workers":
                    workers,
                "timestamp":
                    time.time(),
            },
            f,
            indent=2,
        )

    print()
    print("=" * 78)
    print(
        "PARALLEL FINAL RAG BUILD COMPLETE"
    )
    print("=" * 78)

    print(
        f"Input chunks  : "
        f"{total_partition_records:,}"
    )

    print(
        f"Unique docs   : "
        f"{total_unique:,}"
    )

    print(
        f"Duplicates    : "
        f"{total_duplicates:,}"
    )

    print()
    print(
        f"Final JSONL:"
    )

    print(
        f"  {FINAL_JSONL}"
    )

    print()
    print(
        f"SQLite:"
    )

    print(
        f"  {SQLITE_PATH}"
    )


if __name__ == "__main__":
    main()