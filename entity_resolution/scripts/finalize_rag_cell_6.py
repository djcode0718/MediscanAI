#!/usr/bin/env python3

"""
MediScanAI 2.0 — FINAL RAG BUILDER

FAST + SAFE MAC VERSION

Input:
    entity_resolution/data/final_inputs/
        fda/*.jsonl
        dailymed/*.jsonl
        clinical_trials/*.jsonl

Processing:
    FDA → DailyMed → Clinical Trials

Parallelism:
    9 worker processes
    1 active input file at a time

Optimization:
    - Plain JSONL input (no gzip bottleneck)
    - Independent byte-range workers
    - 10,000-record processing batches
    - Workers write temporary shards
    - Parent performs final deterministic merge
    - In-memory SHA-256 deduplication
    - SQLite only for provenance/statistics
    - No per-document SQLite SELECT
    - File-level checkpoints
    - Low RAM design
    - Raw inputs are never modified
"""

from __future__ import annotations

import gzip
import hashlib
import json
import multiprocessing as mp
import os
import shutil
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from tqdm import tqdm


# =================================================================
# PATHS
# =================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_ROOT = (
    PROJECT_ROOT
    / "entity_resolution"
    / "data"
    / "final_inputs"
)

FDA_DIR = INPUT_ROOT / "fda"
DAILYMED_DIR = INPUT_ROOT / "dailymed"
CT_DIR = INPUT_ROOT / "clinical_trials"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "entity_resolution"
    / "results"
    / "final"
)

CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
SHARD_DIR = OUTPUT_DIR / "shards"

FINAL_RAG = (
    OUTPUT_DIR
    / "mediscanai_rag.jsonl.gz"
)

MANIFEST = (
    OUTPUT_DIR
    / "rag_manifest.json"
)

SQLITE_DB = (
    OUTPUT_DIR
    / "document_dedup.sqlite"
)


# =================================================================
# PERFORMANCE
# =================================================================

# Mac has 10 cores.
# Deliberately leave one core free.
WORKERS = 9

# Target processing batch.
RECORD_BATCH_SIZE = 10_000

# Approximate byte range assigned to one worker task.
#
# 64 MB gives good parallelism without creating excessive tasks.
BYTE_RANGE_SIZE = 64 * 1024 * 1024

# Output gzip compression.
# Level 1 is considerably faster than level 6 and is sufficient
# because the final artifact is for retrieval/embedding.
FINAL_GZIP_LEVEL = 1


# =================================================================
# TEXT
# =================================================================

MIN_TEXT_CHARS = 40
MAX_TEXT_CHARS = 8000


# =================================================================
# SOURCE ORDER
# =================================================================

SOURCE_ORDER = {
    "fda": 0,
    "dailymed": 1,
    "clinical_trials": 2,
}


# =================================================================
# BASIC FUNCTIONS
# =================================================================

def canonical_text(text: Any) -> str:
    """
    Upstream normalization has already handled:
        - Unicode normalization
        - control characters
        - HTML entities
        - normalization work

    Therefore we intentionally avoid expensive repeated
    whitespace normalization here.

    Only strip leading/trailing whitespace.
    """

    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    return text.strip()


def sha256_text(text: str) -> str:

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def get_text(
    record: dict[str, Any]
) -> str:

    for key in (
        "text",
        "content",
        "document_text",
        "body",
    ):

        value = record.get(key)

        if isinstance(value, str):
            return value

    return ""


def get_document_id(
    record: dict[str, Any],
    fallback: str,
) -> str:

    for key in (
        "document_id",
        "id",
        "doc_id",
        "trial_id",
        "set_id",
        "spl_id",
    ):

        value = record.get(key)

        if value is not None:

            value = str(value).strip()

            if value:
                return value

    return fallback


# =================================================================
# CHECKPOINTS
# =================================================================

def checkpoint_path(
    source: str,
    filename: str,
) -> Path:

    safe_name = filename.replace(
        "/",
        "_",
    )

    return (
        CHECKPOINT_DIR
        / f"{source}__{safe_name}.done"
    )


