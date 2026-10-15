import json
import csv
from pathlib import Path
from collections import defaultdict

run_dir = Path("evaluation/results/eval_evidence_verified_both_20261015_102208")
analysis_dir = run_dir / "analysis"
analysis_dir.mkdir(parents=True, exist_ok=True)

# 1. Load summary.json and per_case_results.jsonl
summary = json.loads((run_dir / "summary.json").read_text())
with open(run_dir / "per_case_results.jsonl") as f:
    cases = [json.loads(line) for line in f]

# Load benchmark queries to get expected_evidence_types and candidate_gold_evidence_ids
with open("evaluation/benchmark/candidate_queries.jsonl") as f:
    canon_queries = {q["case_id"]: q for q in (json.loads(l) for l in f)}

# Load Phase A.3 evidence-verified judgments
with open("evaluation/benchmark/evidence_adjudication/phase_a_3/evidence_verified_judgments.jsonl") as f:
    evidence_records = [json.loads(l) for l in f]

judgments_by_case = defaultdict(dict)
for r in evidence_records:
    judgments_by_case[r["case_id"]][r["evidence_id"]] = r

# 2. Compile Case-Level Comparison
case_rows = []
category_stats = defaultdict(lambda: {
    "count": 0, "recall": [], "precision": [], "baseline_mrr": [],
    "graph_added_cov": [], "overlap": [], "base_lat": [], "graph_lat": []
})

total_baseline_rel_hits = 0
total_graph_rel_hits = 0
total_gold_rel_items = 0

for c in cases:
    cid = c["case_id"]
    query = c["query"]
    cat = c["query_category"]
    metrics = c["metrics"]
    elig = metrics.get("eligibility")
    
    # Gold relevant items for this case
    case_judg = judgments_by_case.get(cid, {})
    gold_rel = [eid for eid, j in case_judg.items() if j.get("evidence_based_grade", 0) >= 2 and eid != "none"]
    gold_all = list(case_judg.keys())
    
    # Baseline hits
    b_items = [it for it in c.get("retrieved_items", []) if it["channel"] == "baseline"]
    b_ids = [it["evidence_id"] for it in b_items]
    b_rel_hits = [eid for eid in b_ids if eid in gold_rel]
    
    # Graph hits
    g_items = [it for it in c.get("retrieved_items", []) if it["channel"] == "graph"]
    g_ids = [it["evidence_id"] for it in g_items]
    g_rel_hits = [eid for eid in g_ids if eid in gold_rel]
    
    g_cov = metrics.get("graph_added_coverage") or {}
    rel_graph_added = g_cov.get("relevant_graph_added_count", 0)
    cov_delta = g_cov.get("graph_added_coverage_delta")
    
    recall = metrics.get("recall_at_k")
    precision = metrics.get("precision_at_k")
    mrr = metrics.get("baseline_mrr")
    fp_count = metrics.get("false_positive_count_at_k")
    rej_acc = metrics.get("rejection_accuracy")
    
    # Category aggregation for eligible cases
    if elig == "eligible_evidence_verified":
        category_stats[cat]["count"] += 1
        if recall is not None: category_stats[cat]["recall"].append(recall)
        if precision is not None: category_stats[cat]["precision"].append(precision)
        if mrr is not None: category_stats[cat]["baseline_mrr"].append(mrr)
        if cov_delta is not None: category_stats[cat]["graph_added_cov"].append(cov_delta)
        category_stats[cat]["overlap"].append(c["overlap_count"])
        category_stats[cat]["base_lat"].append(c["baseline_latency_ms"])
        if c["graph_latency_ms"] > 0:
            category_stats[cat]["graph_lat"].append(c["graph_latency_ms"])
            
        total_baseline_rel_hits += len(b_rel_hits)
        total_graph_rel_hits += len(g_rel_hits)
        total_gold_rel_items += len(gold_rel)
    elif elig == "eligible_negative_control":
        category_stats[cat]["count"] += 1
        category_stats[cat]["base_lat"].append(c["baseline_latency_ms"])
        if c["graph_latency_ms"] > 0:
            category_stats[cat]["graph_lat"].append(c["graph_latency_ms"])

    # Interpretation
    notes = []
    if elig == "eligible_negative_control":
        notes.append(f"Negative Control: Baseline FP={fp_count}, Graph returned {len(g_ids)} items (Rejection Acc={rej_acc})")
    elif elig == "excluded_no_relevant_gold_evidence":
        notes.append("No relevant gold evidence (all candidates downgraded/irrelevant)")
    else:
        if rel_graph_added > 0:
            notes.append(f"Graph added {rel_graph_added} new relevant items (Coverage delta +{cov_delta:.2f})")
        if c["overlap_count"] > 0:
            notes.append(f"Channel overlap: {c['overlap_count']} items")
        if c["graph_count"] == 0:
            notes.append("Graph returned 0 results (unmatched query syntax/intent)")
        if not notes:
            notes.append(f"Baseline Recall={recall:.2f}, Graph Only={c['graph_only_count']} items (0 relevant added)")

    case_rows.append({
        "case_id": cid,
        "query": query,
        "query_category": cat,
        "eligibility": elig,
        "gold_relevant_evidence_ids": ";".join(gold_rel) if gold_rel else "none",
        "baseline_retrieved_count": c["baseline_count"],
        "graph_retrieved_count": c["graph_count"],
        "pooled_unique_count": c["pooled_count"],
        "overlap_count": c["overlap_count"],
        "graph_only_count": c["graph_only_count"],
        "baseline_relevant_hits": ";".join(b_rel_hits) if b_rel_hits else "none",
        "graph_relevant_hits": ";".join(g_rel_hits) if g_rel_hits else "none",
        "relevant_graph_added_count": rel_graph_added,
        "recall_at_5": f"{recall:.4f}" if recall is not None else "N/A",
        "precision_at_5": f"{precision:.4f}" if precision is not None else "N/A",
        "baseline_mrr": f"{mrr:.4f}" if mrr is not None else "N/A",
        "graph_mrr": "N/A (unranked)",
        "pooled_mrr": "N/A (prohibited)",
        "graph_added_coverage_delta": f"{cov_delta:.4f}" if cov_delta is not None else "N/A",
        "rejection_accuracy": f"{rej_acc:.4f}" if rej_acc is not None else "N/A",
        "false_positive_count_at_5": str(fp_count) if fp_count is not None else "N/A",
        "baseline_latency_ms": c["baseline_latency_ms"],
        "graph_latency_ms": c["graph_latency_ms"],
        "total_latency_ms": c["total_latency_ms"],
        "interpretation": " | ".join(notes)
    })

# Write case_level_comparison.csv
csv_path = analysis_dir / "case_level_comparison.csv"
fieldnames = list(case_rows[0].keys())
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(case_rows)

print(f"Wrote {len(case_rows)} rows to {csv_path}")
