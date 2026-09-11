#!/usr/bin/env python3
"""
MediScanAI 2.0 — Checkpoint Merging, Deduplication & Validation Pipeline.
Validates 100% input accounting, canonical ID validity, and exports clean audited schemas.
"""

import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from tqdm import tqdm

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"
RESULTS_DIR = BASE / "results"
CHECKPOINT_DIR = BASE / "checkpoints"
INDEX_FILE = DATA_DIR / "indexes" / "fda_name_index.pkl"

RESOLVED_OUT = RESULTS_DIR / "resolved_trial_interventions.jsonl.gz"
AMBIGUOUS_OUT = RESULTS_DIR / "ambiguous_trial_interventions.jsonl.gz"
UNRESOLVED_OUT = RESULTS_DIR / "unresolved_trial_interventions.jsonl.gz"
DIAGNOSTICS_OUT = RESULTS_DIR / "match_diagnostics.jsonl.gz"
SUMMARY_OUT = RESULTS_DIR / "summary.json"


def main():
    print("=" * 80)
    print("MEDISCANAI 2.0 — RESULTS MERGE & INTEGRITY AUDIT")
    print("=" * 80)

    chunk_files = sorted(list(CHECKPOINT_DIR.glob("chunk_*.jsonl.gz")))
    if not chunk_files:
        print(f"No checkpoint chunk files found in {CHECKPOINT_DIR}.")
        sys.exit(1)

    print(f"Found {len(chunk_files)} chunk files to merge.")

    # Load Universe of Valid FDA Canonical Drug IDs
    print("Loading valid FDA canonical drug ID universe...")
    import pickle
    with open(INDEX_FILE, "rb") as f:
        index_data = pickle.load(f)
    fda_records = index_data["fda_records"]
    valid_canonical_ids = {cid for ids in fda_records.values() for cid in ids}
    print(f"Valid FDA Canonical ID universe size: {len(valid_canonical_ids):,}")

    total_records = 0
    status_counts = Counter()
    method_counts = Counter()
    invalid_ids_found = 0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with gzip.open(RESOLVED_OUT, "wt", encoding="utf-8") as res_f, \
         gzip.open(AMBIGUOUS_OUT, "wt", encoding="utf-8") as amb_f, \
         gzip.open(UNRESOLVED_OUT, "wt", encoding="utf-8") as unres_f, \
         gzip.open(DIAGNOSTICS_OUT, "wt", encoding="utf-8") as diag_f:

        for cpath in tqdm(chunk_files, desc="Merging Chunks"):
            with gzip.open(cpath, "rt", encoding="utf-8") as cin:
                for line in cin:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    total_records += 1
                    status = row.get("status")
                    method = row.get("match_method")
                    cid = row.get("canonical_drug_id")

                    status_counts[status] += 1
                    method_counts[method] += 1

                    # Canonical ID Integrity Check
                    if cid and cid not in valid_canonical_ids:
                        invalid_ids_found += 1
                        row["status"] = "unresolved"
                        row["match_method"] = "invalid_canonical_id_detected"
                        row["canonical_drug_id"] = None
                        status = "unresolved"

                    # Diagnostics Output (Complete audit trail)
                    diag_f.write(json.dumps(row, ensure_ascii=False) + "\n")

                    # Partitioned Scientific Exports
                    if status in ("resolved_high", "resolved_medium"):
                        res_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    elif status in ("name_ambiguous", "query_ambiguous"):
                        amb_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    else:
                        unres_f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Strict Validation Invariant Check
    resolved_total = status_counts["resolved_high"] + status_counts["resolved_medium"]
    ambiguous_total = status_counts["name_ambiguous"] + status_counts["query_ambiguous"]
    unresolved_total = status_counts["unresolved"]

    sum_accounted = resolved_total + ambiguous_total + unresolved_total
    assert sum_accounted == total_records, (
        f"Validation Error: Accounted ({sum_accounted}) != Total Processed ({total_records})"
    )
    assert invalid_ids_found == 0, f"Critical: Found {invalid_ids_found} invalid canonical IDs."

    summary = {
        "total_records_processed": total_records,
        "resolved_high": status_counts["resolved_high"],
        "resolved_medium": status_counts["resolved_medium"],
        "name_ambiguous": status_counts["name_ambiguous"],
        "query_ambiguous": status_counts["query_ambiguous"],
        "unresolved": unresolved_total,
        "invalid_canonical_ids": invalid_ids_found,
        "status_distribution": {k: v for k, v in status_counts.items()},
        "method_distribution": {k: v for k, v in method_counts.items()}
    }

    with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("VALIDATION & AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Processed:    {total_records:,}")
    print(f"Resolved (High):    {status_counts['resolved_high']:,} ({(status_counts['resolved_high']/total_records)*100:.2f}%)")
    print(f"Resolved (Medium):  {status_counts['resolved_medium']:,} ({(status_counts['resolved_medium']/total_records)*100:.2f}%)")
    print(f"Name Ambiguous:     {status_counts['name_ambiguous']:,} ({(status_counts['name_ambiguous']/total_records)*100:.2f}%)")
    print(f"Query Ambiguous:    {status_counts['query_ambiguous']:,} ({(status_counts['query_ambiguous']/total_records)*100:.2f}%)")
    print(f"Unresolved:         {unresolved_total:,} ({(unresolved_total/total_records)*100:.2f}%)")
    print(f"Invalid IDs:        {invalid_ids_found} (PASSED)")
    print(f"Audit Status:       100% Verified Consistent")
    print("=" * 80)


if __name__ == "__main__":
    main()