def is_completed(
    source: str,
    filename: str,
) -> bool:

    return checkpoint_path(
        source,
        filename,
    ).exists()


def mark_completed(
    source: str,
    filename: str,
):

    target = checkpoint_path(
        source,
        filename,
    )

    tmp = target.with_suffix(
        ".tmp"
    )

    with open(
        tmp,
        "w",
        encoding="utf-8",
    ) as f:

        f.write("completed\n")

    os.replace(
        tmp,
        target,
    )


# =================================================================
# BYTE-RANGE DISCOVERY
# =================================================================

def make_ranges(
    path: Path,
) -> list[tuple[int, int]]:

    file_size = path.stat().st_size

    ranges = []

    start = 0

    while start < file_size:

        end = min(
            start + BYTE_RANGE_SIZE,
            file_size,
        )

        ranges.append(
            (
                start,
                end,
            )
        )

        start = end

    return ranges


# =================================================================
# WORKER
# =================================================================

def process_byte_range(
    args: tuple[
        str,
        str,
        str,
        int,
        int,
        str,
    ]
) -> dict[str, Any]:

    (
        source,
        filename,
        input_path,
        start_byte,
        end_byte,
        shard_path,
    ) = args

    input_path = Path(
        input_path
    )

    shard_path = Path(
        shard_path
    )

    stats = {
        "input_records": 0,
        "valid_records": 0,
        "empty_text": 0,
        "short_text": 0,
        "truncated": 0,
        "json_errors": 0,
    }

    # -------------------------------------------------------------
    # Each worker opens the plain JSONL independently.
    # -------------------------------------------------------------

    with open(
        input_path,
        "rb",
    ) as f:

        f.seek(start_byte)

        # ---------------------------------------------------------
        # If not at the beginning, discard the partial first line.
        # ---------------------------------------------------------

        if start_byte > 0:
            f.readline()

        actual_start = f.tell()

        # ---------------------------------------------------------
        # Worker writes directly to its own shard.
        # ---------------------------------------------------------

        with open(
            shard_path,
            "w",
            encoding="utf-8",
        ) as out:

            while True:

                current_position = f.tell()

                if (
                    current_position >= end_byte
                    and current_position != actual_start
                ):
                    break

                line = f.readline()

                if not line:
                    break

                line = line.strip()

                if not line:
                    continue

                stats[
                    "input_records"
                ] += 1

                try:

                    record = json.loads(
                        line
                    )

                except Exception:

                    stats[
                        "json_errors"
                    ] += 1

                    continue

                if not isinstance(
                    record,
                    dict,
                ):

                    stats[
                        "json_errors"
                    ] += 1

                    continue

                text = canonical_text(
                    get_text(record)
                )

                if not text:

                    stats[
                        "empty_text"
                    ] += 1

                    continue

                if len(text) < MIN_TEXT_CHARS:

                    stats[
                        "short_text"
                    ] += 1

                    continue

                if len(text) > MAX_TEXT_CHARS:

                    text = text[
                        :MAX_TEXT_CHARS
                    ]

                    stats[
                        "truncated"
                    ] += 1

                # -------------------------------------------------
                # Byte ranges don't know global line numbers.
                # Filename + worker range gives a safe fallback.
                # Existing IDs are preferred.
                # -------------------------------------------------

                document_id = get_document_id(
                    record,
                    fallback=(
                        f"{source}:"
                        f"{filename}:"
                        f"{start_byte}:"
                        f"{stats['input_records']}"
                    ),
                )

                content_hash = sha256_text(
                    text
                )

                record["text"] = text

                record[
                    "document_id"
                ] = document_id

                record[
                    "content_hash"
                ] = content_hash

                record[
                    "source"
                ] = source

                out.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        separators=(
                            ",",
                            ":",
                        ),
                    )
                )

                out.write("\n")

                stats[
                    "valid_records"
                ] += 1

    return {
        "source": source,
        "filename": filename,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "shard_path": str(shard_path),
        **stats,
    }


# =================================================================
# DATABASE
# =================================================================

