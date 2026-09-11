#!/usr/bin/env python3

"""
MediScanAI 2.0 — Final RAG V2 Builder

Production-oriented RAG dataset builder.

Key properties
--------------
1. Prefers uncompressed .jsonl inputs over .jsonl.gz.
2. Uses multiple CPU workers for parsing + semantic chunking.
3. Worker output is uncompressed JSONL for fast deterministic merging.
4. Workers include all provenance needed by the merge.
5. Merge NEVER rescans the original input files.
6. SQLite is the exact-dedup authority.
7. No giant Python set of millions of hashes.
8. Deterministic source/file/record ordering.
9. Restart-safe worker checkpoints.
10. Existing validated results/final/ is never touched.

Expected input structure
------------------------
entity_resolution/data/final_inputs/
    fda/
    dailymed/
    clinical_trials/

Output
------
entity_resolution/results/final_v2/
    worker_shards/
    checkpoints/
    final/
        mediscanai_rag_v2.jsonl
        mediscanai_rag_v2.jsonl.gz      # optional archive
        rag_manifest.json
        document_dedup.sqlite
        merge_complete.json
    profile/                             # existing profile untouched

Run
---
python scripts/build_final_rag_v2.py --workers 9

Force complete rebuild
----------------------
python scripts/build_final_rag_v2.py --workers 9 --force

Archive final JSONL as gzip
---------------------------
python scripts/build_final_rag_v2.py --workers 9 --gzip-final
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from tqdm import tqdm


# ============================================================================
# CONFIG
# ============================================================================

SCRIPT_VERSION = "2.1.0"

BASE = Path("/Users/sj/Documents/mediscanai/entity_resolution")

INPUT_ROOT = BASE / "data" / "final_inputs"
OUTPUT_ROOT = BASE / "results" / "final_v2"

SHARD_ROOT = OUTPUT_ROOT / "worker_shards"
CHECKPOINT_ROOT = OUTPUT_ROOT / "checkpoints"
FINAL_ROOT = OUTPUT_ROOT / "final"

FINAL_JSONL = FINAL_ROOT / "mediscanai_rag_v2.jsonl"
FINAL_JSONL_GZ = FINAL_ROOT / "mediscanai_rag_v2.jsonl.gz"
MANIFEST_PATH = FINAL_ROOT / "rag_manifest.json"
SQLITE_PATH = FINAL_ROOT / "document_dedup.sqlite"
MERGE_COMPLETE = FINAL_ROOT / "merge_complete.json"

DEFAULT_WORKERS = 9

# Target semantic chunk size.
TARGET_CHARS = 6000

# Hard maximum.
MAX_CHARS = 10000

# Avoid generating microscopic chunks unless unavoidable.
MIN_CHARS = 300

# Minimum source text to retain.
ABSOLUTE_MIN_CHARS = 40

# Number of rows before committing SQLite transaction.
SQLITE_COMMIT_EVERY = 10_000

# Source order is important for deterministic output.
SOURCE_ORDER = {
    "fda": 0,
    "dailymed": 1,
    "clinical_trials": 2,
}


# ============================================================================
# HELPERS
# ============================================================================

def normalize_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)

    # Normalize common whitespace without destroying paragraph boundaries.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Collapse horizontal whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)

    return text.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def open_jsonl(path: Path):
    """
    Open either uncompressed JSONL or gzip JSONL.
    """

    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def discover_source_files(source_dir: Path) -> list[Path]:
    """
    Prefer .jsonl when both .jsonl and .jsonl.gz exist.

    This is important because the dataset contains both versions.
    """

    uncompressed = sorted(
        p for p in source_dir.glob("*.jsonl")
        if p.is_file()
    )

    compressed = sorted(
        p for p in source_dir.glob("*.jsonl.gz")
        if p.is_file()
    )

    uncompressed_stems = {
        p.name[:-len(".jsonl")]
        for p in uncompressed
    }

    selected = list(uncompressed)

    for p in compressed:
        stem = p.name[:-len(".jsonl.gz")]
        if stem not in uncompressed_stems:
            selected.append(p)

    return sorted(selected)


def discover_inputs() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []

    for source in ("fda", "dailymed", "clinical_trials"):
        directory = INPUT_ROOT / source

        if not directory.exists():
            raise FileNotFoundError(
                f"Missing input directory: {directory}"
            )

        for path in discover_source_files(directory):
            files.append((source, path))

    files.sort(
        key=lambda x: (
            SOURCE_ORDER[x[0]],
            str(x[1]).lower(),
        )
    )

    return files


# ============================================================================
# SEMANTIC CHUNKING
# ============================================================================

def hard_split(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """
    Hard fallback.

    Prefer paragraph/sentence boundaries before cutting arbitrarily.
    """

    text = normalize_text(text)

    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []

    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))

        if end < len(text):
            # Prefer newline.
            newline = text.rfind("\n", start, end)

            if newline > start + int(max_chars * 0.55):
                end = newline

            else:
                # Prefer sentence boundary.
                sentence = max(
                    text.rfind(". ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("! ", start, end),
                )

                if sentence > start + int(max_chars * 0.55):
                    end = sentence + 1

        piece = text[start:end].strip()

        if piece:
            chunks.append(piece)

        start = end

    return chunks


def semantic_pack(blocks: list[str]) -> list[str]:
    """
    Pack logical blocks toward TARGET_CHARS while respecting MAX_CHARS.
    """

    blocks = [
        normalize_text(x)
        for x in blocks
        if normalize_text(x)
    ]

    if not blocks:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush():
        nonlocal current, current_len

        if current:
            value = "\n\n".join(current).strip()

            if value:
                chunks.append(value)

        current = []
        current_len = 0

    for block in blocks:

        if len(block) > MAX_CHARS:
            flush()

            pieces = hard_split(block)

            for piece in pieces:
                if len(piece) <= MAX_CHARS:
                    chunks.append(piece)
                else:
                    # Defensive fallback.
                    for i in range(0, len(piece), MAX_CHARS):
                        chunks.append(
                            piece[i:i + MAX_CHARS].strip()
                        )

            continue

        proposed = (
            len(block)
            if not current
            else current_len + 2 + len(block)
        )

        if current and proposed > TARGET_CHARS:
            flush()

        current.append(block)
        current_len = (
            len(block)
            if len(current) == 1
            else current_len + 2 + len(block)
        )

        # If the current chunk is already large enough,
        # let the next block start a new chunk.
        if current_len >= TARGET_CHARS:
            flush()

    flush()

    # Merge tiny trailing chunk into previous chunk if possible.
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_CHARS:
        combined = chunks[-2] + "\n\n" + chunks[-1]

        if len(combined) <= MAX_CHARS:
            chunks[-2] = combined
            chunks.pop()

    return chunks


# ============================================================================
# FDA
# ============================================================================

FDA_SECTION_NAMES = {
    "BOXED WARNING",
    "INDICATIONS AND USAGE",
    "DOSAGE AND ADMINISTRATION",
    "DOSAGE FORMS AND STRENGTHS",
    "CONTRAINDICATIONS",
    "WARNINGS AND PRECAUTIONS",
    "ADVERSE REACTIONS",
    "DRUG INTERACTIONS",
    "USE IN SPECIFIC POPULATIONS",
    "DRUG ABUSE AND DEPENDENCE",
    "OVERDOSAGE",
    "DESCRIPTION",
    "CLINICAL PHARMACOLOGY",
    "NONCLINICAL TOXICOLOGY",
    "CLINICAL STUDIES",
    "REFERENCES",
    "HOW SUPPLIED",
    "STORAGE AND HANDLING",
    "PATIENT COUNSELING INFORMATION",
}


def chunk_fda(record: dict[str, Any]) -> list[str]:
    text = normalize_text(record.get("text", ""))

    if len(text) < ABSOLUTE_MIN_CHARS:
        return []

    # FDA data is already section-level in our processed corpus.
    # Preserve it as-is when it fits.
    if len(text) <= MAX_CHARS:
        return [text]

    # For unusually large sections, semantic split.
    paragraphs = re.split(r"\n{2,}", text)

    if len(paragraphs) <= 1:
        # Try sentence-level splitting.
        sentences = re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9])",
            text,
        )
        return semantic_pack(sentences)

    return semantic_pack(paragraphs)


# ============================================================================
# DAILYMED
# ============================================================================

# DailyMed flattened text does not reliably retain XML section structure.
# Therefore we use conservative uppercase heading detection.

DAILYMED_HEADINGS = sorted(
    {
        "DESCRIPTION",
        "CLINICAL PHARMACOLOGY",
        "INDICATIONS AND USAGE",
        "CONTRAINDICATIONS",
        "WARNINGS",
        "WARNINGS AND PRECAUTIONS",
        "PRECAUTIONS",
        "ADVERSE REACTIONS",
        "DRUG INTERACTIONS",
        "DOSAGE AND ADMINISTRATION",
        "HOW SUPPLIED",
        "STORAGE AND HANDLING",
        "OVERDOSAGE",
        "CARCINOGENESIS",
        "MUTAGENESIS",
        "IMPAIRMENT OF FERTILITY",
        "PREGNANCY",
        "NURSING MOTHERS",
        "PEDIATRIC USE",
        "GERIATRIC USE",
        "PATIENT INFORMATION",
        "PATIENT COUNSELING INFORMATION",
        "CLINICAL STUDIES",
        "MECHANISM OF ACTION",
        "PHARMACOKINETICS",
    },
    key=len,
    reverse=True,
)


def split_dailymed_sections(text: str) -> list[str]:
    """
    Conservative heading-based segmentation.

    Because DailyMed text was flattened during preprocessing,
    headings are detected inline rather than assuming they occupy
    their own line.
    """

    positions: list[tuple[int, int, str]] = []

    for heading in DAILYMED_HEADINGS:
        pattern = re.compile(
            rf"(?<![A-Za-z]){re.escape(heading)}(?![A-Za-z])"
        )

        for match in pattern.finditer(text):
            start = match.start()

            # Avoid treating an occurrence deep inside an ordinary
            # lowercase sentence as a heading.
            before = text[max(0, start - 80):start]

            if before and before[-1].isalnum():
                continue

            positions.append(
                (match.start(), match.end(), heading)
            )

    if not positions:
        return re.split(r"\n{2,}", text)

    # Deduplicate overlapping heading matches.
    positions.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    cleaned: list[tuple[int, int, str]] = []

    last_end = -1

    for item in positions:
        if item[0] < last_end:
            continue

        cleaned.append(item)
        last_end = item[1]

    blocks: list[str] = []

    # Preserve pre-heading material.
    first_start = cleaned[0][0]

    if first_start > 0:
        prefix = text[:first_start].strip()

        if prefix:
            blocks.append(prefix)

    for i, (start, end, heading) in enumerate(cleaned):

        next_start = (
            cleaned[i + 1][0]
            if i + 1 < len(cleaned)
            else len(text)
        )

        section = text[start:next_start].strip()

        if section:
            blocks.append(section)

    return blocks


def chunk_dailymed(record: dict[str, Any]) -> list[str]:
    text = normalize_text(record.get("text", ""))

    if len(text) < ABSOLUTE_MIN_CHARS:
        return []

    if len(text) <= MAX_CHARS:
        return [text]

    blocks = split_dailymed_sections(text)

    return semantic_pack(blocks)


# ============================================================================
# CLINICAL TRIALS
# ============================================================================

TRIAL_HEADINGS = [
    "Clinical Trial:",
    "Title:",
    "Official Title:",
    "Study Information:",
    "Conditions:",
    "Interventions:",
    "Study Design:",
    "Eligibility:",
    "Sponsors:",
    "Facilities:",
    "Condition Categories:",
    "Brief Summary:",
    "Detailed Description:",
    "Primary Outcome Measures:",
    "Secondary Outcome Measures:",
    "Other Outcome Measures:",
    "Enrollment:",
    "Study Status:",
    "Locations:",
]


def split_trial_sections(text: str) -> list[tuple[str, str]]:
    """
    Parse flattened ClinicalTrials text using known field labels.

    Returns:
        [(heading, body), ...]
    """

    escaped = "|".join(
        re.escape(x)
        for x in sorted(TRIAL_HEADINGS, key=len, reverse=True)
    )

    pattern = re.compile(
        rf"(?<!\w)({escaped})"
    )

    matches = list(pattern.finditer(text))

    if not matches:
        return [("Trial", text)]

    sections: list[tuple[str, str]] = []

    for i, match in enumerate(matches):

        heading = match.group(1).rstrip(":")

        start = match.end()

        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )

        body = text[start:end].strip()

        if body:
            sections.append((heading, body))

    return sections


def chunk_clinical_trial(record: dict[str, Any]) -> list[str]:
    text = normalize_text(record.get("text", ""))

    if len(text) < ABSOLUTE_MIN_CHARS:
        return []

    if len(text) <= MAX_CHARS:
        return [text]

    sections = split_trial_sections(text)

    # Conditions + Interventions are highly important for our
    # medicine-use retrieval use case, so keep them together.
    blocks: list[str] = []

    i = 0

    while i < len(sections):

        heading, body = sections[i]

        if (
            heading.lower() == "conditions"
            and i + 1 < len(sections)
            and sections[i + 1][0].lower() == "interventions"
        ):
            combined = (
                f"Conditions:\n{body}\n\n"
                f"Interventions:\n{sections[i + 1][1]}"
            )

            blocks.append(combined)
            i += 2
            continue

        blocks.append(
            f"{heading}:\n{body}"
        )

        i += 1

    return semantic_pack(blocks)


# ============================================================================
# SOURCE DISPATCH
# ============================================================================

def chunk_record(
    source: str,
    record: dict[str, Any],
) -> list[str]:

    if source == "fda":
        return chunk_fda(record)

    if source == "dailymed":
        return chunk_dailymed(record)

    if source == "clinical_trials":
        return chunk_clinical_trial(record)

    raise ValueError(f"Unknown source: {source}")


# ============================================================================
# WORKER
# ============================================================================

@dataclass
class WorkerResult:
    source: str
    input_path: str
    shard_path: str
    checkpoint_path: str

    records: int
    valid_records: int
    empty_records: int
    chunks: int

    errors: int
    characters_in: int
    characters_out: int

    elapsed_seconds: float


def worker_process(
    source: str,
    input_path_str: str,
    shard_path_str: str,
    checkpoint_path_str: str,
) -> WorkerResult:

    start_time = time.time()

    input_path = Path(input_path_str)
    shard_path = Path(shard_path_str)
    checkpoint_path = Path(checkpoint_path_str)

    shard_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    temp_shard = shard_path.with_suffix(
        shard_path.suffix + ".tmp"
    )

    records = 0
    valid_records = 0
    empty_records = 0
    chunks_total = 0
    errors = 0

    characters_in = 0
    characters_out = 0

    # IMPORTANT:
    # Worker output is deliberately UNCOMPRESSED.
    # This makes deterministic merge much faster.
    with open(temp_shard, "w", encoding="utf-8") as out:

        with open_jsonl(input_path) as f:

            for source_line, line in enumerate(f, start=1):

                records += 1

                line = line.strip()

                if not line:
                    empty_records += 1
                    continue

                try:
                    record = json.loads(line)

                    if not isinstance(record, dict):
                        errors += 1
                        continue

                    valid_records += 1

                    original_text = normalize_text(
                        record.get("text", "")
                    )

                    characters_in += len(original_text)

                    chunks = chunk_record(
                        source,
                        record,
                    )

                    if not chunks:
                        empty_records += 1
                        continue

                    document_id = str(
                        record.get("document_id")
                        or record.get("trial_id")
                        or f"{source}:{input_path.name}:{source_line}"
                    )

                    chunk_count = len(chunks)

                    for chunk_index, chunk_text in enumerate(chunks):

                        chunk_text = normalize_text(chunk_text)

                        if len(chunk_text) < ABSOLUTE_MIN_CHARS:
                            continue

                        if len(chunk_text) > MAX_CHARS:
                            # Defensive guarantee.
                            pieces = hard_split(chunk_text)

                            for piece_index, piece in enumerate(pieces):

                                if len(piece) < ABSOLUTE_MIN_CHARS:
                                    continue

                                chunk_record_obj = dict(record)

                                chunk_record_obj["text"] = piece

                                chunk_record_obj["content_hash"] = (
                                    sha256_text(piece)
                                )

                                chunk_record_obj["source"] = source

                                chunk_record_obj["rag_chunk"] = {
                                    "parent_document_id": document_id,
                                    "chunk_index": (
                                        chunk_index + piece_index
                                    ),
                                    "chunk_count": chunk_count,
                                    "source_line": source_line,
                                }

                                wrapper = {
                                    "source": source,
                                    "source_file": input_path.name,
                                    "source_line": source_line,
                                    "original_document_id": document_id,
                                    "chunk_index": chunk_index,
                                    "chunk_count": chunk_count,
                                    "record": chunk_record_obj,
                                }

                                out.write(
                                    json.dumps(
                                        wrapper,
                                        ensure_ascii=False,
                                        separators=(",", ":"),
                                    )
                                    + "\n"
                                )

                                chunks_total += 1
                                characters_out += len(piece)

                            continue

                        chunk_record_obj = dict(record)

                        chunk_record_obj["text"] = chunk_text

                        chunk_record_obj["content_hash"] = (
                            sha256_text(chunk_text)
                        )

                        chunk_record_obj["source"] = source

                        chunk_record_obj["rag_chunk"] = {
                            "parent_document_id": document_id,
                            "chunk_index": chunk_index,
                            "chunk_count": chunk_count,
                            "source_line": source_line,
                        }

                        wrapper = {
                            "source": source,
                            "source_file": input_path.name,
                            "source_line": source_line,
                            "original_document_id": document_id,
                            "chunk_index": chunk_index,
                            "chunk_count": chunk_count,
                            "record": chunk_record_obj,
                        }

                        out.write(
                            json.dumps(
                                wrapper,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )
                            + "\n"
                        )

                        chunks_total += 1
                        characters_out += len(chunk_text)

                except Exception:
                    errors += 1

    os.replace(temp_shard, shard_path)

    elapsed = time.time() - start_time

    result = WorkerResult(
        source=source,
        input_path=str(input_path),
        shard_path=str(shard_path),
        checkpoint_path=str(checkpoint_path),
        records=records,
        valid_records=valid_records,
        empty_records=empty_records,
        chunks=chunks_total,
        errors=errors,
        characters_in=characters_in,
        characters_out=characters_out,
        elapsed_seconds=elapsed,
    )

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "script_version": SCRIPT_VERSION,
                "source": source,
                "input_path": str(input_path),
                "shard_path": str(shard_path),
                "records": records,
                "valid_records": valid_records,
                "empty_records": empty_records,
                "chunks": chunks_total,
                "errors": errors,
                "characters_in": characters_in,
                "characters_out": characters_out,
                "elapsed_seconds": elapsed,
            },
            f,
            indent=2,
        )

    return result


# ============================================================================
# SQLITE
# ============================================================================

def initialize_sqlite(path: Path) -> sqlite3.Connection:

    if path.exists():
        path.unlink()

    conn = sqlite3.connect(str(path))

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")

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

        CREATE INDEX idx_documents_document_id
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

        CREATE TABLE input_records (
            source TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_line INTEGER NOT NULL,
            original_document_id TEXT,
            chunk_count INTEGER,
            status TEXT NOT NULL,
            PRIMARY KEY(source, source_file, source_line)
        );

        CREATE TABLE file_stats (
            source TEXT NOT NULL,
            source_file TEXT NOT NULL,
            records INTEGER NOT NULL,
            valid_records INTEGER NOT NULL,
            empty_records INTEGER NOT NULL,
            chunks INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            characters_in INTEGER NOT NULL,
            characters_out INTEGER NOT NULL,
            elapsed_seconds REAL NOT NULL,
            PRIMARY KEY(source, source_file)
        );
        """
    )

    conn.commit()

    return conn


