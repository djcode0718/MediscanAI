#!/usr/bin/env python3

"""
MediScanAI 2.0
Final RAG Dataset Builder V2

INPUT
-----
Existing worker shards produced by build_final_rag_v2.py.

The worker shard format is:

{
    "source": "...",
    "source_file": "...",
    "source_line": ...,
    "original_document_id": "...",
    "chunk_index": ...,
    "chunk_count": ...,
    "record": {
        ...
        "text": "...",
        "content_hash": "...",
        "rag_chunk": {...}
    }
}

GOAL
----
Produce the final exact-deduplicated RAG dataset.

IMPORTANT
---------
- Does NOT reprocess raw source data.
- Does NOT re-chunk.
- Does NOT truncate text.
- Does NOT semantically deduplicate.
- Preserves the complete worker-shard record.
- Uses all 9 CPU workers.
- Dynamically balances Stage 1 by FILE.
- Uses 9 parallel hash buckets for exact global dedup.
- Final shards are written directly by dedup workers.
- No expensive final single-threaded merge.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator


# ============================================================
# CONFIG
# ============================================================

DEFAULT_WORKERS = 9

NUM_BUCKETS = 9

# Final output shard size.
FINAL_RECORDS_PER_SHARD = 75_000

# Compression level 3:
# much faster than maximum gzip compression while still
# significantly reducing storage.
GZIP_LEVEL = 3

ENCODING = "utf-8"


# ============================================================
# FILE HELPERS
# ============================================================

def open_text(path: Path, mode: str = "rt"):
    """
    Open plain JSONL or gzip JSONL.
    """

    if path.name.endswith(".gz"):
        return gzip.open(
            path,
            mode,
            encoding=ENCODING,
        )

    return open(
        path,
        mode,
        encoding=ENCODING,
    )


def iter_jsonl(path: Path) -> Iterator[dict]:
    """
    Stream JSONL records.
    """

    with open_text(path, "rt") as f:

        for line_no, line in enumerate(f, 1):

            line = line.strip()

            if not line:
                continue

            try:
                yield json.loads(line)

            except json.JSONDecodeError as exc:

                raise RuntimeError(
                    f"Invalid JSON: "
                    f"{path}:{line_no}: {exc}"
                )


# ============================================================
# RECORD HELPERS
# ============================================================

def inner_record(wrapper: dict) -> dict:
    """
    Get the actual RAG record.
    """

    record = wrapper.get("record")

    if not isinstance(record, dict):
        raise ValueError(
            "Worker shard record does not contain "
            "a valid nested 'record' object."
        )

    return record


def get_text(wrapper: dict) -> str:
    """
    Extract actual RAG text.
    """

    record = inner_record(wrapper)

    text = record.get("text")

    if text is None:
        return ""

    return str(text)


def get_hash(wrapper: dict) -> str:
    """
    Use the already-computed SHA-256 hash.

    The worker stage already generated content_hash,
    so there is NO reason to hash 5.58M large texts again.
    """

    record = inner_record(wrapper)

    h = record.get("content_hash")

    if not h:
        raise ValueError(
            "Missing content_hash in worker record."
        )

    return str(h)


def verify_hash(wrapper: dict) -> bool:
    """
    Optional correctness check.

    Not used on every record during the main pipeline because
    the worker stage already generated and validated hashes.

    Used only during final sampling/validation.
    """

    text = get_text(wrapper)

    expected = hashlib.sha256(
        text.encode(ENCODING)
    ).hexdigest()

    return expected == get_hash(wrapper)


def bucket_for_hash(h: str) -> int:
    """
    Deterministically assign a SHA-256 hash to one of 9 buckets.
    """

    return int(h[:8], 16) % NUM_BUCKETS


# ============================================================
# DISCOVER INPUTS
# ============================================================

def discover_input_files(input_dir: Path) -> list[Path]:

    files = []

    for p in input_dir.iterdir():

        if not p.is_file():
            continue

        if p.name.endswith(".jsonl"):
            files.append(p)

        elif p.name.endswith(".jsonl.gz"):
            files.append(p)

    return sorted(files)


# ============================================================
# STAGE 1
# PARALLEL HASH PARTITION
# ============================================================

def partition_one_file(
    file_index: int,
    input_path: str,
    bucket_dir: str,
) -> dict:

    """
    Process exactly one worker shard.

    Multiple of these tasks run concurrently through a
    9-process pool.

    Dynamic task scheduling means a huge FDA file or the
    huge Clinical Trials file will not leave one worker
    stuck while others sit idle.
    """

    input_path = Path(input_path)
    bucket_dir = Path(bucket_dir)

    # Each INPUT FILE gets its own directory.
    #
    # Example:
    #
    # 0000_fda.../
    #     bucket_00.jsonl
    #     bucket_01.jsonl
    #     ...
    #
    # This means processes never contend over the same file.

    local_dir = (
        bucket_dir /
        f"{file_index:04d}"
    )

    local_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    handles = {}

    records = 0
    empty = 0
    buckets = [0] * NUM_BUCKETS

    started = time.time()

    try:

        def get_handle(bucket: int):

            if bucket not in handles:

                path = (
                    local_dir /
                    f"bucket_{bucket:02d}.jsonl"
                )

                handles[bucket] = open(
                    path,
                    "w",
                    encoding=ENCODING,
                    buffering=1024 * 1024,
                )

            return handles[bucket]

        for wrapper in iter_jsonl(input_path):

            records += 1

            text = get_text(wrapper)

            if not text:
                empty += 1
                continue

            h = get_hash(wrapper)

            bucket = bucket_for_hash(h)

            handle = get_handle(bucket)

            handle.write(
                json.dumps(
                    wrapper,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )

            handle.write("\n")

            buckets[bucket] += 1

    finally:

        for handle in handles.values():
            handle.close()

    return {
        "file_index": file_index,
        "file": str(input_path),
        "records": records,
        "empty": empty,
        "bucket_counts": buckets,
        "runtime_sec": time.time() - started,
    }


# ============================================================
# STAGE 2
# EXACT GLOBAL DEDUP
# ============================================================

def dedup_bucket(
    bucket_id: int,
    bucket_dir: str,
    output_dir: str,
) -> dict:

    """
    Perform exact global SHA-256 deduplication for one bucket.

    Because ALL identical hashes are guaranteed to belong to
    the same bucket, each bucket can be deduplicated completely
    independently.

    Therefore 9 buckets = 9 simultaneous CPU workers.
    """

    bucket_dir = Path(bucket_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    started = time.time()

    fragments = sorted(
        bucket_dir.glob(
            f"*/bucket_{bucket_id:02d}.jsonl"
        )
    )

    seen = set()

    input_records = 0
    unique_records = 0
    duplicate_records = 0

    shard_index = 0
    shard_records = 0

    output_handle = None
    output_paths = []

    def open_output():

        nonlocal output_handle

        path = (
            output_dir /
            f"dataset-b{bucket_id:02d}-"
            f"{shard_index:06d}.jsonl.gz"
        )

        output_handle = gzip.open(
            path,
            "wt",
            encoding=ENCODING,
            compresslevel=GZIP_LEVEL,
        )

        output_paths.append(str(path))

    def close_output():

        nonlocal output_handle

        if output_handle is not None:
            output_handle.close()
            output_handle = None

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

                    input_records += 1

                    wrapper = json.loads(line)

                    h = get_hash(wrapper)

                    # EXACT GLOBAL DEDUP
                    if h in seen:

                        duplicate_records += 1
                        continue

                    seen.add(h)

                    unique_records += 1

                    if output_handle is None:
                        open_output()

                    output_handle.write(line)
                    output_handle.write("\n")

                    shard_records += 1

                    if (
                        shard_records
                        >= FINAL_RECORDS_PER_SHARD
                    ):

                        close_output()

                        shard_index += 1
                        shard_records = 0

    finally:

        close_output()

    # --------------------------------------------------------
    # Delete THIS bucket's temporary fragments.
    #
    # Other bucket workers can continue independently.
    # --------------------------------------------------------

    deleted_bytes = 0

    for fragment in fragments:

        try:
            deleted_bytes += fragment.stat().st_size
            fragment.unlink()
        except FileNotFoundError:
            pass

    # Remove now-empty input directory.
    for directory in bucket_dir.iterdir():

        if directory.is_dir():

            try:
                directory.rmdir()
            except OSError:
                pass

    return {
        "bucket": bucket_id,
        "input_records": input_records,
        "unique_records": unique_records,
        "duplicate_records": duplicate_records,
        "output_shards": len(output_paths),
        "output_paths": output_paths,
        "deleted_temp_bytes": deleted_bytes,
        "runtime_sec": time.time() - started,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(
    output_dir: Path,
    expected_unique: int | None,
) -> dict:

    print()
    print("=" * 72)
    print("FINAL DATASET VALIDATION")
    print("=" * 72)

    files = sorted(
        output_dir.glob(
            "dataset-*.jsonl.gz"
        )
    )

    if not files:
        raise RuntimeError(
            "No final dataset shards found."
        )

    total = 0
    empty = 0
    missing_hash = 0
    bad_hash = 0

    # NOTE:
    #
    # We do NOT keep every hash in memory here.
    # Exact global uniqueness was already guaranteed by the
    # bucket architecture.
    #
    # Instead, we validate counts + sample hashes and rely on
    # bucket isolation for the global uniqueness invariant.

    source_counts = {}

    sampled = 0
    sample_hash_failures = 0

    for path in files:

        print(
            f"  {path.name}",
            flush=True,
        )

        for wrapper in iter_jsonl(path):

            total += 1

            record = inner_record(wrapper)

            text = record.get("text", "")
            h = record.get("content_hash")

            if not text:
                empty += 1

            if not h:
                missing_hash += 1

            # Validate first 1000 records globally.
            if sampled < 1000:

                if not verify_hash(wrapper):
                    sample_hash_failures += 1

                sampled += 1

            source = wrapper.get(
                "source",
                record.get(
                    "source",
                    "UNKNOWN",
                ),
            )

            source_counts[source] = (
                source_counts.get(source, 0) + 1
            )

    result = {
        "files": len(files),
        "records": total,
        "expected_unique_records": expected_unique,
        "empty_text": empty,
        "missing_hash": missing_hash,
        "sampled_hashes": sampled,
        "sample_hash_failures": sample_hash_failures,
        "source_distribution": source_counts,
    }

    with open(
        output_dir / "validation.json",
        "w",
        encoding=ENCODING,
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        f"Final records:       {total:,}"
    )

    if expected_unique is not None:

        print(
            f"Expected records:    "
            f"{expected_unique:,}"
        )

        print(
            f"Difference:          "
            f"{total - expected_unique:,}"
        )

    print(
        f"Empty text:          {empty:,}"
    )

    print(
        f"Missing hashes:      {missing_hash:,}"
    )

    print(
        f"Sampled hashes:      {sampled:,}"
    )

    print(
        f"Bad sampled hashes:   "
        f"{sample_hash_failures:,}"
    )

    print()
    print("Source distribution:")

    for source, count in sorted(
        source_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    ):

        print(
            f"  {source:<25} "
            f"{count:,}"
        )

    # --------------------------------------------------------
    # HARD VALIDATION
    # --------------------------------------------------------

    if expected_unique is not None:

        if total != expected_unique:

            raise RuntimeError(
                "FINAL RECORD COUNT DOES NOT MATCH "
                "EXPECTED UNIQUE COUNT."
            )

    if empty:
        raise RuntimeError(
            "FINAL DATASET CONTAINS EMPTY TEXT."
        )

    if missing_hash:
        raise RuntimeError(
            "FINAL DATASET CONTAINS MISSING HASHES."
        )

    if sample_hash_failures:
        raise RuntimeError(
            "FINAL DATASET HASH VALIDATION FAILED."
        )

    print()
    print(
        "ALL FINAL DATASET VALIDATION CHECKS PASSED"
    )

    return result


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
        "--input",
        type=Path,
        default=Path(
            "results/final_v2/worker_shards"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/final_v2/dataset"
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    workers = min(
        args.workers,
        os.cpu_count() or args.workers,
    )

    input_dir = args.input
    output_dir = args.output

    temp_dir = (
        output_dir.parent /
        "tmp_hash_buckets"
    )

    checkpoint_dir = (
        output_dir.parent /
        "checkpoints"
    )

    checkpoint_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 72)
    print("MEDISCANAI 2.0 — FINAL DATASET BUILDER")
    print("=" * 72)

    print(
        f"CPU workers:          {workers}"
    )

    print(
        f"Input:                {input_dir}"
    )

    print(
        f"Output:               {output_dir}"
    )

    print(
        f"Hash buckets:         {NUM_BUCKETS}"
    )

    print(
        f"Final shard size:     "
        f"{FINAL_RECORDS_PER_SHARD:,}"
    )

    # --------------------------------------------------------
    # CHECK INPUT
    # --------------------------------------------------------

    if not input_dir.exists():

        raise RuntimeError(
            f"Input directory does not exist:\n"
            f"{input_dir}"
        )

    input_files = discover_input_files(
        input_dir
    )

    if not input_files:

        raise RuntimeError(
            "No worker shard files found."
        )

    print()
    print(
        f"Worker shard files:   "
        f"{len(input_files):,}"
    )

    # --------------------------------------------------------
    # EXPECTED COUNT
    # --------------------------------------------------------

    # We already know this from the previous successful
    # worker build.
    #
    # 5,578,588 chunk candidates.

    EXPECTED_INPUT = 5_578_588

    print(
        f"Expected input:       "
        f"{EXPECTED_INPUT:,}"
    )

    # Previous validated baseline:
    #
    # 5,115,547 input records
    # - 2,050,610 exact duplicates
    # = 3,064,937 unique
    #
    # V2 chunking produces 5,578,588 candidates, so the final
    # unique count MUST be measured by this run.
    #
    # Therefore expected_unique is intentionally NOT hardcoded.

    # --------------------------------------------------------
    # FORCE CLEAN
    # --------------------------------------------------------

    if args.force:

        print()
        print(
            "Removing ONLY V2 temporary/output data..."
        )

        for path in [
            temp_dir,
            output_dir,
        ]:

            if path.exists():

                print(
                    f"  removing {path}"
                )

                shutil.rmtree(path)

    # --------------------------------------------------------
    # STAGE 1
    # --------------------------------------------------------

    stage1_checkpoint = (
        checkpoint_dir /
        "finalize_stage1.json"
    )

    if stage1_checkpoint.exists():

        print()
        print(
            "Stage 1 checkpoint exists."
        )

        print(
            "Skipping Stage 1."
        )

    else:

        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        print()
        print("=" * 72)
        print(
            "STAGE 1 — PARALLEL HASH PARTITION"
        )
        print("=" * 72)

        print(
            f"Launching {workers} workers..."
        )

        started = time.time()

        futures = []

        with ProcessPoolExecutor(
            max_workers=workers
        ) as executor:

            # ------------------------------------------------
            # IMPORTANT:
            #
            # One FUTURE per file.
            #
            # ProcessPoolExecutor dynamically schedules these
            # 237 tasks across the 9 processes.
            #
            # This fixes the severe imbalance seen previously.
            # ------------------------------------------------

            for file_index, path in enumerate(
                input_files
            ):

                future = executor.submit(
                    partition_one_file,
                    file_index,
                    str(path),
                    str(temp_dir),
                )

                futures.append(future)

            completed = 0
            results = []

            for future in as_completed(
                futures
            ):

                result = future.result()

                results.append(result)

                completed += 1

                print(
                    f"[Stage 1] "
                    f"{completed:3d}/{len(futures)} "
                    f"files | "
                    f"{result['records']:,} records | "
                    f"{result['runtime_sec']:.1f}s",
                    flush=True,
                )

        results.sort(
            key=lambda x: x["file_index"]
        )

        total_records = sum(
            x["records"]
            for x in results
        )

        if total_records != EXPECTED_INPUT:

            raise RuntimeError(
                f"Input record count mismatch.\n"
                f"Expected: {EXPECTED_INPUT:,}\n"
                f"Actual:   {total_records:,}"
            )

        stage1 = {
            "workers": workers,
            "files": len(input_files),
            "records": total_records,
            "runtime_sec": time.time() - started,
        }

        with open(
            stage1_checkpoint,
            "w",
            encoding=ENCODING,
        ) as f:

            json.dump(
                stage1,
                f,
                indent=2,
            )

        print()
        print(
            f"STAGE 1 COMPLETE — "
            f"{total_records:,} records"
        )

        print(
            f"Runtime: "
            f"{stage1['runtime_sec']:.1f}s"
        )

    # --------------------------------------------------------
    # STAGE 2
    # --------------------------------------------------------

    stage2_checkpoint = (
        checkpoint_dir /
        "finalize_stage2.json"
    )

    if stage2_checkpoint.exists():

        print()
        print(
            "Stage 2 checkpoint exists."
        )

        print(
            "Skipping Stage 2."
        )

    else:

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        print()
        print("=" * 72)
        print(
            "STAGE 2 — 9-WORKER GLOBAL EXACT DEDUP"
        )
        print("=" * 72)

        print(
            "Launching all 9 bucket workers..."
        )

        started = time.time()

        futures = []

        with ProcessPoolExecutor(
            max_workers=NUM_BUCKETS
        ) as executor:

            for bucket_id in range(
                NUM_BUCKETS
            ):

                future = executor.submit(
                    dedup_bucket,
                    bucket_id,
                    str(temp_dir),
                    str(output_dir),
                )

                futures.append(future)

            results = []
            completed = 0

            for future in as_completed(
                futures
            ):

                result = future.result()

                results.append(result)

                completed += 1

                print(
                    f"\n[Stage 2] "
                    f"bucket "
                    f"{result['bucket']:02d} "
                    f"finished "
                    f"({completed}/9)"
                )

                print(
                    f"  input:      "
                    f"{result['input_records']:,}"
                )

                print(
                    f"  unique:     "
                    f"{result['unique_records']:,}"
                )

                print(
                    f"  duplicates: "
                    f"{result['duplicate_records']:,}"
                )

                print(
                    f"  shards:     "
                    f"{result['output_shards']:,}"
                )

                print(
                    f"  runtime:    "
                    f"{result['runtime_sec']:.1f}s"
                )

        results.sort(
            key=lambda x: x["bucket"]
        )

        total_input = sum(
            x["input_records"]
            for x in results
        )

        total_unique = sum(
            x["unique_records"]
            for x in results
        )

        total_duplicates = sum(
            x["duplicate_records"]
            for x in results
        )

        if total_input != EXPECTED_INPUT:

            raise RuntimeError(
                f"Stage 2 input mismatch.\n"
                f"Expected: {EXPECTED_INPUT:,}\n"
                f"Actual:   {total_input:,}"
            )

        if (
            total_unique +
            total_duplicates
            != total_input
        ):

            raise RuntimeError(
                "Stage 2 accounting mismatch."
            )

        stage2 = {
            "workers": NUM_BUCKETS,
            "input_records": total_input,
            "unique_records": total_unique,
            "duplicate_records": total_duplicates,
            "runtime_sec": time.time() - started,
            "buckets": results,
        }

        with open(
            stage2_checkpoint,
            "w",
            encoding=ENCODING,
        ) as f:

            json.dump(
                stage2,
                f,
                indent=2,
            )

        print()
        print("=" * 72)
        print("STAGE 2 COMPLETE")
        print("=" * 72)

        print(
            f"Input:       {total_input:,}"
        )

        print(
            f"Unique:      {total_unique:,}"
        )

        print(
            f"Duplicates:  {total_duplicates:,}"
        )

        print(
            f"Runtime:     "
            f"{stage2['runtime_sec']:.1f}s"
        )

    # --------------------------------------------------------
    # STAGE 3
    # VALIDATION
    # --------------------------------------------------------

    validation_path = (
        output_dir /
        "validation.json"
    )

    if validation_path.exists():

        print()
        print(
            "Validation already exists."
        )

        with open(
            validation_path,
            "r",
            encoding=ENCODING,
        ) as f:

            validation = json.load(f)

    else:

        # Read Stage 2 result to know expected unique count.

        with open(
            stage2_checkpoint,
            "r",
            encoding=ENCODING,
        ) as f:

            stage2 = json.load(f)

        validation = validate_dataset(
            output_dir,
            stage2["unique_records"],
        )

    # --------------------------------------------------------
    # FINAL MANIFEST
    # --------------------------------------------------------

    final_shards = sorted(
        output_dir.glob(
            "dataset-*.jsonl.gz"
        )
    )

    manifest = {
        "dataset": "MediScanAI 2.0",
        "dataset_version": "final_rag_v2",

        "input": {
            "worker_shards": len(input_files),
            "records": EXPECTED_INPUT,
        },

        "output": {
            "records": validation["records"],
            "shards": len(final_shards),
            "records_per_shard_target": (
                FINAL_RECORDS_PER_SHARD
            ),
        },

        "deduplication": {
            "method": "exact SHA-256 content hash",
            "semantic_deduplication": False,
        },

        "chunking": {
            "performed": True,
            "performed_upstream": True,
            "additional_chunking_here": False,
            "truncation": False,
        },

        "compression": {
            "format": "gzip",
            "level": GZIP_LEVEL,
        },

        "source_distribution": (
            validation["source_distribution"]
        ),

        "shards": [
            {
                "path": str(p),
                "size_bytes": p.stat().st_size,
            }
            for p in final_shards
        ],
    }

    with open(
        output_dir / "manifest.json",
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
    # TEMP CLEANUP
    # --------------------------------------------------------

    if temp_dir.exists():

        print()
        print(
            "Removing temporary hash partitions..."
        )

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print(
        "MEDISCANAI 2.0 FINAL DATASET READY"
    )
    print("=" * 72)

    print(
        f"Input records:       "
        f"{EXPECTED_INPUT:,}"
    )

    print(
        f"Final unique records:"
        f" {validation['records']:,}"
    )

    print(
        f"Exact duplicates:    "
        f"{EXPECTED_INPUT - validation['records']:,}"
    )

    print(
        f"Final shards:        "
        f"{len(final_shards):,}"
    )

    print()
    print(
        f"Location:\n"
        f"{output_dir}"
    )

    print()
    print(
        "NEXT STAGE:"
    )

    print(
        "Move this dataset to Google Colab → "
        "T4 GPU → embedding benchmark."
    )


if __name__ == "__main__":
    main()