def initialize_database():

    conn = sqlite3.connect(
        SQLITE_DB
    )

    conn.execute(
        "PRAGMA journal_mode=WAL"
    )

    conn.execute(
        "PRAGMA synchronous=NORMAL"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            content_hash TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            document_id TEXT,
            output_index INTEGER NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS provenance (
            content_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            filename TEXT NOT NULL,
            document_id TEXT,
            PRIMARY KEY (
                content_hash,
                source,
                filename,
                document_id
            )
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_stats (
            source TEXT NOT NULL,
            filename TEXT NOT NULL,
            input_records INTEGER,
            valid_records INTEGER,
            unique_documents INTEGER,
            duplicate_documents INTEGER,
            empty_text INTEGER,
            short_text INTEGER,
            truncated INTEGER,
            json_errors INTEGER,
            PRIMARY KEY (
                source,
                filename
            )
        )
        """
    )

    conn.commit()

    return conn


# =================================================================
# FILE DISCOVERY
# =================================================================

def discover_files(
    directory: Path,
) -> list[Path]:

    if not directory.exists():

        raise FileNotFoundError(
            f"Missing directory:\n{directory}"
        )

    # Plain JSONL only.
    files = sorted(
        p
        for p in directory.glob(
            "*.jsonl"
        )
        if p.is_file()
    )

    return files


# =================================================================
# PROCESS ONE FILE
# =================================================================

def process_file(
    source: str,
    path: Path,
    executor: ProcessPoolExecutor,
    output,
    conn: sqlite3.Connection,
    global_hashes: set[str],
    output_index: int,
) -> tuple[
    dict[str, Any],
    int,
]:

    print(
        f"\n[{source}] {path.name}"
    )

    start_time = time.time()

    ranges = make_ranges(
        path
    )

    print(
        f"  Size: "
        f"{path.stat().st_size / (1024**2):.1f} MB"
    )

    print(
        f"  Worker ranges: "
        f"{len(ranges)}"
    )

    # -------------------------------------------------------------
    # Temporary directory for this file.
    # -------------------------------------------------------------

    file_shard_dir = (
        SHARD_DIR
        / source
        / path.stem
    )

    if file_shard_dir.exists():
        shutil.rmtree(
            file_shard_dir
        )

    file_shard_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------
    # Create worker tasks.
    # -------------------------------------------------------------

    tasks = []

    for index, (
        start_byte,
        end_byte,
    ) in enumerate(ranges):

        shard_path = (
            file_shard_dir
            / f"shard_{index:05d}.jsonl"
        )

        tasks.append(
            (
                source,
                path.name,
                str(path),
                start_byte,
                end_byte,
                str(shard_path),
            )
        )

    # -------------------------------------------------------------
    # Process byte ranges in parallel.
    # -------------------------------------------------------------

    file_stats = {
        "input_records": 0,
        "valid_records": 0,
        "unique_documents": 0,
        "duplicate_documents": 0,
        "empty_text": 0,
        "short_text": 0,
        "truncated": 0,
        "json_errors": 0,
    }

    worker_results = []

    progress = tqdm(
        total=len(tasks),
        desc=f"{source} workers",
        unit="range",
    )

    for result in executor.map(
        process_byte_range,
        tasks,
        chunksize=1,
    ):

        worker_results.append(
            result
        )

        progress.update(1)

    progress.close()

    # -------------------------------------------------------------
    # Deterministic shard order.
    # -------------------------------------------------------------

    worker_results.sort(
        key=lambda x: x[
            "start_byte"
        ]
    )

    # -------------------------------------------------------------
    # Merge shards.
    #
    # Dedup happens here.
    # -------------------------------------------------------------

    for result in worker_results:

        for key in (
            "input_records",
            "valid_records",
            "empty_text",
            "short_text",
            "truncated",
            "json_errors",
        ):

            file_stats[key] += (
                result[key]
            )

        shard_path = Path(
            result["shard_path"]
        )

        with open(
            shard_path,
            "r",
            encoding="utf-8",
        ) as shard:

            for line in shard:

                line = line.strip()

                if not line:
                    continue

                record = json.loads(
                    line
                )

                content_hash = (
                    record[
                        "content_hash"
                    ]
                )

                document_id = (
                    record[
                        "document_id"
                    ]
                )

                # -------------------------------------------------
                # Provenance is always recorded.
                # -------------------------------------------------

                conn.execute(
                    """
                    INSERT OR IGNORE INTO provenance (
                        content_hash,
                        source,
                        filename,
                        document_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        content_hash,
                        source,
                        path.name,
                        document_id,
                    ),
                )

                # -------------------------------------------------
                # Fast in-memory exact dedup.
                # -------------------------------------------------

                if content_hash in global_hashes:

                    file_stats[
                        "duplicate_documents"
                    ] += 1

                    continue

                global_hashes.add(
                    content_hash
                )

                output_index += 1

                record["rag_index"] = (
                    output_index
                )

                output.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        separators=(
                            ",",
                            ":",
                        ),
                    )
                )

                output.write("\n")

                file_stats[
                    "unique_documents"
                ] += 1

        # ---------------------------------------------------------
        # Delete shard immediately after successful merge.
        # ---------------------------------------------------------

        shard_path.unlink(
            missing_ok=True
        )

    # -------------------------------------------------------------
    # Remove empty shard directory.
    # -------------------------------------------------------------

    try:
        file_shard_dir.rmdir()
    except OSError:
        pass

    # -------------------------------------------------------------
    # Commit provenance.
    # -------------------------------------------------------------

    conn.commit()

    elapsed = (
        time.time()
        - start_time
    )

    print(
        f"  Input records : "
        f"{file_stats['input_records']:,}"
    )

    print(
        f"  Valid records : "
        f"{file_stats['valid_records']:,}"
    )

    print(
        f"  Unique        : "
        f"{file_stats['unique_documents']:,}"
    )

    print(
        f"  Duplicates    : "
        f"{file_stats['duplicate_documents']:,}"
    )

    print(
        f"  Time          : "
        f"{elapsed:.1f} sec"
    )

    print(
        f"  Speed         : "
        f"{file_stats['input_records'] / max(elapsed, 0.001):,.0f} "
        f"records/sec"
    )

    return (
        file_stats,
        output_index,
    )


# =================================================================
# MAIN
# =================================================================

def main():

    print("=" * 72)
    print("MediScanAI — FINAL RAG BUILD")
    print("=" * 72)

    print(
        f"\nCPU workers: {WORKERS}"
    )

    print(
        "Mode: SEQUENTIAL DATASETS + SEQUENTIAL FILES"
    )

    print(
        "Parallelism: 9 workers per active file"
    )

    print(
        f"Record batch target: {RECORD_BATCH_SIZE:,}"
    )

    print(
        f"Byte range target: "
        f"{BYTE_RANGE_SIZE / (1024**2):.0f} MB"
    )

    # -------------------------------------------------------------
    # Directories
    # -------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SHARD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------
    # Discover
    # -------------------------------------------------------------

    fda_files = discover_files(
        FDA_DIR
    )

    dailymed_files = discover_files(
        DAILYMED_DIR
    )

    ct_files = discover_files(
        CT_DIR
    )

    print(
        f"\nFDA files          : "
        f"{len(fda_files)}"
    )

    print(
        f"DailyMed files     : "
        f"{len(dailymed_files)}"
    )

    print(
        f"Clinical Trials    : "
        f"{len(ct_files)}"
    )

    # -------------------------------------------------------------
    # Safety validation
    # -------------------------------------------------------------

    if len(fda_files) != 14:

        raise RuntimeError(
            f"Expected 14 FDA .jsonl files, "
            f"found {len(fda_files)}"
        )

    if len(dailymed_files) != 222:

        raise RuntimeError(
            f"Expected 222 DailyMed .jsonl files, "
            f"found {len(dailymed_files)}"
        )

    if len(ct_files) != 1:

        raise RuntimeError(
            f"Expected 1 Clinical Trials .jsonl file, "
            f"found {len(ct_files)}"
        )

    print(
        "\nInput validation: PASSED"
    )

    # -------------------------------------------------------------
    # Initialize SQLite.
    #
    # If the final directory was deleted before this run, this
    # creates a fresh DB.
    # -------------------------------------------------------------

    print(
        "\nPreparing SQLite provenance database..."
    )

    conn = initialize_database()

    # -------------------------------------------------------------
    # Important:
    #
    # If this is a completely fresh run, there must be no old
    # output.
    #
    # Checkpoints are only meaningful when output already exists.
    # -------------------------------------------------------------

    if not FINAL_RAG.exists():

        # If DB existed independently, rebuild it.
        conn.close()

        if SQLITE_DB.exists():
            SQLITE_DB.unlink()

        conn = initialize_database()

    # -------------------------------------------------------------
    # Build an in-memory hash set from the existing DB.
    #
    # This allows safe resume if checkpoints exist.
    # -------------------------------------------------------------

    print(
        "\nLoading existing deduplication hashes..."
    )

    global_hashes = set()

    cursor = conn.execute(
        """
        SELECT content_hash
        FROM documents
        """
    )

    for row in cursor:
        global_hashes.add(
            row[0]
        )

    output_index_row = conn.execute(
        """
        SELECT COALESCE(
            MAX(output_index),
            0
        )
        FROM documents
        """
    ).fetchone()

    output_index = (
        output_index_row[0]
        if output_index_row
        else 0
    )

    print(
        f"Existing unique hashes: "
        f"{len(global_hashes):,}"
    )

    # -------------------------------------------------------------
    # Final output.
    #
    # append if resuming, otherwise write fresh.
    # -------------------------------------------------------------

    output_mode = (
        "at"
        if FINAL_RAG.exists()
        else "wt"
    )

    overall_start = time.time()

    totals = {
        "files": 0,
        "input_records": 0,
        "valid_records": 0,
        "unique_documents": 0,
        "duplicate_documents": 0,
        "empty_text": 0,
        "short_text": 0,
        "truncated": 0,
        "json_errors": 0,
    }

    source_totals = {}

    # -------------------------------------------------------------
    # Spawn 9 workers.
    # -------------------------------------------------------------

    ctx = mp.get_context(
        "spawn"
    )

    with ProcessPoolExecutor(
        max_workers=WORKERS,
        mp_context=ctx,
    ) as executor:

        with gzip.open(
            FINAL_RAG,
            output_mode,
            encoding="utf-8",
            compresslevel=FINAL_GZIP_LEVEL,
        ) as output:

            # =====================================================
            # FDA
            # =====================================================

            print("\n" + "=" * 72)
            print("DATASET 1 / 3 — FDA")
            print("=" * 72)

            for index, path in enumerate(
                fda_files,
                1,
            ):

                print(
                    f"\nFDA file "
                    f"{index}/{len(fda_files)}"
                )

                if is_completed(
                    "fda",
                    path.name,
                ):

                    print(
                        "  ✓ checkpoint exists — skipping"
                    )

                    continue

                stats, output_index = process_file(
                    "fda",
                    path,
                    executor,
                    output,
                    conn,
                    global_hashes,
                    output_index,
                )

                # -------------------------------------------------
                # Save file statistics.
                # -------------------------------------------------

                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_stats (
                        source,
                        filename,
                        input_records,
                        valid_records,
                        unique_documents,
                        duplicate_documents,
                        empty_text,
                        short_text,
                        truncated,
                        json_errors
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "fda",
                        path.name,
                        stats[
                            "input_records"
                        ],
                        stats[
                            "valid_records"
                        ],
                        stats[
                            "unique_documents"
                        ],
                        stats[
                            "duplicate_documents"
                        ],
                        stats[
                            "empty_text"
                        ],
                        stats[
                            "short_text"
                        ],
                        stats[
                            "truncated"
                        ],
                        stats[
                            "json_errors"
                        ],
                    ),
                )

                conn.commit()

                # -------------------------------------------------
                # Checkpoint ONLY after successful merge.
                # -------------------------------------------------

                mark_completed(
                    "fda",
                    path.name,
                )

                totals[
                    "files"
                ] += 1

                for key in (
                    "input_records",
                    "valid_records",
                    "unique_documents",
                    "duplicate_documents",
                    "empty_text",
                    "short_text",
                    "truncated",
                    "json_errors",
                ):

                    totals[key] += (
                        stats[key]
                    )

            # =====================================================
            # DAILYMED
            # =====================================================

            print("\n" + "=" * 72)
            print("DATASET 2 / 3 — DAILYMED")
            print("=" * 72)

            for index, path in enumerate(
                dailymed_files,
                1,
            ):

                print(
                    f"\nDailyMed file "
                    f"{index}/{len(dailymed_files)}"
                )

                if is_completed(
                    "dailymed",
                    path.name,
                ):

                    print(
                        "  ✓ checkpoint exists — skipping"
                    )

                    continue

                stats, output_index = process_file(
                    "dailymed",
                    path,
                    executor,
                    output,
                    conn,
                    global_hashes,
                    output_index,
                )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_stats (
                        source,
                        filename,
                        input_records,
                        valid_records,
                        unique_documents,
                        duplicate_documents,
                        empty_text,
                        short_text,
                        truncated,
                        json_errors
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "dailymed",
                        path.name,
                        stats[
                            "input_records"
                        ],
                        stats[
                            "valid_records"
                        ],
                        stats[
                            "unique_documents"
                        ],
                        stats[
                            "duplicate_documents"
                        ],
                        stats[
                            "empty_text"
                        ],
                        stats[
                            "short_text"
                        ],
                        stats[
                            "truncated"
                        ],
                        stats[
                            "json_errors"
                        ],
                    ),
                )

                conn.commit()

                mark_completed(
                    "dailymed",
                    path.name,
                )

                totals[
                    "files"
                ] += 1

                for key in (
                    "input_records",
                    "valid_records",
                    "unique_documents",
                    "duplicate_documents",
                    "empty_text",
                    "short_text",
                    "truncated",
                    "json_errors",
                ):

                    totals[key] += (
                        stats[key]
                    )

            # =====================================================
            # CLINICAL TRIALS
            # =====================================================

            print("\n" + "=" * 72)
            print(
                "DATASET 3 / 3 — CLINICAL TRIALS"
            )
            print("=" * 72)

            for index, path in enumerate(
                ct_files,
                1,
            ):

                print(
                    f"\nClinical Trials file "
                    f"{index}/{len(ct_files)}"
                )

                if is_completed(
                    "clinical_trials",
                    path.name,
                ):

                    print(
                        "  ✓ checkpoint exists — skipping"
                    )

                    continue

                stats, output_index = process_file(
                    "clinical_trials",
                    path,
                    executor,
                    output,
                    conn,
                    global_hashes,
                    output_index,
                )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_stats (
                        source,
                        filename,
                        input_records,
                        valid_records,
                        unique_documents,
                        duplicate_documents,
                        empty_text,
                        short_text,
                        truncated,
                        json_errors
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "clinical_trials",
                        path.name,
                        stats[
                            "input_records"
                        ],
                        stats[
                            "valid_records"
                        ],
                        stats[
                            "unique_documents"
                        ],
                        stats[
                            "duplicate_documents"
                        ],
                        stats[
                            "empty_text"
                        ],
                        stats[
                            "short_text"
                        ],
                        stats[
                            "truncated"
                        ],
                        stats[
                            "json_errors"
                        ],
                    ),
                )

                conn.commit()

                mark_completed(
                    "clinical_trials",
                    path.name,
                )

                totals[
                    "files"
                ] += 1

                for key in (
                    "input_records",
                    "valid_records",
                    "unique_documents",
                    "duplicate_documents",
                    "empty_text",
                    "short_text",
                    "truncated",
                    "json_errors",
                ):

                    totals[key] += (
                        stats[key]
                    )

    # -------------------------------------------------------------
    # Final DB commit.
    # -------------------------------------------------------------

    conn.commit()

    unique_documents = conn.execute(
        """
        SELECT COUNT(*)
        FROM documents
        """
    ).fetchone()[0]

    provenance_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM provenance
        """
    ).fetchone()[0]

    conn.close()

    # -------------------------------------------------------------
    # Manifest.
    # -------------------------------------------------------------

    elapsed = (
        time.time()
        - overall_start
    )

    manifest = {
        "dataset": "MediScanAI 2.0",

        "configuration": {
            "workers": WORKERS,
            "processing_mode": (
                "sequential_dataset_"
                "and_sequential_file"
            ),
            "parallelism": (
                "byte_range_parallelism"
            ),
            "record_batch_size": (
                RECORD_BATCH_SIZE
            ),
            "byte_range_size_mb": (
                BYTE_RANGE_SIZE
                / (1024 * 1024)
            ),
            "min_text_chars": (
                MIN_TEXT_CHARS
            ),
            "max_text_chars": (
                MAX_TEXT_CHARS
            ),
            "deduplication": (
                "exact_sha256"
            ),
            "final_gzip_level": (
                FINAL_GZIP_LEVEL
            ),
        },

        "inputs": {
            "fda_files": len(fda_files),
            "dailymed_files": len(
                dailymed_files
            ),
            "clinical_trials_files": len(
                ct_files
            ),
            "total_files": (
                len(fda_files)
                + len(dailymed_files)
                + len(ct_files)
            ),
        },

        "records": {
            "input_records": (
                totals[
                    "input_records"
                ]
            ),
            "valid_records": (
                totals[
                    "valid_records"
                ]
            ),
            "unique_documents": (
                unique_documents
            ),
            "duplicate_documents": (
                totals[
                    "duplicate_documents"
                ]
            ),
            "empty_text": (
                totals[
                    "empty_text"
                ]
            ),
            "short_text": (
                totals[
                    "short_text"
                ]
            ),
            "truncated": (
                totals[
                    "truncated"
                ]
            ),
            "json_errors": (
                totals[
                    "json_errors"
                ]
            ),
            "provenance_rows": (
                provenance_rows
            ),
        },

        "outputs": {
            "rag": str(FINAL_RAG),
            "sqlite": str(SQLITE_DB),
            "manifest": str(MANIFEST),
            "checkpoints": str(
                CHECKPOINT_DIR
            ),
        },

        "runtime": {
            "seconds": round(
                elapsed,
                3,
            ),
            "minutes": round(
                elapsed / 60,
                2,
            ),
        },
    }

    with open(
        MANIFEST,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # -------------------------------------------------------------
    # Final report.
    # -------------------------------------------------------------

    print("\n" + "=" * 72)
    print("FINAL RAG BUILD COMPLETE")
    print("=" * 72)

    print(
        f"\nFiles processed:     "
        f"{totals['files']:,}"
    )

    print(
        f"Input records:       "
        f"{totals['input_records']:,}"
    )

    print(
        f"Valid records:       "
        f"{totals['valid_records']:,}"
    )

    print(
        f"Unique documents:    "
        f"{unique_documents:,}"
    )

    print(
        f"Exact duplicates:    "
        f"{totals['duplicate_documents']:,}"
    )

    print(
        f"Provenance rows:     "
        f"{provenance_rows:,}"
    )

    print(
        f"Empty text:          "
        f"{totals['empty_text']:,}"
    )

    print(
        f"Short text:          "
        f"{totals['short_text']:,}"
    )

    print(
        f"Truncated:           "
        f"{totals['truncated']:,}"
    )

    print(
        f"JSON errors:         "
        f"{totals['json_errors']:,}"
    )

    print(
        f"\nFinal RAG:"
        f"\n  {FINAL_RAG}"
    )

    print(
        f"\nFinal RAG size:"
        f"\n  "
        f"{FINAL_RAG.stat().st_size / (1024**3):.2f} GB"
    )

    print(
        f"\nTotal runtime:"
        f"\n  {elapsed / 60:.2f} minutes"
    )

    print("\n" + "=" * 72)
    print("✓ READY FOR GPU EMBEDDING")
    print("=" * 72)


# =================================================================
# ENTRY POINT
# =================================================================

if __name__ == "__main__":

    mp.freeze_support()

    main()