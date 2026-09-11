#!/usr/bin/env python3

"""
MediScanAI 2.0 — CELL 7
FINAL RAG VALIDATION / AUDIT

Validates the corpus produced by Cell 6.

Checks:
    1. Final RAG exists
    2. Manifest exists
    3. SQLite exists
    4. Expected input file counts
    5. Final JSONL validity
    6. Required fields
    7. Empty/short text
    8. Content-hash correctness
    9. Duplicate content hashes
    10. Source distribution
    11. rag_index continuity
    12. SQLite document count
    13. SQLite provenance count
    14. Final output size
    15. Manifest consistency

This is READ-ONLY.
It does NOT modify:
    - raw data
    - final RAG
    - checkpoints
    - SQLite
    - input files

Designed for:
    MacBook M4
    10 cores

No multiprocessing is used here because this is an audit pass,
not a transformation pass. Sequential streaming keeps RAM usage
very low and avoids competing for disk bandwidth.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path


# ================================================================
# PATHS
# ================================================================

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


# ================================================================
# EXPECTED INPUTS
# ================================================================

EXPECTED_FDA_FILES = 14
EXPECTED_DAILYMED_FILES = 222
EXPECTED_CT_FILES = 1

MIN_TEXT_CHARS = 40
MAX_TEXT_CHARS = 8000


# ================================================================
# HELPERS
# ================================================================

def sha256_text(text: str) -> str:

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def human_size(size: int) -> str:

    if size >= 1024 ** 3:
        return f"{size / 1024 ** 3:.2f} GB"

    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.2f} MB"

    if size >= 1024:
        return f"{size / 1024:.2f} KB"

    return f"{size} B"


def fail(message: str):

    print("\n" + "=" * 72)
    print("VALIDATION FAILED")
    print("=" * 72)
    print(message)
    print("=" * 72)

    sys.exit(1)


# ================================================================
# START
# ================================================================

start_time = time.time()

print("=" * 72)
print("MediScanAI 2.0 — CELL 7")
print("FINAL RAG VALIDATION / AUDIT")
print("=" * 72)

print(
    "\nProject:"
    f"\n  {PROJECT_ROOT}"
)

print(
    "\nFinal RAG:"
    f"\n  {FINAL_RAG}"
)


# ================================================================
# 1. EXISTENCE CHECKS
# ================================================================

print("\n" + "=" * 72)
print("1. OUTPUT EXISTENCE")
print("=" * 72)

required_outputs = {
    "Final RAG": FINAL_RAG,
    "Manifest": MANIFEST,
    "SQLite": SQLITE_DB,
}

for name, path in required_outputs.items():

    if not path.exists():
        fail(
            f"{name} is missing:\n{path}"
        )

    print(
        f"✓ {name:<12} "
        f"{human_size(path.stat().st_size):>12} "
        f"{path}"
    )


# ================================================================
# 2. INPUT FILE COUNTS
# ================================================================

print("\n" + "=" * 72)
print("2. INPUT FILE COUNTS")
print("=" * 72)


def jsonl_files(directory: Path):

    return sorted(
        p
        for p in directory.glob(
            "*.jsonl"
        )
        if p.is_file()
    )


fda_files = jsonl_files(FDA_DIR)
dailymed_files = jsonl_files(DAILYMED_DIR)
ct_files = jsonl_files(CT_DIR)

print(
    f"FDA:              "
    f"{len(fda_files)} "
    f"(expected {EXPECTED_FDA_FILES})"
)

print(
    f"DailyMed:         "
    f"{len(dailymed_files)} "
    f"(expected {EXPECTED_DAILYMED_FILES})"
)

print(
    f"Clinical Trials:  "
    f"{len(ct_files)} "
    f"(expected {EXPECTED_CT_FILES})"
)

if len(fda_files) != EXPECTED_FDA_FILES:
    fail("FDA input file count mismatch.")

if len(dailymed_files) != EXPECTED_DAILYMED_FILES:
    fail("DailyMed input file count mismatch.")

if len(ct_files) != EXPECTED_CT_FILES:
    fail("Clinical Trials input file count mismatch.")

print("\n✓ Input file counts correct")


# ================================================================
# 3. MANIFEST VALIDATION
# ================================================================

print("\n" + "=" * 72)
print("3. MANIFEST")
print("=" * 72)

try:

    with open(
        MANIFEST,
        "r",
        encoding="utf-8",
    ) as f:

        manifest = json.load(f)

except Exception as e:

    fail(
        f"Could not read manifest:\n{e}"
    )

print(
    f"Dataset: "
    f"{manifest.get('dataset')}"
)

config = manifest.get(
    "configuration",
    {}
)

print(
    f"Workers: "
    f"{config.get('workers')}"
)

print(
    f"Min text chars: "
    f"{config.get('min_text_chars')}"
)

print(
    f"Max text chars: "
    f"{config.get('max_text_chars')}"
)

print(
    f"Deduplication: "
    f"{config.get('deduplication')}"
)

manifest_inputs = manifest.get(
    "inputs",
    {}
)

if manifest_inputs.get(
    "fda_files"
) != EXPECTED_FDA_FILES:

    fail(
        "Manifest FDA count mismatch."
    )

if manifest_inputs.get(
    "dailymed_files"
) != EXPECTED_DAILYMED_FILES:

    fail(
        "Manifest DailyMed count mismatch."
    )

if manifest_inputs.get(
    "clinical_trials_files"
) != EXPECTED_CT_FILES:

    fail(
        "Manifest Clinical Trials count mismatch."
    )

print(
    "\n✓ Manifest input counts correct"
)


# ================================================================
# 4. STREAM FINAL RAG
# ================================================================

print("\n" + "=" * 72)
print("4. FINAL RAG STREAM VALIDATION")
print("=" * 72)

print(
    "\nReading final RAG sequentially..."
)

total_lines = 0
valid_records = 0
invalid_json = 0

missing_text = 0
short_text = 0
long_text = 0
missing_document_id = 0
missing_hash = 0
bad_hash = 0
bad_source = 0
bad_rag_index = 0

source_counts = Counter()

# In-memory exact hash set.
#
# This is intentionally used here only for validation.
# It allows us to detect duplicate content hashes in the final
# corpus without modifying anything.
hashes = set()

expected_rag_index = 1

sample_records = []

with gzip.open(
    FINAL_RAG,
    "rt",
    encoding="utf-8",
) as f:

    for line in f:

        total_lines += 1

        line = line.strip()

        if not line:
            continue

        try:

            record = json.loads(
                line
            )

        except Exception:

            invalid_json += 1
            continue

        if not isinstance(
            record,
            dict,
        ):

            invalid_json += 1
            continue

        valid_records += 1

        # --------------------------------------------------------
        # Required text
        # --------------------------------------------------------

        text = record.get(
            "text"
        )

        if not isinstance(
            text,
            str,
        ) or not text.strip():

            missing_text += 1

        else:

            text_length = len(
                text
            )

            if text_length < MIN_TEXT_CHARS:
                short_text += 1

            if text_length > MAX_TEXT_CHARS:
                long_text += 1

        # --------------------------------------------------------
        # document_id
        # --------------------------------------------------------

        document_id = record.get(
            "document_id"
        )

        if not document_id:
            missing_document_id += 1

        # --------------------------------------------------------
        # source
        # --------------------------------------------------------

        source = record.get(
            "source"
        )

        if source not in (
            "fda",
            "dailymed",
            "clinical_trials",
        ):

            bad_source += 1

        else:

            source_counts[
                source
            ] += 1

        # --------------------------------------------------------
        # content hash
        # --------------------------------------------------------

        content_hash = record.get(
            "content_hash"
        )

        if not content_hash:

            missing_hash += 1

        elif isinstance(
            text,
            str,
        ):

            calculated_hash = (
                sha256_text(
                    text
                )
            )

            if calculated_hash != content_hash:

                bad_hash += 1

            if content_hash in hashes:

                # Duplicate hash in final output.
                #
                # This should be zero because Cell 6 deduplicates
                # exact content.
                pass

            hashes.add(
                content_hash
            )

        # --------------------------------------------------------
        # rag_index
        # --------------------------------------------------------

        rag_index = record.get(
            "rag_index"
        )

        if rag_index != expected_rag_index:

            bad_rag_index += 1

        expected_rag_index += 1

        # --------------------------------------------------------
        # Keep a few examples for inspection.
        # --------------------------------------------------------

        if len(
            sample_records
        ) < 3:

            sample_records.append(
                record
            )

        # --------------------------------------------------------
        # Progress every 100k records.
        # --------------------------------------------------------

        if valid_records % 100_000 == 0:

            print(
                f"  Validated "
                f"{valid_records:,} records..."
            )


# ================================================================
# 5. FINAL RAG RESULTS
# ================================================================

print("\n" + "=" * 72)
print("5. RAG RESULTS")
print("=" * 72)

print(
    f"\nTotal JSONL lines:     "
    f"{total_lines:,}"
)

print(
    f"Valid records:         "
    f"{valid_records:,}"
)

print(
    f"Invalid JSON:          "
    f"{invalid_json:,}"
)

print(
    f"Unique content hashes: "
    f"{len(hashes):,}"
)

print(
    f"Missing text:          "
    f"{missing_text:,}"
)

print(
    f"Short text:            "
    f"{short_text:,}"
)

print(
    f"Over max length:       "
    f"{long_text:,}"
)

print(
    f"Missing document ID:   "
    f"{missing_document_id:,}"
)

print(
    f"Missing hash:          "
    f"{missing_hash:,}"
)

print(
    f"Bad SHA-256 hash:      "
    f"{bad_hash:,}"
)

print(
    f"Bad source:            "
    f"{bad_source:,}"
)

print(
    f"Bad RAG index:         "
    f"{bad_rag_index:,}"
)


# ================================================================
# 6. SOURCE DISTRIBUTION
# ================================================================

print("\n" + "=" * 72)
print("6. SOURCE DISTRIBUTION")
print("=" * 72)

for source in (
    "fda",
    "dailymed",
    "clinical_trials",
):

    count = source_counts[
        source
    ]

    percentage = (
        count / valid_records * 100
        if valid_records
        else 0
    )

    print(
        f"{source:<18}"
        f"{count:>15,}"
        f"  ({percentage:6.2f}%)"
    )


# ================================================================
# 7. DETECT FINAL DUPLICATES
# ================================================================

print("\n" + "=" * 72)
print("7. EXACT DUPLICATE CHECK")
print("=" * 72)

duplicate_count = (
    valid_records
    - len(hashes)
)

print(
    f"Final records:       "
    f"{valid_records:,}"
)

print(
    f"Unique hashes:       "
    f"{len(hashes):,}"
)

print(
    f"Duplicate records:   "
    f"{duplicate_count:,}"
)

if duplicate_count == 0:

    print(
        "\n✓ No duplicate content hashes "
        "in final RAG"
    )

else:

    print(
        "\n⚠ Duplicate content hashes detected"
    )


# ================================================================
# 8. SQLITE VALIDATION
# ================================================================

print("\n" + "=" * 72)
print("8. SQLITE VALIDATION")
print("=" * 72)

try:

    conn = sqlite3.connect(
        SQLITE_DB
    )

    db_documents = conn.execute(
        """
        SELECT COUNT(*)
        FROM documents
        """
    ).fetchone()[0]

    db_provenance = conn.execute(
        """
        SELECT COUNT(*)
        FROM provenance
        """
    ).fetchone()[0]

    db_files = conn.execute(
        """
        SELECT COUNT(*)
        FROM file_stats
        """
    ).fetchone()[0]

    print(
        f"Documents table:    "
        f"{db_documents:,}"
    )

    print(
        f"Provenance rows:    "
        f"{db_provenance:,}"
    )

    print(
        f"File stats rows:    "
        f"{db_files:,}"
    )

    if db_documents != len(hashes):

        fail(
            "SQLite document count does not "
            "match final RAG unique hash count."
        )

    conn.close()

except Exception as e:

    fail(
        f"SQLite validation failed:\n{e}"
    )

print(
    "\n✓ SQLite document count matches RAG"
)


# ================================================================
# 9. MANIFEST RECORD CHECK
# ================================================================

print("\n" + "=" * 72)
print("9. MANIFEST RECORD COUNTS")
print("=" * 72)

manifest_records = manifest.get(
    "records",
    {}
)

for key in (
    "input_records",
    "valid_records",
    "unique_documents",
    "duplicate_documents",
):

    print(
        f"{key:<24}"
        f"{manifest_records.get(key, 'N/A')}"
    )


manifest_unique = manifest_records.get(
    "unique_documents"
)

if (
    manifest_unique is not None
    and manifest_unique != len(hashes)
):

    fail(
        "Manifest unique document count "
        "does not match final RAG."
    )

print(
    "\n✓ Manifest unique count matches"
)


# ================================================================
# 10. SAMPLE RECORDS
# ================================================================

print("\n" + "=" * 72)
print("10. SAMPLE RECORDS")
print("=" * 72)

for i, record in enumerate(
    sample_records,
    1,
):

    print(
        f"\nSample {i}:"
    )

    print(
        f"  source:       "
        f"{record.get('source')}"
    )

    print(
        f"  document_id:  "
        f"{record.get('document_id')}"
    )

    print(
        f"  rag_index:    "
        f"{record.get('rag_index')}"
    )

    print(
        f"  text chars:   "
        f"{len(record.get('text', '')):,}"
    )

    print(
        f"  hash:         "
        f"{record.get('content_hash')}"
    )

    text_preview = (
        record.get(
            "text",
            "",
        )
        .replace(
            "\n",
            " ",
        )
    )

    print(
        f"  preview:      "
        f"{text_preview[:200]}..."
    )


# ================================================================
# 11. FINAL SAFETY DECISION
# ================================================================

print("\n" + "=" * 72)
print("11. FINAL SAFETY CHECK")
print("=" * 72)

errors = []

if invalid_json:
    errors.append(
        f"invalid JSON={invalid_json:,}"
    )

if missing_text:
    errors.append(
        f"missing text={missing_text:,}"
    )

if short_text:
    errors.append(
        f"short text={short_text:,}"
    )

if missing_document_id:
    errors.append(
        f"missing document_id={missing_document_id:,}"
    )

if missing_hash:
    errors.append(
        f"missing hash={missing_hash:,}"
    )

if bad_hash:
    errors.append(
        f"bad hash={bad_hash:,}"
    )

if bad_source:
    errors.append(
        f"bad source={bad_source:,}"
    )

if bad_rag_index:
    errors.append(
        f"bad rag_index={bad_rag_index:,}"
    )

if duplicate_count:
    errors.append(
        f"duplicate content={duplicate_count:,}"
    )


# ================================================================
# FINAL RESULT
# ================================================================

elapsed = (
    time.time()
    - start_time
)

print(
    f"\nValidation runtime: "
    f"{elapsed / 60:.2f} minutes"
)

if errors:

    print(
        "\n⚠ VALIDATION COMPLETED "
        "WITH ISSUES:"
    )

    for error in errors:
        print(
            f"  ✗ {error}"
        )

    print(
        "\nDo NOT proceed to embedding "
        "until these are reviewed."
    )

    sys.exit(1)


print(
    "\n🎉 ALL FINAL RAG VALIDATION CHECKS PASSED"
)

print(
    "\n✓ JSON validity"
)

print(
    "✓ Required fields"
)

print(
    "✓ SHA-256 integrity"
)

print(
    "✓ No duplicate content"
)

print(
    "✓ Source integrity"
)

print(
    "✓ RAG index continuity"
)

print(
    "✓ SQLite consistency"
)

print(
    "✓ Manifest consistency"
)

print(
    "\n" + "=" * 72
)

print(
    "✓ CELL 7 COMPLETE"
)

print(
    "✓ FINAL RAG CORPUS IS READY FOR EMBEDDING"
)

print(
    "=" * 72
)