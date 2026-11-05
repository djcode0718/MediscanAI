"""
Evaluation case status model + aggregator (P1 / eval-repair).

A case result can NEVER silently become 0, 1 or NaN: every non-valid case carries an explicit status,
`score=None`, and a stored cause (error_class / error_message). Aggregation computes means over
`valid` cases only and reports counts of every invalid status.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class EvalStatus(str, Enum):
    valid = "valid"
    invalid_parse_failure = "invalid_parse_failure"
    invalid_empty_statements = "invalid_empty_statements"
    invalid_contaminated = "invalid_contaminated"
    error_runtime = "error_runtime"


@dataclass
class CaseResult:
    case_id: str
    status: EvalStatus
    score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    judge_call_count: int = 0
    retries: int = 0
    # Extra context (not part of the minimal contract, useful for reports / unsupported-statement dumps)
    statements: List[str] = field(default_factory=list)
    statement_details: List[Dict[str, Any]] = field(default_factory=list)
    unsupported: List[Dict[str, Any]] = field(default_factory=list)
    category: Optional[str] = None
    guard_version: Optional[str] = None
    cache_hit: bool = False

    def __post_init__(self):
        self.status = EvalStatus(self.status)
        if self.status is EvalStatus.valid:
            if self.score is None or not isinstance(self.score, (int, float)) or math.isnan(self.score):
                raise ValueError(f"{self.case_id}: a valid result needs a finite numeric score")
        else:
            if self.score is not None:
                raise ValueError(f"{self.case_id}: invalid result ({self.status.value}) must have score=None")

    @property
    def is_valid(self) -> bool:
        return self.status is EvalStatus.valid

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def aggregate_results(results: Iterable[CaseResult]) -> Dict[str, Any]:
    """Means over valid cases only; never coerces an invalid case into a number."""
    results = list(results)
    valid = [r for r in results if r.is_valid]
    invalid_by_status: Dict[str, int] = {s.value: 0 for s in EvalStatus if s is not EvalStatus.valid}
    for r in results:
        if not r.is_valid:
            invalid_by_status[r.status.value] += 1
    scores = sorted(r.score for r in valid)
    n = len(scores)
    median = None
    if n:
        median = scores[n // 2] if n % 2 else (scores[n // 2 - 1] + scores[n // 2]) / 2

    by_cat: Dict[str, List[float]] = defaultdict(list)
    cat_total: Counter = Counter()
    for r in results:
        cat = r.category or "UNKNOWN"
        cat_total[cat] += 1
        if r.is_valid:
            by_cat[cat].append(r.score)

    return {
        "n_total": len(results),
        "n_valid": n,
        "n_invalid": len(results) - n,
        "n_invalid_by_status": invalid_by_status,
        "mean_valid": round(sum(scores) / n, 4) if n else None,
        "median_valid": round(median, 4) if median is not None else None,
        "per_category": {
            c: {
                "n_total": cat_total[c],
                "n_valid": len(by_cat[c]),
                "mean_valid": round(sum(by_cat[c]) / len(by_cat[c]), 4) if by_cat[c] else None,
            }
            for c in sorted(cat_total)
        },
        "note": "Means are computed over status == valid cases only. Invalid cases are never coerced to a number.",
    }