# ============================================================================
# MERGE
# ============================================================================

def merge_shards(
    inputs: list[tuple[str, Path]],
    worker_results: dict[str, WorkerResult],
) -> dict[str, Any]:

    print()
    print("=" * 78)
    print("DETERMINISTIC MERGE")
    print("=" * 78)

    FINAL_ROOT.mkdir(parents=True, exist_ok=True)

    # Remove partial merge artifacts only.
    for path in (
        FINAL_JSONL,
        FINAL_JSONL_GZ,
        MANIFEST_PATH,
        SQLITE_PATH,
        MERGE_COMPLETE,
    ):
        if path.exists():
            path.unlink()

    # Remove WAL/SHM files if present.
    for suffix in ("-wal", "-shm"):
        p = Path(str(SQLITE_PATH) + suffix)
        if p.exists():
            p.unlink()

    conn = initialize_sqlite(SQLITE_PATH)

    output_records = 0
    duplicate_records = 0
    input_records = 0
    provenance_records = 0

    source_stats: dict[str, dict[str, int]] = {}

    start_time = time.time()

    with open(FINAL_JSONL, "w", encoding="utf-8") as final_out:

        for file_index, (source, input_path) in enumerate(
            inputs,
            start=1,
        ):

            key = str(input_path)

            result = worker_results.get(key)

            if result is None:
                raise RuntimeError(
                    f"Missing worker result for {input_path}"
                )

            shard_path = Path(result.shard_path)

            if not shard_path.exists():
                raise FileNotFoundError(
                    f"Missing shard: {shard_path}"
                )

            file_records = 0
            file_chunks = 0

            # Track source lines encountered in this shard.
            seen_lines: set[int] = set()

            with open(
                shard_path,
                "r",
                encoding="utf-8",
            ) as shard:

                for line in shard:

                    wrapper = json.loads(line)

                    source_line = int(
                        wrapper["source_line"]
                    )

                    original_document_id = str(
                        wrapper["original_document_id"]
                    )

                    chunk_index = int(
                        wrapper["chunk_index"]
                    )

                    chunk_count = int(
                        wrapper["chunk_count"]
                    )

                    record = wrapper["record"]

                    text = normalize_text(
                        record.get("text", "")
                    )

                    if len(text) < ABSOLUTE_MIN_CHARS:
                        continue

                    if len(text) > MAX_CHARS:
                        raise RuntimeError(
                            f"Worker emitted > MAX_CHARS: "
                            f"{source}/{input_path.name}:"
                            f"{source_line}"
                        )

                    content_hash = record.get(
                        "content_hash"
                    )

                    if not content_hash:
                        content_hash = sha256_text(text)
                        record["content_hash"] = content_hash

                    # Always preserve provenance, including duplicates.
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
                            input_path.name,
                            source_line,
                            original_document_id,
                            chunk_index,
                            chunk_count,
                        ),
                    )

                    provenance_records += 1

                    seen_lines.add(source_line)

                    # SQLite is the dedup authority.
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO documents (
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
                            output_records,
                            content_hash,
                            original_document_id,
                            source,
                            input_path.name,
                            source_line,
                            chunk_index,
                            chunk_count,
                        ),
                    )

                    if cursor.rowcount == 1:

                        record["rag_index"] = output_records

                        final_out.write(
                            json.dumps(
                                record,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )
                            + "\n"
                        )

                        output_records += 1

                    else:
                        duplicate_records += 1

                    file_chunks += 1

                    if (
                        provenance_records
                        % SQLITE_COMMIT_EVERY
                        == 0
                    ):
                        conn.commit()

            # Input record count is reconstructed from unique
            # source-line identifiers present in the shard.
            #
            # This is metadata only; it does NOT trigger a rescan
            # of the original input file.
            input_records += len(seen_lines)

            source_stats.setdefault(
                source,
                {
                    "files": 0,
                    "records": 0,
                    "chunks": 0,
                    "unique_documents": 0,
                    "duplicates": 0,
                },
            )

            source_stats[source]["files"] += 1
            source_stats[source]["records"] += result.records
            source_stats[source]["chunks"] += file_chunks

            print(
                f"[MERGED {file_index:3d}/{len(inputs)}] "
                f"{source:15s} "
                f"{input_path.name:55s} "
                f"records={result.records:,} "
                f"chunks={file_chunks:,} "
                f"unique_so_far={output_records:,}"
            )

            conn.commit()

    conn.commit()

    elapsed = time.time() - start_time

    # Compute source unique counts directly from SQLite.
    for source in source_stats:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE source = ?
            """,
            (source,),
        ).fetchone()

        source_stats[source]["unique_documents"] = int(row[0])

        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM provenance
            WHERE source = ?
            """,
            (source,),
        ).fetchone()

        source_stats[source]["provenance"] = int(row[0])

        source_stats[source]["duplicates"] = (
            source_stats[source]["provenance"]
            - source_stats[source]["unique_documents"]
        )

    conn.commit()

    conn.close()

    return {
        "input_records": input_records,
        "provenance_records": provenance_records,
        "output_unique_documents": output_records,
        "duplicate_chunks": duplicate_records,
        "elapsed_seconds": elapsed,
        "source_statistics": source_stats,
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_final(
    expected_input_records: int,
    expected_unique: int,
    expected_provenance: int,
) -> dict[str, Any]:

    print()
    print("=" * 78)
    print("FINAL VALIDATION")
    print("=" * 78)

    start = time.time()

    if not FINAL_JSONL.exists():
        raise RuntimeError("Final JSONL does not exist.")

    conn = sqlite3.connect(str(SQLITE_PATH))

    row = conn.execute(
        "SELECT COUNT(*) FROM documents"
    ).fetchone()

    sqlite_documents = int(row[0])

    row = conn.execute(
        "SELECT COUNT(*) FROM provenance"
    ).fetchone()

    sqlite_provenance = int(row[0])

    row = conn.execute(
        "SELECT COUNT(*) FROM input_records"
    ).fetchone()

    sqlite_input_records = int(row[0])

    if sqlite_documents != expected_unique:
        raise RuntimeError(
            f"SQLite documents mismatch: "
            f"{sqlite_documents:,} != {expected_unique:,}"
        )

    if sqlite_provenance != expected_provenance:
        raise RuntimeError(
            f"SQLite provenance mismatch: "
            f"{sqlite_provenance:,} != {expected_provenance:,}"
        )

    json_lines = 0
    unique_hashes = set()

    invalid_json = 0
    missing_text = 0
    short_text = 0
    oversized = 0
    missing_hash = 0
    bad_hash = 0
    missing_rag_index = 0

    previous_rag_index = -1

    with open(
        FINAL_JSONL,
        "r",
        encoding="utf-8",
    ) as f:

        for line in tqdm(
            f,
            desc="Validating final JSONL",
            unit=" docs",
        ):

            json_lines += 1

            try:
                record = json.loads(line)
            except Exception:
                invalid_json += 1
                continue

            text = record.get("text")

            if not text:
                missing_text += 1
                continue

            text = str(text)

            if len(text) < ABSOLUTE_MIN_CHARS:
                short_text += 1

            if len(text) > MAX_CHARS:
                oversized += 1

            content_hash = record.get(
                "content_hash"
            )

            if not content_hash:
                missing_hash += 1
            else:
                unique_hashes.add(content_hash)

                actual = sha256_text(text)

                if actual != content_hash:
                    bad_hash += 1

            rag_index = record.get("rag_index")

            if rag_index is None:
                missing_rag_index += 1
            else:
                if int(rag_index) != previous_rag_index + 1:
                    raise RuntimeError(
                        "rag_index is not contiguous/deterministic"
                    )

                previous_rag_index = int(rag_index)

    conn.close()

    checks = {
        "json_lines": json_lines,
        "sqlite_documents": sqlite_documents,
        "sqlite_provenance": sqlite_provenance,
        "sqlite_input_records": sqlite_input_records,
        "expected_input_records": expected_input_records,
        "unique_content_hashes": len(unique_hashes),
        "invalid_json": invalid_json,
        "missing_text": missing_text,
        "short_text": short_text,
        "oversized": oversized,
        "missing_hash": missing_hash,
        "bad_hash": bad_hash,
        "missing_rag_index": missing_rag_index,
        "elapsed_seconds": time.time() - start,
    }

    print()
    for key, value in checks.items():
        if isinstance(value, float):
            print(f"{key:30s}: {value:.2f}")
        else:
            print(f"{key:30s}: {value:,}" if isinstance(value, int) else f"{key:30s}: {value}")

    failures = []

    if json_lines != expected_unique:
        failures.append("JSON line count mismatch")

    if sqlite_documents != expected_unique:
        failures.append("SQLite document count mismatch")

    if len(unique_hashes) != expected_unique:
        failures.append("Final content hashes are not unique")

    if invalid_json:
        failures.append("Invalid JSON")

    if missing_text:
        failures.append("Missing text")

    if oversized:
        failures.append("Oversized text")

    if missing_hash:
        failures.append("Missing content hash")

    if bad_hash:
        failures.append("Bad SHA-256")

    if missing_rag_index:
        failures.append("Missing rag_index")

    if sqlite_provenance != expected_provenance:
        failures.append("Provenance mismatch")

    if failures:
        raise RuntimeError(
            "VALIDATION FAILED:\n - "
            + "\n - ".join(failures)
        )

    print()
    print("ALL FINAL RAG V2 VALIDATION CHECKS PASSED")

    return checks


# ============================================================================
# MANIFEST
# ============================================================================

def write_manifest(
    inputs: list[tuple[str, Path]],
    worker_results: dict[str, WorkerResult],
    merge_stats: dict[str, Any],
    validation: dict[str, Any],
    gzip_final: bool,
):

    manifest = {
        "dataset": "MediScanAI 2.0",
        "builder": "final_rag_v2",
        "builder_version": SCRIPT_VERSION,
        "created_at_unix": time.time(),

        "configuration": {
            "workers": DEFAULT_WORKERS,
            "target_chars": TARGET_CHARS,
            "max_chars": MAX_CHARS,
            "min_chars": MIN_CHARS,
            "absolute_min_chars": ABSOLUTE_MIN_CHARS,
            "prefer_uncompressed_jsonl": True,
            "gzip_final_archive": gzip_final,
        },

        "input": {
            "root": str(INPUT_ROOT),
            "files": len(inputs),
            "sources": {
                source: sum(
                    1
                    for s, _ in inputs
                    if s == source
                )
                for source in (
                    "fda",
                    "dailymed",
                    "clinical_trials",
                )
            },
        },

        "records": {
            "input": merge_stats["input_records"],
            "provenance": merge_stats["provenance_records"],
            "unique_documents": merge_stats[
                "output_unique_documents"
            ],
            "duplicate_chunks": merge_stats[
                "duplicate_chunks"
            ],
        },

        "source_statistics": merge_stats[
            "source_statistics"
        ],

        "timing": {
            "merge_seconds": merge_stats[
                "elapsed_seconds"
            ],
            "validation_seconds": validation[
                "elapsed_seconds"
            ],
        },

        "outputs": {
            "jsonl": str(FINAL_JSONL),
            "jsonl_gz": (
                str(FINAL_JSONL_GZ)
                if gzip_final
                else None
            ),
            "sqlite": str(SQLITE_PATH),
        },

        "validation": validation,
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
            ensure_ascii=False,
        )


# ============================================================================
# OPTIONAL FINAL GZIP
# ============================================================================

def gzip_final_output():

    print()
    print("Creating optional gzip archive...")

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
                length=1024 * 1024 * 8,
            )

    elapsed = time.time() - start

    print(
        f"Compressed archive created in {elapsed:.1f}s"
    )

    print(
        f"Archive: {FINAL_JSONL_GZ}"
    )


