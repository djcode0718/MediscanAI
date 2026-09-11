#!/usr/bin/env python3
"""
MediScanAI 2.0 — Main Trial-to-FDA Entity Resolution Engine.
- Multi-core multiprocessing pipeline optimized for Mac M4.
- Atomic gzip checkpoint chunks (chunk_*.jsonl.gz + state.json) for crash-safety.
- Incorporates alias evidence convergence via intervention_id.
"""

import argparse
import gzip
import json
import multiprocessing as mp
import pickle
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm

from normalization import parse_intervention
from candidate_generation import retrieve_candidates
from scoring import evaluate_candidate, classify_match, MatchVerdict

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"
RESULTS_DIR = BASE / "results"
CHECKPOINT_DIR = BASE / "checkpoints"
INDEX_FILE = DATA_DIR / "indexes" / "fda_name_index.pkl"
TRIAL_INTERVENTIONS_FILE = DATA_DIR / "trial_interventions.jsonl.gz"
TRIAL_ALIASES_FILE = DATA_DIR / "trial_aliases.jsonl.gz"
STATE_FILE = CHECKPOINT_DIR / "state.json"

CHUNK_SIZE = 10000

# Global worker index pointer
WORKER_INDEX = None


def init_worker(shared_index):
    global WORKER_INDEX
    WORKER_INDEX = shared_index


def process_single_row(row: dict, aliases_by_intervention: Dict[str, List[str]]) -> dict:
    """Matches a single trial intervention using multi-representation and alias consensus."""
    global WORKER_INDEX
    index = WORKER_INDEX
    fda_records = index["fda_records"]

    query_raw = row.get("intervention_name", "")
    nct_id = row.get("nct_id", "")
    interv_id = str(row.get("intervention_id", ""))
    src = row.get("source_file", "trial_interventions.jsonl.gz")

    q_parsed = parse_intervention(query_raw)
    if q_parsed.is_empty or len(q_parsed.normalized) < 2:
        return {
            "nct_id": nct_id,
            "intervention_id": interv_id,
            "intervention_name": query_raw,
            "normalized_name": q_parsed.normalized,
            "status": "unresolved",
            "match_method": "too_short",
            "canonical_drug_id": None,
            "all_canonical_ids": [],
            "matched_fda_name": None,
            "confidence": 0.0,
            "margin": 0.0,
            "features": {},
            "source_file": src,
        }

    # Generate Candidates
    candidate_names = retrieve_candidates(q_parsed, index)
    scored = []
    for cname in candidate_names:
        feats = evaluate_candidate(
            query_parsed=q_parsed,
            candidate_name=cname,
            cand_normalized=index["normalized"][cname],
            cand_compact=index["compact"][cname],
            cand_tokens=index["tokens"][cname],
            cand_identifiers=index["identifiers"][cname],
            cand_radiolabels=index.get("radiolabels", {}).get(cname, []),
            token_idf=index["token_idf"],
        )
        scored.append((cname, feats))

    scored.sort(key=lambda x: x[1]["composite_score"], reverse=True)
    verdict: MatchVerdict = classify_match(q_parsed, scored, fda_records)

    # Evidence Convergence using Intervention Aliases
    aliases = aliases_by_intervention.get(interv_id, [])
    if aliases and verdict.status in ("resolved_medium", "query_ambiguous", "unresolved"):
        for alias_str in aliases:
            a_parsed = parse_intervention(alias_str)
            if a_parsed.is_empty:
                continue
            a_cands = retrieve_candidates(a_parsed, index, max_token_candidates=50)
            a_scored = []
            for cname in a_cands:
                feats = evaluate_candidate(
                    query_parsed=a_parsed,
                    candidate_name=cname,
                    cand_normalized=index["normalized"][cname],
                    cand_compact=index["compact"][cname],
                    cand_tokens=index["tokens"][cname],
                    cand_identifiers=index["identifiers"][cname],
                    cand_radiolabels=index.get("radiolabels", {}).get(cname, []),
                    token_idf=index["token_idf"],
                )
                a_scored.append((cname, feats))
            a_scored.sort(key=lambda x: x[1]["composite_score"], reverse=True)
            a_verdict = classify_match(a_parsed, a_scored, fda_records)

            # Consensus Boost: If alias independently agrees with matched FDA entity
            if (
                a_verdict.canonical_drug_id
                and verdict.matched_fda_name == a_verdict.matched_fda_name
                and verdict.status in ("resolved_medium", "query_ambiguous")
            ):
                verdict.status = "resolved_high"
                verdict.method = f"{verdict.method}+alias_consensus"
                verdict.canonical_drug_id = a_verdict.canonical_drug_id
                verdict.confidence = min(round(verdict.confidence + 0.08, 4), 1.0)
                break

    return {
        "nct_id": nct_id,
        "intervention_id": interv_id,
        "intervention_name": query_raw,
        "normalized_name": q_parsed.normalized,
        "status": verdict.status,
        "match_method": verdict.method,
        "canonical_drug_id": verdict.canonical_drug_id,
        "all_canonical_ids": verdict.all_canonical_ids,
        "matched_fda_name": verdict.matched_fda_name,
        "confidence": verdict.confidence,
        "margin": verdict.margin,
        "features": verdict.features,
        "source_file": src,
    }


def worker_task(batch_and_aliases):
    batch, aliases_map = batch_and_aliases
    return [process_single_row(row, aliases_map) for row in batch]


def load_aliases() -> Dict[str, List[str]]:
    """Loads aliases grouped by intervention_id."""
    if not TRIAL_ALIASES_FILE.exists():
        return {}
    print("Loading Trial Aliases by intervention_id...")
    aliases_by_id = defaultdict(list)
    with gzip.open(TRIAL_ALIASES_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            iid = str(row.get("intervention_id", "")).strip()
            name = row.get("name")
            if iid and name:
                aliases_by_id[iid].append(str(name).strip())
    print(f"Loaded aliases for {len(aliases_by_id):,} unique interventions.")
    return dict(aliases_by_id)


def main():
    parser = argparse.ArgumentParser(description="MediScanAI 2.0 Matcher")
    parser.add_argument("--limit", type=int, default=None, help="Record limit for benchmarking")
    parser.add_argument("--fresh", action="store_true", help="Discard checkpoints and start fresh")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, mp.cpu_count() - 1),
        help="CPU worker count (defaults to available M4 cores - 1)",
    )
    args = parser.parse_args()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MEDISCANAI 2.0 — HIGH-PRECISION TRIAL MATCHER (M4 OPTIMIZED)")
    print("=" * 80)

    if not INDEX_FILE.exists():
        print("ERROR: FDA index missing. Run prepare_index.py first.")
        sys.exit(1)

    print(f"Loading FDA index from {INDEX_FILE}...")
    with open(INDEX_FILE, "rb") as f:
        index_data = pickle.load(f)
    print("FDA Index loaded.")

    aliases_by_id = load_aliases()

    # Load trial interventions
    print(f"Streaming trial interventions from {TRIAL_INTERVENTIONS_FILE}...")
    trial_records = []
    with gzip.open(TRIAL_INTERVENTIONS_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            trial_records.append(json.loads(line))
            if args.limit and len(trial_records) >= args.limit:
                break

    total_records = len(trial_records)
    print(f"Targeting {total_records:,} intervention rows.")

    # State & Resume Handling
    start_chunk = 0
    if not args.fresh and STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            start_chunk = state.get("completed_chunks", 0)
        print(f"Resuming from chunk {start_chunk + 1:,} (already processed {start_chunk * CHUNK_SIZE:,} records).")
    elif args.fresh:
        for p in CHECKPOINT_DIR.glob("chunk_*.jsonl.gz"):
            p.unlink()
        if STATE_FILE.exists():
            STATE_FILE.unlink()

    num_chunks = (total_records + CHUNK_SIZE - 1) // CHUNK_SIZE

    print(f"Processing in {num_chunks} chunks using {args.workers} worker processes...")

    with mp.Pool(processes=args.workers, initializer=init_worker, initargs=(index_data,)) as pool:
        for chunk_idx in range(start_chunk, num_chunks):
            chunk_start = chunk_idx * CHUNK_SIZE
            chunk_end = min(chunk_start + CHUNK_SIZE, total_records)
            chunk_rows = trial_records[chunk_start:chunk_end]

            chunk_filename = CHECKPOINT_DIR / f"chunk_{chunk_idx + 1:06d}.jsonl.gz"

            sub_batch_size = max(1, len(chunk_rows) // (args.workers * 4))
            sub_batches = [
                (chunk_rows[i:i + sub_batch_size], aliases_by_id)
                for i in range(0, len(chunk_rows), sub_batch_size)
            ]

            chunk_results = []
            desc = f"Chunk {chunk_idx + 1}/{num_chunks} [{chunk_start:,}..{chunk_end:,}]"
            for batch_res in tqdm(pool.imap(worker_task, sub_batches), total=len(sub_batches), desc=desc):
                chunk_results.extend(batch_res)

            # Write chunk atomically
            temp_chunk = chunk_filename.with_suffix(".tmp")
            with gzip.open(temp_chunk, "wt", encoding="utf-8") as out:
                for res in chunk_results:
                    out.write(json.dumps(res, ensure_ascii=False) + "\n")
            temp_chunk.replace(chunk_filename)

            # Update State
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"completed_chunks": chunk_idx + 1, "total_records": total_records}, f, indent=2)

    print("\nMatching complete across all chunks.")
    print("Run `python scripts/merge_results.py` to synthesize final outputs.")


if __name__ == "__main__":
    main()