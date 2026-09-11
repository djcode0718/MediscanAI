#!/usr/bin/env python3

"""
MediScanAI 2.0
Medical RAG Input Profiler

Purpose
-------
Profile the ORIGINAL final_inputs corpus before building final_v2.

We specifically want to understand:
    - FDA structure
    - DailyMed structure
    - Clinical Trial structure
    - long-document distribution
    - documents that would have been truncated by the old 8k limit
    - available metadata
    - section / field patterns
    - how much text is potentially recoverable

IMPORTANT
---------
This script is READ-ONLY.

It does NOT modify:
    results/final/
    data/final_inputs/
    SQLite databases
    source data

Output
------
results/final_v2/profile/
    profile_summary.json
    long_documents.jsonl.gz
    source_statistics.json
    sample_records/
"""

from __future__ import annotations

import gzip
import json
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parents[1]

INPUT_ROOT = BASE / "data" / "final_inputs"

OUTPUT_ROOT = (
    BASE
    / "results"
    / "final_v2"
    / "profile"
)

LONG_OUTPUT = OUTPUT_ROOT / "long_documents.jsonl.gz"
SUMMARY_OUTPUT = OUTPUT_ROOT / "profile_summary.json"
SOURCE_STATS_OUTPUT = OUTPUT_ROOT / "source_statistics.json"

SAMPLES_ROOT = OUTPUT_ROOT / "sample_records"


# ============================================================
# PARAMETERS
# ============================================================

OLD_MAX_CHARS = 8_000

# Keep enough samples to understand the structure.
SAMPLES_PER_SOURCE = 10

# Save these many long examples.
LONG_SAMPLES_PER_SOURCE = 25


SOURCE_DIRS = {
    "fda": INPUT_ROOT / "fda",
    "dailymed": INPUT_ROOT / "dailymed",
    "clinical_trials": INPUT_ROOT / "clinical_trials",
}


# ============================================================
# HELPERS
# ============================================================

def normalize_text(text: Any) -> str:

    if not isinstance(text, str):
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(
        r"\n[ \t]*\n[ \t]*\n+",
        "\n\n",
        text,
    )

    return text.strip()


def get_text(record: Dict[str, Any]) -> str:

    for key in (
        "text",
        "content",
        "body",
        "description",
    ):
        value = record.get(key)

        if isinstance(value, str):
            return normalize_text(value)

    return ""


def get_document_id(record: Dict[str, Any]) -> str:

    for key in (
        "document_id",
        "doc_id",
        "id",
    ):
        value = record.get(key)

        if value is not None:
            return str(value)

    return ""


def flatten_keys(
    obj: Any,
    prefix: str = "",
) -> List[str]:

    keys = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            path = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            keys.append(path)

            keys.extend(
                flatten_keys(
                    value,
                    path,
                )
            )

    elif isinstance(obj, list):

        # Only inspect the first item for schema profiling.
        if obj:
            keys.extend(
                flatten_keys(
                    obj[0],
                    prefix + "[]"
                    if prefix
                    else "[]",
                )
            )

    return keys


def detect_headings(text: str) -> List[str]:

    headings = []

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Numbered section.
        if re.match(
            r"^\d+(?:\.\d+)*[\.\)]?\s+\S+",
            line,
        ):
            headings.append(line[:150])
            continue

        # Common FDA / medical headings.
        upper = line.upper()

        known = (
            "INDICATIONS",
            "DOSAGE",
            "CONTRAINDICATIONS",
            "WARNINGS",
            "PRECAUTIONS",
            "ADVERSE REACTIONS",
            "DRUG INTERACTIONS",
            "CLINICAL PHARMACOLOGY",
            "USE IN SPECIFIC POPULATIONS",
            "OVERDOSAGE",
            "DESCRIPTION",
            "HOW SUPPLIED",
            "CLINICAL STUDIES",
            "ELIGIBILITY",
            "INTERVENTION",
            "OUTCOME",
            "STUDY DESIGN",
        )

        if any(
            upper.startswith(prefix)
            for prefix in known
        ):
            headings.append(line[:150])

    return headings[:50]


def discover_files() -> List[Tuple[str, Path]]:

    files = []

    for source, directory in SOURCE_DIRS.items():

        if not directory.exists():
            print(
                f"WARNING: missing directory: {directory}"
            )
            continue

        for path in sorted(
            directory.rglob("*.jsonl.gz")
        ):
            files.append(
                (source, path)
            )

    return files


def percentile(
    values: List[int],
    p: float,
) -> float:

    if not values:
        return 0.0

    values = sorted(values)

    index = (
        (len(values) - 1)
        * p
    )

    lower = int(index)
    upper = min(
        lower + 1,
        len(values) - 1,
    )

    fraction = index - lower

    return (
        values[lower]
        + (
            values[upper]
            - values[lower]
        )
        * fraction
    )


