"""
MediScanAI Dynamic Evaluation Reporting (Phase 2).

All reports are strictly derived from raw scored JSONL, verdicts, and manifest.json.
Zero hard-coded metric values, commit SHAs, or test attestations.

Requirements:
  1. Recomputes n_valid, mean, median, unsupported counts from data.
  2. Paired analysis strictly on the INTERSECTION of valid cases.
  3. Explicitly prints excluded cases and reasons.
  4. Bootstrap 95% CI on paired differences (10,000 resamples, fixed seed=42).
  5. Verdict logic:
     - INCONCLUSIVE if invalid rate > 3% or paired intersection coverage < 90%.
     - Never a recommendation from mean alone.
  6. Verification report obtains git status dynamically and runs pytest (or outputs 'not run').
"""

import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def is_valid_score(val: Any) -> bool:
    """Check if score is numeric and non-NaN."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return not math.isnan(val)
    return False


def load_scored_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load scored results records from JSONL."""
    records = []
    p = Path(file_path)
    if not p.is_file():
        return records
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                try:
                    records.append(json.loads(line_str))
                except Exception:
                    pass
    return records


def load_unsupported_statements(file_path: Optional[Path]) -> List[Dict[str, Any]]:
    """Load unsupported statements from JSONL."""
    if not file_path:
        return []
    p = Path(file_path)
    if not p.is_file():
        return []
    items = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                try:
                    items.append(json.loads(line_str))
                except Exception:
                    pass
    return items


