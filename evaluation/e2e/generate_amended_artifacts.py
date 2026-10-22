#!/usr/bin/env python3
"""
MediScanAI Audit Amendment (Steps 5b, 5c, 5d).
1. Auto-classifies 86 unsupported A2 statements into taxonomy_auto.csv.
2. Samples 20 stratified non-abstention claims for human_check_20.csv.
3. Performs exact two-sided binomial sign-tests and bootstrap 95% CIs.
"""

import re
import csv
import json
import random
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from rapidfuzz import fuzz

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "evaluation/e2e/results"


def extract_drug_names_from_contexts(contexts):
    names = []
    for ctx in contexts:
        for pat in [
            r"Brand:\s*([^|]+)",
            r"Generic:\s*([^|]+)",
            r"Active ingredients:\s*([^|]+)",
            r"name:\s*([^|]+)",
            r"Also marketed as:\s*([^|]+)",
        ]:
            m = re.search(pat, ctx)
            if m:
                val = m.group(1).strip()
                for sub in val.split(";"):
                    if sub.strip():
                        names.append(sub.strip())
    return names


def step_5b_auto_classify():
    print("--- STEP 5b: Auto-classify A2 Unsupported Statements ---")
    with open(RESULTS_DIR / "A2/generated_cases.jsonl") as f:
        cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(RESULTS_DIR / "A2/unsupported_statements.jsonl") as f:
        unsupp = [json.loads(line) for line in f if line.strip()]

    re_abstention = re.compile(r"(not stated|not sufficient|could not be identified|not explicitly)", re.IGNORECASE)
    re_template = re.compile(r"label evidence for (.*?) lists uses that match your symptoms", re.IGNORECASE)
    junk_keywords = ["wipe", "wipes", "sunscreen", "creme", "cream", "kit", "survivalist", "moisturizer", "soap"]

    classified = []
    examples = defaultdict(list)

    for u in unsupp:
        cid = u["case_id"]
        stmt = u["statement"]
        case = cases[cid]
        shown_drugs = extract_drug_names_from_contexts(case.get("retrieved_contexts", []))
        label = None

        # 1. ABSTENTION
        if re_abstention.search(stmt):
            label = "ABSTENTION"

        # 2. DISEASE_NAME_AS_SYMPTOM
        if not label:
            m_cond = re.match(r"^([A-Za-z\s\-]+?)\s+(?:lists|includes|also includes)\s+(.*)$", stmt, re.IGNORECASE)
            if m_cond:
                cname = m_cond.group(1).strip().lower()
                rest = m_cond.group(2).lower()
                if cname in rest and len(cname) > 3:
                    label = "DISEASE_NAME_AS_SYMPTOM"

        # 3. JUNK_DRUG
        if not label:
            if any(j in stmt.lower() for j in junk_keywords):
                label = "JUNK_DRUG"

        # 4. TEMPLATE_VERDICT or ENTITY_NOT_IN_EVIDENCE
        if not label:
            m_t = re_template.search(stmt)
            if m_t:
                dname = m_t.group(1).strip()
                max_fuzz = max([fuzz.token_set_ratio(dname.lower(), d.lower()) for d in shown_drugs], default=0)
                if max_fuzz >= 85:
                    label = "TEMPLATE_VERDICT"
                else:
                    label = "ENTITY_NOT_IN_EVIDENCE"

        # 5. ENTITY_NOT_IN_EVIDENCE fallback
        if not label:
            unanswerable_drugs = ["glycozempra", "valerionex", "xanthroflurane", "novaproxin", "nonexistentdrugz", "glibenclarnide", "atzumi"]
            if any(ud in stmt.lower() for ud in unanswerable_drugs):
                label = "ENTITY_NOT_IN_EVIDENCE"

        # 6. Fallback
        if not label:
            label = "OTHER"

        classified.append({"case_id": cid, "statement": stmt, "label": label, "reason": u.get("reason", "")})
        examples[label].append(stmt)

    # Save to taxonomy_auto.csv
    out_csv = RESULTS_DIR / "A2/taxonomy_auto.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "statement", "assigned_label", "judge_reason"])
        for c in classified:
            writer.writerow([c["case_id"], c["statement"], c["label"], c["reason"]])

    print(f"✅ Written {len(classified)} classified rows to {out_csv}")
    return classified, examples


def step_5c_human_check():
    print("--- STEP 5c: Human Check File Generation ---")
    with open(RESULTS_DIR / "free_metrics_summary.json") as f:
        free = json.load(f)
    with open(RESULTS_DIR / "A2/generated_cases.jsonl") as f:
        cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(RESULTS_DIR / "A2/unsupported_statements.jsonl") as f:
        unsupp_stmts = {u["statement"].strip(): u for u in [json.loads(line) for line in f if line.strip()]}

    hhem_a2 = dict(zip([json.loads(line)["case_id"] for line in open(RESULTS_DIR / "A2/generated_cases.jsonl")], free["results"]["A2"]["hhem_raw"]))
    re_abstention = re.compile(r"(not stated|not sufficient|could not be identified|not explicitly|not applicable)", re.IGNORECASE)

    candidate_claims = defaultdict(list)
    for cid, case in cases.items():
        cat = case["category"]
        raw_out = case.get("raw_llm_output", "")
        contexts = case.get("retrieved_contexts", [])

        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", raw_out) if s.strip()]
        for s in sents:
            if s.startswith("#") or s.startswith("**Verdict:"):
                m_q = re.search(r"\"([^\"]+)\"", s)
                if m_q:
                    claim_text = m_q.group(1).strip()
                else:
                    continue
            else:
                claim_text = s

            if re_abstention.search(claim_text) or len(claim_text.split()) < 4:
                continue

            tags = re.findall(r"\[E\d+\]", claim_text)
            cited_blocks = []
            for t in tags:
                for ctx in contexts:
                    if ctx.startswith(t):
                        cited_blocks.append(ctx)

            is_unsupp = any(u in claim_text or claim_text in u for u in unsupp_stmts)
            judge_verdict = 0 if is_unsupp else 1

            candidate_claims[cat].append({
                "case_id": cid,
                "claim_text": claim_text,
                "cited_blocks": "\n".join(cited_blocks) if cited_blocks else "None cited",
                "judge_verdict": judge_verdict,
                "hhem_v2_score": hhem_a2.get(cid, 0.0),
            })

    target_sample = {
        "symptom_only": 4,
        "medicine_only_clean_ocr": 3,
        "medicine_only_noisy_ocr": 3,
        "symptom_plus_medicine_match": 4,
        "symptom_plus_medicine_mismatch": 3,
        "unanswerable": 3,
    }

    rng = random.Random(42)
    sampled_20 = []
    for cat in sorted(candidate_claims.keys()):
        clist = candidate_claims[cat]
        k = target_sample.get(cat, 3)
        clist_sorted = sorted(clist, key=lambda x: (x["case_id"], x["claim_text"]))
        chosen = rng.sample(clist_sorted, min(k, len(clist_sorted)))
        sampled_20.extend(chosen)

    out_csv = RESULTS_DIR / "A2/human_check_20.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "claim_text", "cited_evidence_blocks", "judge_verdict", "hhem_v2_score", "human_supported (1/0)", "note"])
        for s in sampled_20:
            val = s["hhem_v2_score"]
            writer.writerow([
                s["case_id"],
                s["claim_text"],
                s["cited_blocks"],
                s["judge_verdict"],
                f"{val:.4f}",
                "",
                "",
            ])

    print(f"✅ Written 20 sampled claims to {out_csv}")
    return sampled_20


def step_5d_sign_tests():
    print("--- STEP 5d: Sign Test Honesty Check ---")
    with open(RESULTS_DIR / "R0s/scored_results.jsonl") as f:
        r0s = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(RESULTS_DIR / "A1/scored_results.jsonl") as f:
        a1 = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(RESULTS_DIR / "A2/scored_results.jsonl") as f:
        a2 = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    # A1 vs R0s-15
    diffs_1 = []
    for cid, r_r0 in r0s.items():
        f0 = r_r0["judge_faithfulness"]
        f1 = a1[cid]["judge_faithfulness"]
        if pd.notna(f0) and pd.notna(f1):
            diffs_1.append(f1 - f0)
    diffs_1 = np.array(diffs_1)
    wins_1 = int(np.sum(diffs_1 > 0))
    losses_1 = int(np.sum(diffs_1 < 0))
    ties_1 = int(np.sum(diffs_1 == 0))
    n_eff_1 = wins_1 + losses_1
    p_val_1 = binomtest(wins_1, n_eff_1, p=0.5, alternative="two-sided").pvalue if n_eff_1 > 0 else 1.0

    rng = np.random.RandomState(42)
    boot_1 = [np.mean(rng.choice(diffs_1, size=len(diffs_1), replace=True)) for _ in range(10000)]
    ci_1 = (np.percentile(boot_1, 2.5), np.percentile(boot_1, 97.5))

    # A2 vs A1
    diffs_2 = []
    for cid, r_a1 in a1.items():
        f1 = r_a1["judge_faithfulness"]
        f2 = a2[cid]["judge_faithfulness"]
        if pd.notna(f1) and pd.notna(f2):
            diffs_2.append(f2 - f1)
    diffs_2 = np.array(diffs_2)
    wins_2 = int(np.sum(diffs_2 > 0))
    losses_2 = int(np.sum(diffs_2 < 0))
    ties_2 = int(np.sum(diffs_2 == 0))
    n_eff_2 = wins_2 + losses_2
    p_val_2 = binomtest(wins_2, n_eff_2, p=0.5, alternative="two-sided").pvalue if n_eff_2 > 0 else 1.0

    boot_2 = [np.mean(rng.choice(diffs_2, size=len(diffs_2), replace=True)) for _ in range(10000)]
    ci_2 = (np.percentile(boot_2, 2.5), np.percentile(boot_2, 97.5))

    return {
        "a1_vs_r0": {
            "n": len(diffs_1),
            "wins": wins_1,
            "losses": losses_1,
            "ties": ties_1,
            "mean_diff": float(np.mean(diffs_1)),
            "p_val": float(p_val_1),
            "ci_95": [float(ci_1[0]), float(ci_1[1])],
            "significant": bool((ci_1[0] > 0 or ci_1[1] < 0) and p_val_1 < 0.05),
        },
        "a2_vs_a1": {
            "n": len(diffs_2),
            "wins": wins_2,
            "losses": losses_2,
            "ties": ties_2,
            "mean_diff": float(np.mean(diffs_2)),
            "p_val": float(p_val_2),
            "ci_95": [float(ci_2[0]), float(ci_2[1])],
            "significant": bool((ci_2[0] > 0 or ci_2[1] < 0) and p_val_2 < 0.05),
        }
    }


def main():
    classified, examples = step_5b_auto_classify()
    sampled_20 = step_5c_human_check()
    sign_stats = step_5d_sign_tests()
    print("Sign test stats:", sign_stats)


if __name__ == "__main__":
    main()