# ============================================================================
# MAIN
# ============================================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description="MediScanAI 2.0 Final RAG V2 Builder"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete V2 worker shards/checkpoints/final outputs and rebuild.",
    )

    parser.add_argument(
        "--gzip-final",
        action="store_true",
        help="Also create final .jsonl.gz archive after validation.",
    )

    return parser.parse_args()


def main():

    args = parse_args()

    workers = max(
        1,
        int(args.workers),
    )

    print("=" * 78)
    print("MEDISCANAI 2.0 — FINAL RAG V2 BUILDER")
    print("=" * 78)

    print(f"Input   : {INPUT_ROOT}")
    print(f"Output  : {OUTPUT_ROOT}")
    print(f"Workers : {workers}")
    print(f"Version : {SCRIPT_VERSION}")

    if not INPUT_ROOT.exists():
        raise FileNotFoundError(
            f"Input root does not exist: {INPUT_ROOT}"
        )

    # ---------------------------------------------------------------------
    # FORCE CLEAN
    # ---------------------------------------------------------------------

    if args.force:

        print()
        print("FORCE MODE: clearing V2 build artifacts...")

        for path in (
            SHARD_ROOT,
            CHECKPOINT_ROOT,
            FINAL_ROOT,
        ):
            if path.exists():
                shutil.rmtree(path)

    SHARD_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    CHECKPOINT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINAL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------------------
    # DISCOVER
    # ---------------------------------------------------------------------

    print()
    print("Discovering input files...")

    inputs = discover_inputs()

    if not inputs:
        raise RuntimeError(
            "No input files found."
        )

    print(
        f"Discovered {len(inputs)} input files."
    )

    for source in (
        "fda",
        "dailymed",
        "clinical_trials",
    ):

        count = sum(
            1
            for s, _ in inputs
            if s == source
        )

        print(
            f"  {source:16s}: {count}"
        )

    # Explicitly show whether compressed files are being used.
    compressed_count = sum(
        1
        for _, path in inputs
        if path.name.endswith(".gz")
    )

    uncompressed_count = len(inputs) - compressed_count

    print()
    print(
        f"Uncompressed inputs selected: {uncompressed_count}"
    )
    print(
        f"Compressed-only inputs selected: {compressed_count}"
    )

    # ---------------------------------------------------------------------
    # WORKER JOBS
    # ---------------------------------------------------------------------

    print()
    print(
        f"Starting {workers} CPU workers..."
    )

    worker_results: dict[str, WorkerResult] = {}

    jobs = []

    for index, (source, input_path) in enumerate(
        inputs
    ):

        # One shard per input file.
        # This makes provenance and deterministic merge extremely simple.
        safe_name = input_path.name.replace(
            ".jsonl.gz",
            "",
        ).replace(
            ".jsonl",
            "",
        )

        shard_name = (
            f"{index:04d}_{source}_{safe_name}.jsonl"
        )

        checkpoint_name = (
            f"{index:04d}_{source}_{safe_name}.json"
        )

        shard_path = (
            SHARD_ROOT / shard_name
        )

        checkpoint_path = (
            CHECKPOINT_ROOT / checkpoint_name
        )

        key = str(input_path)

        # Resume only if both checkpoint and shard exist.
        if (
            checkpoint_path.exists()
            and shard_path.exists()
            and not args.force
        ):

            with open(
                checkpoint_path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            worker_results[key] = WorkerResult(
                source=data["source"],
                input_path=data["input_path"],
                shard_path=data["shard_path"],
                checkpoint_path=data["checkpoint_path"]
                if "checkpoint_path" in data
                else str(checkpoint_path),
                records=data["records"],
                valid_records=data["valid_records"],
                empty_records=data["empty_records"],
                chunks=data["chunks"],
                errors=data["errors"],
                characters_in=data["characters_in"],
                characters_out=data["characters_out"],
                elapsed_seconds=data[
                    "elapsed_seconds"
                ],
            )

            continue

        jobs.append(
            (
                source,
                str(input_path),
                str(shard_path),
                str(checkpoint_path),
            )
        )

    print(
        f"Pending worker files: {len(jobs)}"
    )

    # ---------------------------------------------------------------------
    # RUN WORKERS
    # ---------------------------------------------------------------------

    if jobs:

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=workers
        ) as executor:

            future_map = {
                executor.submit(
                    worker_process,
                    *job,
                ): job
                for job in jobs
            }

            with tqdm(
                total=len(jobs),
                desc="Worker files",
                unit="file",
            ) as progress:

                for future in concurrent.futures.as_completed(
                    future_map
                ):

                    job = future_map[future]

                    result = future.result()

                    worker_results[
                        result.input_path
                    ] = result

                    progress.update(1)

    else:
        print(
            "All worker shards already complete."
        )

    # ---------------------------------------------------------------------
    # VERIFY WORKER COMPLETENESS
    # ---------------------------------------------------------------------

    if len(worker_results) != len(inputs):

        missing = [
            str(path)
            for _, path in inputs
            if str(path) not in worker_results
        ]

        raise RuntimeError(
            "Missing worker results:\n"
            + "\n".join(missing[:20])
        )

    total_worker_records = sum(
        r.records
        for r in worker_results.values()
    )

    total_worker_chunks = sum(
        r.chunks
        for r in worker_results.values()
    )

    total_worker_errors = sum(
        r.errors
        for r in worker_results.values()
    )

    print()
    print("WORKER STAGE COMPLETE")
    print(
        f"Input records : {total_worker_records:,}"
    )
    print(
        f"Chunks        : {total_worker_chunks:,}"
    )
    print(
        f"Errors        : {total_worker_errors:,}"
    )

    if total_worker_errors:
        raise RuntimeError(
            f"Worker stage encountered "
            f"{total_worker_errors:,} errors."
        )

    # ---------------------------------------------------------------------
    # MERGE
    # ---------------------------------------------------------------------

    merge_stats = merge_shards(
        inputs,
        worker_results,
    )

    # ---------------------------------------------------------------------
    # VALIDATE
    # ---------------------------------------------------------------------

    validation = validate_final(
        expected_input_records=total_worker_records,
        expected_unique=merge_stats[
            "output_unique_documents"
        ],
        expected_provenance=merge_stats[
            "provenance_records"
        ],
    )

    # ---------------------------------------------------------------------
    # MANIFEST
    # ---------------------------------------------------------------------

    write_manifest(
        inputs,
        worker_results,
        merge_stats,
        validation,
        args.gzip_final,
    )

    # ---------------------------------------------------------------------
    # OPTIONAL GZIP
    # ---------------------------------------------------------------------

    if args.gzip_final:
        gzip_final_output()

    # ---------------------------------------------------------------------
    # COMPLETE MARKER
    # ---------------------------------------------------------------------

    with open(
        MERGE_COMPLETE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "completed": True,
                "script_version": SCRIPT_VERSION,
                "timestamp": time.time(),
                "documents": merge_stats[
                    "output_unique_documents"
                ],
                "input_records": total_worker_records,
            },
            f,
            indent=2,
        )

    print()
    print("=" * 78)
    print("FINAL RAG V2 BUILD COMPLETE")
    print("=" * 78)

    print(
        f"Final documents : "
        f"{merge_stats['output_unique_documents']:,}"
    )

    print(
        f"Input records   : "
        f"{total_worker_records:,}"
    )

    print(
        f"Duplicates      : "
        f"{merge_stats['duplicate_chunks']:,}"
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

    if args.gzip_final:
        print()
        print(
            f"Archive:"
        )
        print(
            f"  {FINAL_JSONL_GZ}"
        )


if __name__ == "__main__":
    main()