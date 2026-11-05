"""Case-Clustered Bootstrap and Paired Statistical Protocol (Revision 2.4)."""

import math
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

def compute_binary_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """Computes binary classification metrics from 0/1 vectors."""
    assert len(y_true) == len(y_pred)
    n = len(y_true)
    if n == 0:
        return {}

    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    overall_agreement = (tp + tn) / n
    pos_agreement = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    neg_agreement = tn / (tn + fp) if (tn + fp) > 0 else float("nan")
    neg_precision = tn / (tn + fn) if (tn + fn) > 0 else float("nan")
    pos_precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    fnr = fn / (tp + fn) if (tp + fn) > 0 else float("nan")
    fpr = fp / (tn + fp) if (tn + fp) > 0 else float("nan")

    balanced_acc = (
        0.5 * (pos_agreement + neg_agreement)
        if not math.isnan(pos_agreement) and not math.isnan(neg_agreement)
        else float("nan")
    )

    f1_pos = (
        2 * tp / (2 * tp + fp + fn)
        if (2 * tp + fp + fn) > 0
        else float("nan")
    )
    f1_neg = (
        2 * tn / (2 * tn + fp + fn)
        if (2 * tn + fp + fn) > 0
        else float("nan")
    )
    macro_f1 = (
        0.5 * (f1_pos + f1_neg)
        if not math.isnan(f1_pos) and not math.isnan(f1_neg)
        else float("nan")
    )

    return {
        "n": n,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "overall_agreement": overall_agreement,
        "pos_agreement": pos_agreement,
        "neg_agreement": neg_agreement,
        "neg_precision": neg_precision,
        "pos_precision": pos_precision,
        "fnr": fnr,
        "fpr": fpr,
        "balanced_accuracy": balanced_acc,
        "macro_f1": macro_f1
    }


def mcnemar_test(y_true: List[int], y_ctrl: List[int], y_interv: List[int]) -> Dict[str, Any]:
    """Computes McNemar test for paired binary classifier comparison with continuity correction."""
    assert len(y_true) == len(y_ctrl) == len(y_interv)

    # b: control correct, interv incorrect (regression)
    # c: control incorrect, interv correct (improvement)
    b = 0
    c = 0
    both_correct = 0
    both_incorrect = 0

    for t, ctrl, interv in zip(y_true, y_ctrl, y_interv):
        ctrl_corr = (ctrl == t)
        interv_corr = (interv == t)
        if ctrl_corr and not interv_corr:
            b += 1
        elif not ctrl_corr and interv_corr:
            c += 1
        elif ctrl_corr and interv_corr:
            both_correct += 1
        else:
            both_incorrect += 1

    total_discordant = b + c
    if total_discordant == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "b_regressions": 0,
            "c_improvements": 0,
            "both_correct": both_correct,
            "both_incorrect": both_incorrect,
            "note": "Zero discordant pairs"
        }

    # Edwards continuity-corrected McNemar statistic
    stat = (abs(b - c) - 1.0) ** 2 / total_discordant if abs(b - c) > 0 else 0.0
    
    # 1-df chi-square p-value via survival function
    # using approximation: p = 2 * (1 - NormalCDF(sqrt(stat)))
    z = math.sqrt(stat)
    p_value = math.erfc(z / math.sqrt(2.0))

    return {
        "statistic": round(stat, 4),
        "p_value": round(p_value, 5),
        "b_regressions": b,
        "c_improvements": c,
        "both_correct": both_correct,
        "both_incorrect": both_incorrect
    }


def case_clustered_bootstrap(
    case_statement_pairs: List[Dict[str, Any]],
    n_bootstraps: int = 10000,
    seed: int = 42
) -> Dict[str, Any]:
    """Executes case-clustered bootstrap resampling with replacement at the case level."""
    rng = np.random.RandomState(seed)

    # Group statements by case_id
    case_map: Dict[str, List[Dict[str, Any]]] = {}
    for item in case_statement_pairs:
        cid = item["case_id"]
        case_map.setdefault(cid, []).append(item)

    unique_cases = sorted(list(case_map.keys()))
    m = len(unique_cases)
    if m == 0:
        return {}

    metric_samples: Dict[str, List[float]] = {
        "overall_agreement": [],
        "pos_agreement": [],
        "neg_agreement": [],
        "neg_precision": [],
        "pos_precision": [],
        "fnr": [],
        "fpr": [],
        "balanced_accuracy": [],
        "macro_f1": []
    }
    sparse_replicates = 0

    for _ in range(n_bootstraps):
        # Sample cases with replacement
        sampled_indices = rng.choice(m, size=m, replace=True)
        sample_items = []
        for idx in sampled_indices:
            cid = unique_cases[idx]
            sample_items.extend(case_map[cid])

        y_true = [item["human_label"] for item in sample_items]
        y_pred = [item["judge_verdict"] for item in sample_items]

        m_dict = compute_binary_metrics(y_true, y_pred)
        if any(math.isnan(v) for v in m_dict.values()):
            sparse_replicates += 1

        for k in metric_samples:
            val = m_dict.get(k, float("nan"))
            if not math.isnan(val):
                metric_samples[k].append(val)

    # Compute percentiles
    results = {
        "n_cases": m,
        "n_statements": len(case_statement_pairs),
        "n_replicates": n_bootstraps,
        "sparse_replicates": sparse_replicates,
        "metrics": {}
    }

    for k, samples in metric_samples.items():
        if len(samples) > 0:
            results["metrics"][k] = {
                "mean": round(float(np.mean(samples)), 4),
                "ci_lower": round(float(np.percentile(samples, 2.5)), 4),
                "ci_upper": round(float(np.percentile(samples, 97.5)), 4),
                "valid_replicates": len(samples)
            }
        else:
            results["metrics"][k] = {
                "mean": float("nan"),
                "ci_lower": float("nan"),
                "ci_upper": float("nan"),
                "valid_replicates": 0,
                "note": "unstable_sparse_class"
            }

    return results


def holm_bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[Dict[str, Any]]:
    """Applies Holm-Bonferroni step-down correction to a family of p-values."""
    m = len(p_values)
    indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])
    
    results = [None] * m
    reject = True

    for rank, (orig_idx, p) in enumerate(indexed_p):
        k = rank + 1
        threshold = alpha / (m - k + 1)
        if reject and p <= threshold:
            sig = True
        else:
            sig = False
            reject = False  # Step-down stops

        results[orig_idx] = {
            "rank": k,
            "original_p": p,
            "adjusted_threshold": round(threshold, 6),
            "is_significant": sig
        }

    return results
