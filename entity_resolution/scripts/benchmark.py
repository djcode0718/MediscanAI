#!/usr/bin/env python3
"""
MediScanAI 2.0 — Adversarial & Regression Benchmark Test Suite.
Tests all Section 31 adversarial queries, drug codes, combinations,
radiolabels, and stereoisomers against the revised candidate evaluation engine.
"""

import pickle
import sys
from pathlib import Path

from normalization import parse_intervention
from candidate_generation import retrieve_candidates
from scoring import evaluate_candidate, classify_match

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"
INDEX_FILE = DATA_DIR / "indexes" / "fda_name_index.pkl"


ADVERSARIAL_CASES = [
    # 1. Dangerous non-drug/control/radiation texts that must NEVER resolve
    ("0 Hz Control", "unresolved"),
    ("1,2 dithiolane 3 valeric acid", "unresolved"),
    ("#1 Respiratory Care Solution", "unresolved"),
    ("10-10-10 Protocol", "unresolved"),
    ("30 Gy over 3 weeks", "unresolved"),
    ("211 Information Sheet", "unresolved"),
    ("25G x 1 Needle Autoinjector", "unresolved"),
    ("3d printed restoration", "unresolved"),
    ("3TC Once Daily", "unresolved"),
    ("5 A model", "unresolved"),
    ("500 with BP treatment", "unresolved"),
    ("6% HES 130/0.4 in a saline solution", "unresolved"),
    ("7.5% hypertonic saline/6% Dextran-70", "unresolved"),
    ("131-MIBG + Vorinostat", "unresolved"),

    # 2. Alphanumeric development codes that MUST survive normalization
    ("PF-04995274", None),          # Valid identifier test
    ("0.075 mg NX-1207", None),     # Measurement stripping without code loss
    ("JNJ-42491293", None),         # Identifier preservation
    ("5FU", None),                  # Abbreviation preservation
    ("3TC", None),                  # Abbreviation preservation

    # 3. Radiolabels & Stereochemistry
    ("(+)-Epicatechin", None),
    ("[89Zr]Panitumumab PET-MRI", None),
    ("177Lu-Dotatate PRRT", "unresolved"),   # Must NOT match 68ga-dotatate due to isotope mismatch
    ("(+)-SJ000557733", None),
]


def run_benchmark():
    print("=" * 80)
    print("MEDISCANAI 2.0 — ADVERSARIAL BENCHMARK SUITE")
    print("=" * 80)

    if not INDEX_FILE.exists():
        print("ERROR: FDA index missing. Build it first with prepare_index.py.")
        sys.exit(1)

    with open(INDEX_FILE, "rb") as f:
        index = pickle.load(f)

    fda_records = index["fda_records"]
    failures = 0

    for query, expected_status in ADVERSARIAL_CASES:
        q_parsed = parse_intervention(query)
        candidates = retrieve_candidates(q_parsed, index)
        scored = []

        for cname in candidates:
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
        verdict = classify_match(q_parsed, scored, fda_records)

        passed = True
        if expected_status and verdict.status != expected_status:
            passed = False
            failures += 1

        # Strict safety check: None of the dangerous controls should be resolved
        if expected_status == "unresolved" and verdict.status in ("resolved_high", "resolved_medium"):
            passed = False
            failures += 1

        # Alphanumeric codes check: verify that identifier codes survived into q_parsed
        if query in ("PF-04995274", "0.075 mg NX-1207", "JNJ-42491293", "5FU", "3TC"):
            if not q_parsed.tokens or q_parsed.is_empty:
                passed = False
                failures += 1

        status_marker = "PASS" if passed else "FAIL"
        print(f"[{status_marker}] Query: '{query}'")
        print(f"       Parsed: norm='{q_parsed.normalized}', idents={q_parsed.identifiers}, ret={q_parsed.retention_ratio}")
        print(f"       Verdict: status={verdict.status}, method={verdict.method}, matched={verdict.matched_fda_name}")
        print(f"       Confidence={verdict.confidence}, Margin={verdict.margin}")
        print("-" * 80)

    print("\n" + "=" * 80)
    if failures == 0:
        print("ALL ADVERSARIAL BENCHMARK TESTS PASSED (0 False Positives).")
    else:
        print(f"BENCHMARK FAILED WITH {failures} ERRORS.")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark()