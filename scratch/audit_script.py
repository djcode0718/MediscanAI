import json
import csv
from pathlib import Path
from collections import defaultdict
import numpy as np

run_dir = Path("evaluation/results/eval_evidence_verified_both_20261015_102208")
with open(run_dir / "summary.json") as f:
    reported_summary = json.load(f)

with open(run_dir / "per_case_results.jsonl") as f:
    cases = [json.loads(line) for line in f]

with open("evaluation/benchmark/evidence_adjudication/phase_a_3/evidence_verified_judgments.jsonl") as f:
    evidence_records = [json.loads(line) for line in f]

with open("evaluation/benchmark/candidate_queries.jsonl") as f:
    queries = {q["case_id"]: q for q in (json.loads(line) for line in f)}

print("Loaded files successfully.")
print(f"Total cases: {len(cases)}, Total evidence records: {len(evidence_records)}, Total queries: {len(queries)}")

# Group evidence by case
gold_by_case = defaultdict(dict)
for r in evidence_records:
    cid = r["case_id"]
    eid = r["evidence_id"]
    grade = r["evidence_based_grade"]
    status = r["judgment_status"]
    gold_by_case[cid][eid] = {
        "grade": grade,
        "is_relevant": grade >= 2 and eid != "none",
        "status": status,
        "preliminary_grade": r.get("preliminary_grade"),
    }

discrepancies = []

recomputed_recalls = []
recomputed_precisions = []
recomputed_mrrs = []
recomputed_cov_deltas = []
recomputed_rej_accs = []
recomputed_fps = []

case_audits = []

base_latencies = []
graph_latencies = []
total_latencies = []

cases_with_graph_added_rel = []

for c in cases:
    cid = c["case_id"]
    q_info = queries[cid]
    expected_types = q_info.get("expected_evidence_types", [])
    cat = c["query_category"]
    
    # Check gold
    c_gold = gold_by_case[cid]
    rel_gold_ids = {eid for eid, g in c_gold.items() if g["is_relevant"]}
    all_gold_ids = set(c_gold.keys())
    
    # Check eligibility
    is_neg_ctrl = (cat == "insufficient_evidence_unanswerable" and expected_types == ["none"])
    if len(rel_gold_ids) > 0:
        expected_elig = "eligible_evidence_verified"
    elif is_neg_ctrl:
        expected_elig = "eligible_negative_control"
    else:
        expected_elig = "excluded_no_relevant_gold_evidence"
        
    reported_elig = c["metrics"]["eligibility"]
    if reported_elig != expected_elig:
        discrepancies.append({
            "case_id": cid, "field": "eligibility",
            "reported": reported_elig, "recomputed": expected_elig
        })
        
    # Latencies
    total_latencies.append(c["total_latency_ms"])
    if c["baseline_latency_ms"] > 0:
        base_latencies.append(c["baseline_latency_ms"])
    if c["graph_latency_ms"] > 0:
        graph_latencies.append(c["graph_latency_ms"])

    # Retrieved items
    b_items = [it for it in c["retrieved_items"] if it["channel"] == "baseline"]
    g_items = [it for it in c["retrieved_items"] if it["channel"] == "graph"]
    
    b_ids = [it["evidence_id"] for it in b_items]
    g_ids = [it["evidence_id"] for it in g_items]
    
    # Check counts
    if len(b_ids) != c["baseline_count"]:
        discrepancies.append({"case_id": cid, "field": "baseline_count", "reported": c["baseline_count"], "recomputed": len(b_ids)})
    if len(g_ids) != c["graph_count"]:
        discrepancies.append({"case_id": cid, "field": "graph_count", "reported": c["graph_count"], "recomputed": len(g_ids)})
        
    overlap = set(b_ids) & set(g_ids)
    if len(overlap) != c["overlap_count"]:
        discrepancies.append({"case_id": cid, "field": "overlap_count", "reported": c["overlap_count"], "recomputed": len(overlap)})
        
    pooled_ids = list(dict.fromkeys(b_ids + g_ids))
    if len(pooled_ids) != c["pooled_count"]:
        discrepancies.append({"case_id": cid, "field": "pooled_count", "reported": c["pooled_count"], "recomputed": len(pooled_ids)})

    # Metrics
    if expected_elig == "eligible_evidence_verified":
        # Hits
        b_hits = [eid for eid in b_ids if eid in rel_gold_ids]
        rec = len(b_hits) / len(rel_gold_ids)
        prec = len(b_hits) / 5.0
        
        mrr = 0.0
        for rank, eid in enumerate(b_ids, 1):
            if eid in rel_gold_ids:
                mrr = 1.0 / rank
                break
                
        # Graph added coverage
        g_hits = [eid for eid in g_ids if eid in rel_gold_ids]
        g_added = [eid for eid in g_hits if eid not in set(b_ids)]
        cov_delta = len(g_added) / len(rel_gold_ids)
        
        if len(g_added) > 0:
            cases_with_graph_added_rel.append({
                "case_id": cid,
                "query": c["query"],
                "g_added": g_added,
                "cov_delta": cov_delta,
                "gold_rel_count": len(rel_gold_ids)
            })

        recomputed_recalls.append(rec)
        recomputed_precisions.append(prec)
        recomputed_mrrs.append(mrr)
        recomputed_cov_deltas.append(cov_delta)
        
        rep_rec = c["metrics"]["recall_at_k"]
        rep_prec = c["metrics"]["precision_at_k"]
        rep_mrr = c["metrics"]["baseline_mrr"]
        rep_cov = c["metrics"]["graph_added_coverage"]["graph_added_coverage_delta"]
        
        if abs(rec - rep_rec) > 1e-4:
            discrepancies.append({"case_id": cid, "field": "recall_at_k", "reported": rep_rec, "recomputed": rec})
        if abs(prec - rep_prec) > 1e-4:
            discrepancies.append({"case_id": cid, "field": "precision_at_k", "reported": rep_prec, "recomputed": prec})
        if abs(mrr - rep_mrr) > 1e-4:
            discrepancies.append({"case_id": cid, "field": "baseline_mrr", "reported": rep_mrr, "recomputed": mrr})
        if abs(cov_delta - rep_cov) > 1e-4:
            discrepancies.append({"case_id": cid, "field": "graph_added_coverage_delta", "reported": rep_cov, "recomputed": cov_delta})

    elif expected_elig == "eligible_negative_control":
        rej_acc = 1.0 if len(b_ids) == 0 else 0.0
        fp = len(b_ids)
        recomputed_rej_accs.append(rej_acc)
        recomputed_fps.append(fp)
        
        rep_rej = c["metrics"]["rejection_accuracy"]
        rep_fp = c["metrics"]["false_positive_count_at_k"]
        if abs(rej_acc - rep_rej) > 1e-4:
            discrepancies.append({"case_id": cid, "field": "rejection_accuracy", "reported": rep_rej, "recomputed": rej_acc})
        if abs(fp - rep_fp) > 1e-4:
            discrepancies.append({"case_id": cid, "field": "false_positive_count_at_k", "reported": rep_fp, "recomputed": fp})

print(f"Total case discrepancies: {len(discrepancies)}")
print(f"Cases with graph added relevant evidence: {len(cases_with_graph_added_rel)}")
for item in cases_with_graph_added_rel:
    print(f"  {item['case_id']}: {item['query']} -> added {item['g_added']}, delta={item['cov_delta']}")

print(f"Mean recomputed Recall@5: {np.mean(recomputed_recalls):.4f} (reported: {reported_summary['macro_metrics']['macro_recall_at_5']})")
print(f"Mean recomputed Precision@5: {np.mean(recomputed_precisions):.4f} (reported: {reported_summary['macro_metrics']['macro_precision_at_5']})")
print(f"Mean recomputed Baseline MRR: {np.mean(recomputed_mrrs):.4f} (reported: {reported_summary['macro_metrics']['macro_baseline_mrr']})")
print(f"Mean recomputed Cov Delta (across 45 cases): {np.mean(recomputed_cov_deltas):.4f} (reported in analysis: 0.1000)")
sum_cov_deltas = sum(recomputed_cov_deltas)
print(f"Sum of Cov Deltas across 45 cases: {sum_cov_deltas:.4f} -> 4.5 / 45 = {sum_cov_deltas/45:.4f}")