# ============================================================
# MAIN
# ============================================================

def main():

    start = time.time()

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    SAMPLES_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    for source in SOURCE_DIRS:
        (
            SAMPLES_ROOT / source
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    files = discover_files()

    print("=" * 80)
    print("MEDISCANAI MEDICAL RAG INPUT PROFILER")
    print("=" * 80)

    print(f"\nInput root : {INPUT_ROOT}")
    print(f"Files      : {len(files)}")
    print(
        f"Old cutoff : {OLD_MAX_CHARS:,} characters"
    )

    if not files:
        raise RuntimeError(
            "No *.jsonl.gz files found."
        )

    # --------------------------------------------------------
    # Global statistics
    # --------------------------------------------------------

    source_stats = {}

    global_total = 0
    global_long = 0
    global_valid = 0

    global_lengths = []

    global_keys = Counter()

    global_text_fields = Counter()

    global_long_lengths = []

    source_samples = defaultdict(list)
    source_long_samples = defaultdict(list)

    # --------------------------------------------------------
    # Long document output
    # --------------------------------------------------------

    with gzip.open(
        LONG_OUTPUT,
        "wt",
        encoding="utf-8",
        compresslevel=6,
    ) as long_out:

        for file_index, (source, path) in enumerate(
            files,
            start=1,
        ):

            print(
                f"\n[{file_index}/{len(files)}] "
                f"{source}: {path.name}"
            )

            stats = {
                "files": 1,
                "records": 0,
                "valid_records": 0,
                "long_records": 0,
                "empty_text": 0,
                "missing_document_id": 0,
                "lengths": [],
                "long_lengths": [],
                "keys": Counter(),
                "text_fields": Counter(),
                "heading_counts": Counter(),
            }

            with gzip.open(
                path,
                "rt",
                encoding="utf-8",
                errors="replace",
            ) as f:

                for line_number, line in enumerate(
                    f,
                    start=1,
                ):

                    line = line.strip()

                    if not line:
                        continue

                    stats["records"] += 1
                    global_total += 1

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(record, dict):
                        continue

                    stats["valid_records"] += 1
                    global_valid += 1

                    # -------------------------------
                    # Keys
                    # -------------------------------

                    for key in record.keys():
                        stats["keys"][key] += 1
                        global_keys[key] += 1

                    # -------------------------------
                    # Text
                    # -------------------------------

                    text = get_text(record)

                    if not text:
                        stats["empty_text"] += 1
                        continue

                    # Identify which field supplied text.
                    for field in (
                        "text",
                        "content",
                        "body",
                        "description",
                    ):
                        if isinstance(
                            record.get(field),
                            str,
                        ):
                            stats[
                                "text_fields"
                            ][field] += 1
                            global_text_fields[
                                field
                            ] += 1

                    length = len(text)

                    stats["lengths"].append(
                        length
                    )

                    global_lengths.append(
                        length
                    )

                    document_id = get_document_id(
                        record
                    )

                    if not document_id:
                        stats[
                            "missing_document_id"
                        ] += 1

                    # -------------------------------
                    # Sample records
                    # -------------------------------

                    if len(
                        source_samples[source]
                    ) < SAMPLES_PER_SOURCE:

                        source_samples[source].append(
                            {
                                "file": str(path),
                                "line": line_number,
                                "document_id": document_id,
                                "text_chars": length,
                                "keys": sorted(
                                    record.keys()
                                ),
                                "headings": detect_headings(
                                    text
                                ),
                                "record": record,
                            }
                        )

                    # -------------------------------
                    # Long records
                    # -------------------------------

                    if length > OLD_MAX_CHARS:

                        stats["long_records"] += 1
                        global_long += 1

                        stats[
                            "long_lengths"
                        ].append(length)

                        global_long_lengths.append(
                            length
                        )

                        headings = detect_headings(
                            text
                        )

                        for heading in headings:
                            stats[
                                "heading_counts"
                            ][heading] += 1

                        long_record = {
                            "source": source,
                            "file": str(path),
                            "line": line_number,
                            "document_id": document_id,
                            "text_chars": length,
                            "chars_lost_by_8k_cutoff":
                                length - OLD_MAX_CHARS,
                            "headings": headings,
                            "keys": sorted(
                                record.keys()
                            ),
                            "record": record,
                        }

                        long_out.write(
                            json.dumps(
                                long_record,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )
                            + "\n"
                        )

                        if len(
                            source_long_samples[source]
                        ) < LONG_SAMPLES_PER_SOURCE:

                            source_long_samples[
                                source
                            ].append(
                                long_record
                            )

            # ------------------------------------------------
            # Per-file output
            # ------------------------------------------------

            lengths = stats["lengths"]
            long_lengths = stats["long_lengths"]

            file_summary = {
                "file": str(path),
                "records": stats["records"],
                "valid_records":
                    stats["valid_records"],
                "long_records":
                    stats["long_records"],
                "empty_text":
                    stats["empty_text"],
                "missing_document_id":
                    stats["missing_document_id"],
                "text_length": {
                    "min": min(lengths)
                    if lengths
                    else 0,
                    "max": max(lengths)
                    if lengths
                    else 0,
                    "mean": round(
                        statistics.mean(lengths),
                        2,
                    )
                    if lengths
                    else 0,
                    "p50": round(
                        percentile(lengths, 0.50),
                        2,
                    ),
                    "p90": round(
                        percentile(lengths, 0.90),
                        2,
                    ),
                    "p95": round(
                        percentile(lengths, 0.95),
                        2,
                    ),
                    "p99": round(
                        percentile(lengths, 0.99),
                        2,
                    ),
                },
                "long_text_length": {
                    "count": len(long_lengths),
                    "min": min(long_lengths)
                    if long_lengths
                    else 0,
                    "max": max(long_lengths)
                    if long_lengths
                    else 0,
                    "mean": round(
                        statistics.mean(
                            long_lengths
                        ),
                        2,
                    )
                    if long_lengths
                    else 0,
                    "p50": round(
                        percentile(
                            long_lengths,
                            0.50,
                        ),
                        2,
                    ),
                    "p90": round(
                        percentile(
                            long_lengths,
                            0.90,
                        ),
                        2,
                    ),
                    "p95": round(
                        percentile(
                            long_lengths,
                            0.95,
                        ),
                        2,
                    ),
                    "p99": round(
                        percentile(
                            long_lengths,
                            0.99,
                        ),
                        2,
                    ),
                },
                "top_keys": (
                    stats["keys"]
                    .most_common(50)
                ),
                "text_fields": (
                    stats["text_fields"]
                    .most_common()
                ),
                "top_headings": (
                    stats["heading_counts"]
                    .most_common(50)
                ),
            }

            # Store a compact per-file summary.
            stats.setdefault(
                "summaries",
                []
            )

            source_stats.setdefault(
                source,
                {
                    "files": 0,
                    "records": 0,
                    "valid_records": 0,
                    "long_records": 0,
                    "empty_text": 0,
                    "missing_document_id": 0,
                    "file_summaries": [],
                },
            )

            source_stats[source][
                "files"
            ] += 1

            source_stats[source][
                "records"
            ] += stats["records"]

            source_stats[source][
                "valid_records"
            ] += stats["valid_records"]

            source_stats[source][
                "long_records"
            ] += stats["long_records"]

            source_stats[source][
                "empty_text"
            ] += stats["empty_text"]

            source_stats[source][
                "missing_document_id"
            ] += stats[
                "missing_document_id"
            ]

            source_stats[source][
                "file_summaries"
            ].append(
                file_summary
            )

            print(
                f"  records: {stats['records']:,}"
            )
            print(
                f"  long >8k: "
                f"{stats['long_records']:,}"
            )

    # ========================================================
    # Save source statistics
    # ========================================================

    # Convert Counters if present.
    with open(
        SOURCE_STATS_OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            source_stats,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================
    # Save sample records
    # ========================================================

    for source, samples in source_samples.items():

        path = (
            SAMPLES_ROOT
            / source
            / "normal_samples.json"
        )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                samples,
                f,
                indent=2,
                ensure_ascii=False,
            )

    for source, samples in source_long_samples.items():

        path = (
            SAMPLES_ROOT
            / source
            / "long_samples.json"
        )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                samples,
                f,
                indent=2,
                ensure_ascii=False,
            )

    # ========================================================
    # Global summary
    # ========================================================

    global_summary = {
        "input_root": str(INPUT_ROOT),
        "old_cutoff_chars": OLD_MAX_CHARS,
        "files": len(files),
        "records": global_total,
        "valid_records": global_valid,
        "long_records": global_long,
        "long_fraction": round(
            global_long / global_valid,
            6,
        )
        if global_valid
        else 0,
        "text_length": {
            "min": min(global_lengths)
            if global_lengths
            else 0,
            "max": max(global_lengths)
            if global_lengths
            else 0,
            "mean": round(
                statistics.mean(
                    global_lengths
                ),
                2,
            )
            if global_lengths
            else 0,
            "p50": round(
                percentile(
                    global_lengths,
                    0.50,
                ),
                2,
            ),
            "p90": round(
                percentile(
                    global_lengths,
                    0.90,
                ),
                2,
            ),
            "p95": round(
                percentile(
                    global_lengths,
                    0.95,
                ),
                2,
            ),
            "p99": round(
                percentile(
                    global_lengths,
                    0.99,
                ),
                2,
            ),
        },
        "long_text_length": {
            "count":
                len(global_long_lengths),
            "min":
                min(global_long_lengths)
                if global_long_lengths
                else 0,
            "max":
                max(global_long_lengths)
                if global_long_lengths
                else 0,
            "mean": round(
                statistics.mean(
                    global_long_lengths
                ),
                2,
            )
            if global_long_lengths
            else 0,
            "p50": round(
                percentile(
                    global_long_lengths,
                    0.50,
                ),
                2,
            ),
            "p90": round(
                percentile(
                    global_long_lengths,
                    0.90,
                ),
                2,
            ),
            "p95": round(
                percentile(
                    global_long_lengths,
                    0.95,
                ),
                2,
            ),
            "p99": round(
                percentile(
                    global_long_lengths,
                    0.99,
                ),
                2,
            ),
        },
        "potentially_lost_characters": sum(
            max(
                0,
                length - OLD_MAX_CHARS,
            )
            for length in global_long_lengths
        ),
        "global_keys": (
            global_keys.most_common(100)
        ),
        "text_fields": (
            global_text_fields.most_common()
        ),
        "outputs": {
            "long_documents":
                str(LONG_OUTPUT),
            "source_statistics":
                str(SOURCE_STATS_OUTPUT),
            "samples":
                str(SAMPLES_ROOT),
        },
        "runtime_seconds": round(
            time.time() - start,
            2,
        ),
    }

    with open(
        SUMMARY_OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            global_summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================
    # Console summary
    # ========================================================

    print("\n" + "=" * 80)
    print("PROFILE COMPLETE")
    print("=" * 80)

    print(
        f"\nTotal records      : "
        f"{global_total:,}"
    )

    print(
        f"Valid records      : "
        f"{global_valid:,}"
    )

    print(
        f"Long >8k           : "
        f"{global_long:,}"
    )

    print(
        f"Long fraction      : "
        f"{global_long / global_valid:.2%}"
        if global_valid
        else "Long fraction      : 0%"
    )

    print(
        f"\nGlobal text length:"
    )

    print(
        f"  p50              : "
        f"{global_summary['text_length']['p50']:,.0f}"
    )

    print(
        f"  p90              : "
        f"{global_summary['text_length']['p90']:,.0f}"
    )

    print(
        f"  p95              : "
        f"{global_summary['text_length']['p95']:,.0f}"
    )

    print(
        f"  p99              : "
        f"{global_summary['text_length']['p99']:,.0f}"
    )

    print(
        f"  max              : "
        f"{global_summary['text_length']['max']:,}"
    )

    print(
        f"\nLong-document lengths:"
    )

    print(
        f"  p50              : "
        f"{global_summary['long_text_length']['p50']:,.0f}"
    )

    print(
        f"  p90              : "
        f"{global_summary['long_text_length']['p90']:,.0f}"
    )

    print(
        f"  p95              : "
        f"{global_summary['long_text_length']['p95']:,.0f}"
    )

    print(
        f"  p99              : "
        f"{global_summary['long_text_length']['p99']:,.0f}"
    )

    print(
        f"  max              : "
        f"{global_summary['long_text_length']['max']:,}"
    )

    print(
        f"\nPotentially lost characters "
        f"from old 8k cutoff:"
    )

    print(
        f"  "
        f"{global_summary['potentially_lost_characters']:,}"
    )

    print("\nSource distribution:")

    for source in (
        "fda",
        "dailymed",
        "clinical_trials",
    ):

        stats = source_stats.get(
            source,
            {},
        )

        print(
            f"  {source:20s}"
            f" files={stats.get('files', 0):4d}"
            f" records={stats.get('records', 0):>12,}"
            f" long={stats.get('long_records', 0):>12,}"
        )

    print("\nOutputs:")

    print(
        f"  {SUMMARY_OUTPUT}"
    )

    print(
        f"  {SOURCE_STATS_OUTPUT}"
    )

    print(
        f"  {LONG_OUTPUT}"
    )

    print(
        f"  {SAMPLES_ROOT}"
    )

    print(
        f"\nRuntime: "
        f"{(time.time() - start) / 60:.2f} minutes"
    )

    print("\n✓ READ-ONLY PROFILE")
    print(
        "✓ No existing corpus was modified"
    )


if __name__ == "__main__":
    main()