def compute_dataset_stats(
    records: List[Dict[str, Any]],
    unsupported_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute dataset-level faithfulness statistics strictly from records."""
    total_count = len(records)
    valid_records = []
    invalid_records = []

    for r in records:
        f = r.get("judge_faithfulness")
        st = r.get("eval_status")
        # Valid if status is valid or if numeric non-NaN score present without failure status
        if st == "valid" or (st is None and is_valid_score(f)):
            valid_records.append(r)
        else:
            invalid_records.append(r)

    valid_scores = [float(r["judge_faithfulness"]) for r in valid_records if is_valid_score(r.get("judge_faithfulness"))]

    mean_val = float(np.mean(valid_scores)) if valid_scores else 0.0
    median_val = float(np.median(valid_scores)) if valid_scores else 0.0
    p10_val = float(np.percentile(valid_scores, 10)) if valid_scores else 0.0

    n_valid = len(valid_scores)
    n_invalid = total_count - n_valid
    invalid_rate = (n_invalid / total_count) if total_count > 0 else 0.0

    # Unsupported count: either from provided list or aggregated from records
    if unsupported_items is not None:
        unsupported_count = len(unsupported_items)
    else:
        unsupported_count = 0
        for r in records:
            unsupp = r.get("unsupported", [])
            if isinstance(unsupp, list):
                unsupported_count += len(unsupp)

    return {
        "total_count": total_count,
        "valid_count": n_valid,
        "invalid_count": n_invalid,
        "invalid_rate": invalid_rate,
        "mean": round(mean_val, 4),
        "median": round(median_val, 4),
        "p10": round(p10_val, 4),
        "unsupported_count": unsupported_count,
        "valid_records_by_id": {r["case_id"]: r for r in valid_records if "case_id" in r},
        "invalid_records_by_id": {r["case_id"]: r for r in invalid_records if "case_id" in r},
    }


def compute_bootstrap_paired_ci(
    paired_deltas: List[float],
    n_resamples: int = 10000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Computes bootstrap confidence interval for paired mean delta with a fixed seed.
    Returns mean, std_err, ci_lower, ci_upper.
    """
    if not paired_deltas:
        return {
            "mean": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "std_err": 0.0,
            "n_resamples": n_resamples,
            "seed": seed,
        }

    deltas_arr = np.array(paired_deltas, dtype=float)
    n = len(deltas_arr)
    rng = np.random.RandomState(seed)

    # Resample with replacement
    indices = rng.randint(0, n, size=(n_resamples, n))
    resampled_means = np.mean(deltas_arr[indices], axis=1)

    ci_lower = float(np.percentile(resampled_means, 100 * (alpha / 2.0)))
    ci_upper = float(np.percentile(resampled_means, 100 * (1.0 - alpha / 2.0)))
    mean_delta = float(np.mean(deltas_arr))
    std_err = float(np.std(resampled_means))

    return {
        "mean": round(mean_delta, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "std_err": round(std_err, 4),
        "n_resamples": n_resamples,
        "seed": seed,
    }


def compute_paired_comparison(
    cand_stats: Dict[str, Any],
    base_stats: Dict[str, Any],
    tolerance: float = 1e-4,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Computes paired analysis strictly on the INTERSECTION of valid cases.
    Identifies excluded cases and reasons, and determines verdict.
    """
    cand_valid_ids: Set[str] = set(cand_stats["valid_records_by_id"].keys())
    base_valid_ids: Set[str] = set(base_stats["valid_records_by_id"].keys())
    all_case_ids: Set[str] = cand_valid_ids.union(
        cand_stats["invalid_records_by_id"].keys(),
        base_valid_ids,
        base_stats["invalid_records_by_id"].keys(),
    )

    intersection_ids = sorted(list(cand_valid_ids.intersection(base_valid_ids)))
    total_benchmark_cases = len(all_case_ids) or 40

    # Identify exclusions
    excluded_cases = []
    for cid in sorted(list(all_case_ids)):
        if cid not in intersection_ids:
            reasons = []
            if cid not in cand_valid_ids:
                cand_inv = cand_stats["invalid_records_by_id"].get(cid, {})
                st = cand_inv.get("eval_status", "invalid")
                err = cand_inv.get("nan_reasons") or cand_inv.get("error_class") or "unscored/missing"
                reasons.append(f"Candidate invalid ({st}: {err})")
            if cid not in base_valid_ids:
                base_inv = base_stats["invalid_records_by_id"].get(cid, {})
                st = base_inv.get("eval_status", "invalid")
                err = base_inv.get("nan_reasons") or base_inv.get("error_class") or "unscored/missing"
                reasons.append(f"Baseline invalid ({st}: {err})")
            excluded_cases.append({
                "case_id": cid,
                "reason": "; ".join(reasons),
            })

    paired_deltas = []
    cand_intersection_scores = []
    base_intersection_scores = []
    wins = 0
    losses = 0
    ties = 0

    for cid in intersection_ids:
        c_score = float(cand_stats["valid_records_by_id"][cid]["judge_faithfulness"])
        b_score = float(base_stats["valid_records_by_id"][cid]["judge_faithfulness"])
        cand_intersection_scores.append(c_score)
        base_intersection_scores.append(b_score)
        delta = c_score - b_score
        paired_deltas.append(delta)

        if delta > tolerance:
            wins += 1
        elif delta < -tolerance:
            losses += 1
        else:
            ties += 1

    bootstrap_ci = compute_bootstrap_paired_ci(paired_deltas, seed=seed)

    coverage_rate = (len(intersection_ids) / total_benchmark_cases) if total_benchmark_cases > 0 else 0.0
    cand_invalid_rate = cand_stats["invalid_rate"]
    base_invalid_rate = base_stats["invalid_rate"]

    # Strict Verdict Determination
    # Rule: Output INCONCLUSIVE if invalid rate > 3% or paired set covers < 90% of cases; never recommendation from mean alone.
    if cand_invalid_rate > 0.03:
        verdict = "INCONCLUSIVE"
        verdict_reason = f"Candidate invalid rate ({cand_invalid_rate:.1%}) exceeds 3.0% threshold."
    elif base_invalid_rate > 0.03:
        verdict = "INCONCLUSIVE"
        verdict_reason = f"Baseline invalid rate ({base_invalid_rate:.1%}) exceeds 3.0% threshold."
    elif coverage_rate < 0.90:
        verdict = "INCONCLUSIVE"
        verdict_reason = f"Paired valid intersection coverage ({coverage_rate:.1%}) is below 90.0% threshold."
    else:
        # Check bootstrap CI: strictly positive -> IMPROVEMENT, strictly negative -> REGRESSION, spans zero -> INCONCLUSIVE
        ci_lower = bootstrap_ci["ci_lower"]
        ci_upper = bootstrap_ci["ci_upper"]
        if ci_lower > 0:
            verdict = "CANDIDATE IMPROVEMENT"
            verdict_reason = f"Paired mean delta is statistically positive (95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}])."
        elif ci_upper < 0:
            verdict = "REGRESSION DETECTED (REVERT / ROLLBACK)"
            verdict_reason = f"Paired mean delta is statistically negative (95% CI: [{ci_lower:+.4f}, {ci_upper:+.4f}])."
        else:
            verdict = "INCONCLUSIVE / NO STATISTICAL DIFFERENCE"
            verdict_reason = f"95% bootstrap CI crosses zero ([{ci_lower:+.4f}, {ci_upper:+.4f}])."

    base_intersect_mean = round(float(np.mean(base_intersection_scores)), 4) if base_intersection_scores else 0.0
    cand_intersect_mean = round(float(np.mean(cand_intersection_scores)), 4) if cand_intersection_scores else 0.0
    intersect_delta = round(cand_intersect_mean - base_intersect_mean, 4)

    return {
        "intersection_count": len(intersection_ids),
        "total_benchmark_cases": total_benchmark_cases,
        "coverage_rate": coverage_rate,
        "base_intersection_mean": base_intersect_mean,
        "cand_intersection_mean": cand_intersect_mean,
        "intersection_mean_delta": intersect_delta,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "bootstrap_ci": bootstrap_ci,
        "excluded_cases": excluded_cases,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }


def compute_category_breakdown(
    cand_records: List[Dict[str, Any]],
    base_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compute breakdown by category using only valid cases in each category."""
    cand_by_cat: Dict[str, List[float]] = {}
    base_by_cat: Dict[str, List[float]] = {}
    all_cats = set()

    for r in cand_records:
        cat = r.get("category", "unknown")
        all_cats.add(cat)
        f = r.get("judge_faithfulness")
        st = r.get("eval_status")
        if (st == "valid" or st is None) and is_valid_score(f):
            cand_by_cat.setdefault(cat, []).append(float(f))

    for r in base_records:
        cat = r.get("category", "unknown")
        all_cats.add(cat)
        f = r.get("judge_faithfulness")
        st = r.get("eval_status")
        if (st == "valid" or st is None) and is_valid_score(f):
            base_by_cat.setdefault(cat, []).append(float(f))

    rows = []
    for cat in sorted(list(all_cats)):
        c_scores = cand_by_cat.get(cat, [])
        b_scores = base_by_cat.get(cat, [])
        c_mean = float(np.mean(c_scores)) if c_scores else 0.0
        b_mean = float(np.mean(b_scores)) if b_scores else 0.0
        c_count = len(c_scores)
        b_count = len(b_scores)
        delta = c_mean - b_mean
        rows.append({
            "category": cat,
            "count": max(c_count, b_count),
            "cand_valid": c_count,
            "base_valid": b_count,
            "base_mean": round(b_mean, 4),
            "cand_mean": round(c_mean, 4),
            "delta": round(delta, 4),
        })
    return rows


def generate_evaluation_markdown(
    candidate_id: str,
    baseline_id: str,
    cand_records: List[Dict[str, Any]],
    base_records: List[Dict[str, Any]],
    cand_unsupported: Optional[List[Dict[str, Any]]] = None,
    base_unsupported: Optional[List[Dict[str, Any]]] = None,
    cand_manifest: Optional[Dict[str, Any]] = None,
    base_manifest: Optional[Dict[str, Any]] = None,
    seed: int = 42,
) -> str:
    """Generate complete evaluation report markdown dynamically from data."""
    cand_stats = compute_dataset_stats(cand_records, cand_unsupported)
    base_stats = compute_dataset_stats(base_records, base_unsupported)
    paired = compute_paired_comparison(cand_stats, base_stats, seed=seed)
    cat_rows = compute_category_breakdown(cand_records, base_records)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    ci = paired["bootstrap_ci"]

    lines = [
        f"# MediScanAI Dynamic Evaluation Report: {candidate_id} vs {baseline_id}",
        "",
        f"**Generated:** {timestamp}",
        f"**Candidate:** `{candidate_id}`",
        f"**Baseline:** `{baseline_id}`",
        f"**Evaluation Mode:** Manifest-driven, data-only recomputation",
        "",
        "## 1. Executive Summary & Verdict",
        "",
        f"### Verdict: **{paired['verdict']}**",
        f"> **Verdict Rationale:** {paired['verdict_reason']}",
        "",
        "| Metric | Baseline (`" + baseline_id + "`) | Candidate (`" + candidate_id + "`) | Delta / Comparison |",
        "|---|---:|---:|---:|",
        f"| **Valid Scored Cases** | {base_stats['valid_count']} / {base_stats['total_count']} | {cand_stats['valid_count']} / {cand_stats['total_count']} | {cand_stats['valid_count'] - base_stats['valid_count']:+d} |",
        f"| **Invalid Rate** | {base_stats['invalid_rate']:.1%} | {cand_stats['invalid_rate']:.1%} | {cand_stats['invalid_rate'] - base_stats['invalid_rate']:+.1%} |",
        f"| **Mean Faithfulness (All Valid)** | {base_stats['mean']:.4f} | {cand_stats['mean']:.4f} | {cand_stats['mean'] - base_stats['mean']:+.4f} |",
        f"| **Median Faithfulness** | {base_stats['median']:.4f} | {cand_stats['median']:.4f} | {cand_stats['median'] - base_stats['median']:+.4f} |",
        f"| **Unsupported Statements** | {base_stats['unsupported_count']} | {cand_stats['unsupported_count']} | {cand_stats['unsupported_count'] - base_stats['unsupported_count']:+d} |",
        f"| **Paired Intersection Cases** | {paired['intersection_count']} cases | {paired['intersection_count']} cases | Coverage: {paired['coverage_rate']:.1%} |",
        f"| **Paired Intersection Mean** | {paired['base_intersection_mean']:.4f} | {paired['cand_intersection_mean']:.4f} | **{paired['intersection_mean_delta']:+.4f}** |",
        f"| **Paired Wins / Losses / Ties** | — | — | **{paired['wins']} Wins / {paired['losses']} Losses / {paired['ties']} Ties** |",
        f"| **Bootstrap 95% CI (10k resamples)** | — | — | **[{ci['ci_lower']:+.4f}, {ci['ci_upper']:+.4f}]** (SE={ci['std_err']:.4f}) |",
        "",
        "## 2. Excluded Cases in Paired Analysis",
        "",
    ]

    if paired["excluded_cases"]:
        lines.append(f"The following {len(paired['excluded_cases'])} case(s) were excluded from paired comparison due to invalid/missing status:")
        lines.append("")
        lines.append("| Case ID | Reason for Exclusion |")
        lines.append("|---|---|")
        for exc in paired["excluded_cases"]:
            lines.append(f"| `{exc['case_id']}` | {exc['reason']} |")
        lines.append("")
    else:
        lines.append("No cases were excluded. Full 100% paired intersection evaluated.\n")

    lines.extend([
        "## 3. Category Breakdown",
        "",
        "| Category | Valid N (Base/Cand) | Baseline Mean | Candidate Mean | Delta |",
        "|---|---:|---:|---:|---:|",
    ])
    for cr in cat_rows:
        lines.append(f"| `{cr['category']}` | {cr['base_valid']} / {cr['cand_valid']} | {cr['base_mean']:.4f} | {cr['cand_mean']:.4f} | {cr['delta']:+.4f} |")

    lines.append("")
    return "\n".join(lines)


def run_dynamic_verification(run_full_pytest: bool = False) -> Dict[str, Any]:
    """Dynamically query git state and test counts without hardcoding literals."""
    git_sha = "unknown"
    git_dirty = "unknown"
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            git_sha = r.stdout.strip()
        r_st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5)
        git_dirty = "dirty" if r_st.stdout.strip() else "clean"
    except Exception as e:
        git_sha = f"git_error: {e}"

    pytest_results = "not run"
    if run_full_pytest:
        try:
            cmd = ["pytest", "tests/evaluation/test_cache_and_reporting.py", "-q"]
            res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
            pytest_results = res.stdout.strip().split("\n")[-1]
        except Exception as e:
            pytest_results = f"pytest_error: {e}"

    return {
        "git_commit": git_sha,
        "working_tree": git_dirty,
        "pytest_summary": pytest_results,
    }
