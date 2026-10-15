"""
MediScanAI — Phase B: Deterministic Retrieval Metrics
Implements Recall@K, Precision@K, MRR, Graph-Added Evidence Coverage,
and latency telemetry percentiles strictly conforming to evaluation/benchmark/metric_contract.md.
"""

import math
from typing import List, Set, Dict, Any, Optional


def is_relevant(grade: Optional[int], threshold: int = 2) -> bool:
    """
    Binary relevance conversion per metric contract:
    - Primary Threshold (default): grade >= 2 (Directly Relevant [3] or Relevant Supporting [2])
    - Strict Threshold: grade == 3 (Directly Relevant only)
    """
    if grade is None:
        return False
    return grade >= threshold


def deduplicate_ordered(items: List[str]) -> List[str]:
    """Preserves ranking order while deduplicating by stable identity."""
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def compute_recall_at_k(
    retrieved_ids: List[str],
    gold_relevant_ids: Set[str],
    k: int = 5,
) -> Optional[float]:
    """
    Computes Recall@K: |R_K ∩ G| / |G|.
    Returns None if |G| == 0 (unanswerable / negative control cases are ineligible for Recall@K).
    """
    if not gold_relevant_ids:
        return None

    unique_retrieved = deduplicate_ordered(retrieved_ids)[:k]
    hits = sum(1 for eid in unique_retrieved if eid in gold_relevant_ids)
    return hits / float(len(gold_relevant_ids))


def compute_precision_at_k(
    retrieved_ids: List[str],
    gold_relevant_ids: Set[str],
    k: int = 5,
) -> float:
    """
    Computes Precision@K: |R_K ∩ G| / K.
    Fewer than K unique results maintain K in the denominator per metric contract.
    """
    if k <= 0:
        return 0.0

    unique_retrieved = deduplicate_ordered(retrieved_ids)[:k]
    hits = sum(1 for eid in unique_retrieved if eid in gold_relevant_ids)
    return hits / float(k)


def compute_reciprocal_rank(
    retrieved_ids: List[str],
    gold_relevant_ids: Set[str],
    k: int = 10,
) -> Optional[float]:
    """
    Computes Reciprocal Rank (RR): 1 / rank_1 of the first relevant document in top K.
    Returns None if query has no gold relevant evidence (|G| == 0).
    Returns 0.0 if no relevant evidence is found within top K.
    """
    if not gold_relevant_ids:
        return None

    unique_retrieved = deduplicate_ordered(retrieved_ids)[:k]
    for rank_idx, eid in enumerate(unique_retrieved, 1):
        if eid in gold_relevant_ids:
            return 1.0 / float(rank_idx)
    return 0.0


def compute_false_positive_count_at_k(
    retrieved_ids: List[str],
    k: int = 5,
) -> int:
    """
    Computes False Positive Count at K for negative control / unanswerable queries: |R_K|.
    Since G(q) = empty, every retrieved candidate in top K is a false positive.
    """
    if k <= 0:
        return 0
    return len(deduplicate_ordered(retrieved_ids)[:k])


def compute_rejection_accuracy(
    retrieved_ids: List[str],
    k: int = 5,
) -> float:
    """
    Computes Zero-Retrieval / Rejection Accuracy per metric_contract.md Section 5:
    Returns 1.0 if no evidence is retrieved in top K, 0.0 otherwise.
    """
    fp_count = compute_false_positive_count_at_k(retrieved_ids, k=k)
    return 1.0 if fp_count == 0 else 0.0


def compute_graph_added_coverage(
    baseline_ids: List[str],
    graph_ids: List[str],
    gold_relevant_ids: Set[str],
    unresolved_graph_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Computes Graph-Added Evidence Coverage and redundancy metrics.
    Excludes unresolved graph evidence lacking verifiable source provenance.
    """
    unresolved = unresolved_graph_ids or set()
    valid_graph_ids = [gid for gid in graph_ids if gid not in unresolved]

    base_set = set(baseline_ids)
    graph_set = set(valid_graph_ids)

    overlap = base_set & graph_set
    new_graph_items = graph_set - base_set

    # Relevant graph-added items
    new_rel_items = new_graph_items & gold_relevant_ids if gold_relevant_ids else set()

    gold_count = len(gold_relevant_ids) if gold_relevant_ids else 0
    coverage_delta = (len(new_rel_items) / float(gold_count)) if gold_count > 0 else 0.0

    redundancy_rate = (len(overlap) / float(len(graph_set))) if graph_set else 0.0

    return {
        "baseline_count": len(base_set),
        "graph_count": len(graph_set),
        "unresolved_graph_count": len(unresolved),
        "pooled_unique_count": len(base_set | graph_set),
        "overlap_count": len(overlap),
        "graph_only_count": len(new_graph_items),
        "relevant_graph_added_count": len(new_rel_items),
        "graph_added_coverage_delta": coverage_delta,
        "graph_redundancy_rate": redundancy_rate,
    }


def compute_latency_percentiles(latencies_ms: List[int]) -> Dict[str, Any]:
    """
    Computes min, mean, p50, p95, p99 on monotonic millisecond timings.
    Uses nearest-rank interpolation. Labels tail percentiles as unstable if sample count < 20.
    """
    if not latencies_ms:
        return {
            "sample_count": 0,
            "min_ms": None,
            "max_ms": None,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "stability_note": "zero_samples",
        }

    sorted_vals = sorted(latencies_ms)
    n = len(sorted_vals)

    def percentile(p: float) -> int:
        idx = max(0, min(n - 1, math.ceil((p / 100.0) * n) - 1))
        return sorted_vals[idx]

    mean_val = round(sum(sorted_vals) / float(n), 2)
    stability = "stable_sample" if n >= 20 else "unstable_small_sample"

    return {
        "sample_count": n,
        "min_ms": sorted_vals[0],
        "max_ms": sorted_vals[-1],
        "mean_ms": mean_val,
        "p50_ms": percentile(50),
        "p95_ms": percentile(95),
        "p99_ms": percentile(99),
        "stability_note": stability,
    }
