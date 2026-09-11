#!/usr/bin/env python3
"""
MediScanAI 2.0 — FDA Corpus Index Builder.
Builds and serializes all data-driven lexical and structural indexes
from FDA normalized names, storing metadata and precomputed corpus statistics.
"""

from __future__ import annotations
import gzip
import json
import math
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path
from tqdm import tqdm

from normalization import parse_intervention

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INDEX_DIR = DATA_DIR / "indexes"
FDA_FILE = DATA_DIR / "fda_names.jsonl.gz"
INDEX_FILE = INDEX_DIR / "fda_name_index.pkl"
METADATA_FILE = INDEX_DIR / "index_metadata.json"

INDEX_DIR.mkdir(parents=True, exist_ok=True)


def main():
    start_time = time.time()
    print("=" * 80)
    print("MEDISCANAI 2.0 — DATA-DRIVEN FDA INDEX BUILDER")
    print("=" * 80)

    if not FDA_FILE.exists():
        raise FileNotFoundError(f"FDA file missing: {FDA_FILE}")

    name_to_ids = defaultdict(set)
    record_count = 0

    print("Step 1/3: Loading FDA Records...")
    with gzip.open(FDA_FILE, "rt", encoding="utf-8") as f:
        for line in tqdm(f, desc="Reading FDA Names", unit="lines"):
            if not line.strip():
                continue
            obj = json.loads(line)
            raw_name = obj.get("normalized_name")
            cid = obj.get("canonical_drug_id")
            if not raw_name or not cid:
                continue
            name = str(raw_name).strip()
            if not name:
                continue
            name_to_ids[name].add(cid)
            record_count += 1

    fda_names = list(name_to_ids.keys())
    total_names = len(fda_names)
    print(f"Loaded {record_count:,} records ({total_names:,} unique FDA names).")

    print("\nStep 2/3: Building Representation & Inverted Indexes...")
    normalized_cache = {}
    compact_cache = {}
    tokens_cache = {}
    identifiers_cache = {}
    radiolabels_cache = {}

    exact_index = defaultdict(list)
    compact_index = defaultdict(list)
    identifier_index = defaultdict(list)
    token_index = defaultdict(set)
    ngram_index = defaultdict(set)

    token_df = Counter()
    ngram_df = Counter()

    for name in tqdm(fda_names, desc="Parsing FDA Names"):
        parsed = parse_intervention(name)
        normalized_cache[name] = parsed.normalized
        compact_cache[name] = parsed.compact
        tokens_cache[name] = parsed.tokens
        identifiers_cache[name] = parsed.identifiers
        radiolabels_cache[name] = parsed.radiolabels

        if parsed.normalized:
            exact_index[parsed.normalized].append(name)
        if parsed.compact:
            compact_index[parsed.compact].append(name)
        for ident in parsed.identifiers:
            identifier_index[ident].append(name)

        for token in parsed.tokens:
            token_index[token].add(name)
            token_df[token] += 1

        if parsed.compact and len(parsed.compact) >= 3:
            grams = {
                parsed.compact[i:i + 3]
                for i in range(len(parsed.compact) - 2)
            }
            for gram in grams:
                ngram_index[gram].add(name)
                ngram_df[gram] += 1

    print("\nStep 3/3: Calculating Corpus-Wide IDF Statistics...")
    token_idf = {
        token: math.log((1 + total_names) / (1 + df)) + 1.0
        for token, df in token_df.items()
    }
    ngram_idf = {
        gram: math.log((1 + total_names) / (1 + df)) + 1.0
        for gram, df in ngram_df.items()
    }

    ambiguous_count = sum(1 for ids in name_to_ids.values() if len(ids) > 1)

    index_payload = {
        "fda_records": {k: sorted(list(v)) for k, v in name_to_ids.items()},
        "normalized": normalized_cache,
        "compact": compact_cache,
        "tokens": tokens_cache,
        "identifiers": identifiers_cache,
        "radiolabels": radiolabels_cache,
        "exact_index": dict(exact_index),
        "compact_index": dict(compact_index),
        "identifier_index": dict(identifier_index),
        "token_index": {k: tuple(v) for k, v in token_index.items()},
        "ngram_index": {k: tuple(v) for k, v in ngram_index.items()},
        "token_idf": token_idf,
        "ngram_idf": ngram_idf,
    }

    metadata = {
        "record_count": record_count,
        "unique_names": total_names,
        "unique_exact_keys": len(exact_index),
        "unique_compact_keys": len(compact_index),
        "unique_identifiers": len(identifier_index),
        "unique_tokens": len(token_df),
        "unique_ngrams": len(ngram_df),
        "ambiguous_fda_names": ambiguous_count,
        "build_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.1.0-m4-optimized",
    }

    print(f"Saving serialized index to {INDEX_FILE}...")
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(index_payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    elapsed = time.time() - start_time
    print(f"Index created in {elapsed:.2f} seconds.")
    print(f"Index Size: {INDEX_FILE.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"Ambiguous FDA Names: {ambiguous_count:,} ({(ambiguous_count / total_names) * 100:.2f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()