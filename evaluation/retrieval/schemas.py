"""
MediScanAI — Phase B: Retrieval Evaluation & Pooling Schemas
Defines typed models for retrieval outputs, pooled evidence, metric results,
and run telemetry.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class RetrievedItem:
    """Represents a single evidence item returned by a retrieval channel."""
    evidence_id: str
    evidence_type: str  # "drug_product" | "disease_chunk"
    source_record_id: int
    channel: str  # "baseline" | "graph"
    rank: int  # 1-indexed channel rank
    score: Optional[float] = None
    evidence_excerpt: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    is_resolved: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PooledEvidence:
    """Represents a deduplicated evidence item combining channel observations and review status."""
    case_id: str
    query: str
    query_category: str
    evidence_id: str
    evidence_type: str
    source_record_id: int
    retrieval_channels: List[str]  # e.g. ["baseline", "graph"]
    baseline_rank: Optional[int] = None
    graph_rank: Optional[int] = None
    source_excerpt: str = ""
    proposed_grade: Optional[int] = None
    reviewed_grade: Optional[int] = None
    judgment_status: str = "unreviewed_pooled_candidate"
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    judgment_rationale: str = ""
    adjudication_notes: str = ""
    is_resolved: bool = True
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CaseEvaluationResult:
    """Per-case evaluation telemetry, evidence, and deterministic metrics."""
    case_id: str
    query: str
    query_category: str
    mode: str
    status: str  # "success" | "empty" | "error" | "retrieval_failed"
    baseline_count: int = 0
    graph_count: int = 0
    pooled_count: int = 0
    overlap_count: int = 0
    graph_only_count: int = 0
    baseline_latency_ms: int = 0
    graph_latency_ms: int = 0
    pooling_latency_ms: int = 0
    total_latency_ms: int = 0
    retrieved_items: List[RetrievedItem] = field(default_factory=list)
    pooled_evidence: List[PooledEvidence] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["retrieved_items"] = [item.to_dict() for item in self.retrieved_items]
        d["pooled_evidence"] = [p.to_dict() for p in self.pooled_evidence]
        return d


@dataclass
class EvaluationSummary:
    """
    Aggregated evaluation summary for a benchmark run.

    is_dirty semantics:
    - True: working tree is known to be dirty (uncommitted modifications or untracked files).
    - False: working tree is confirmed clean by git status --porcelain.
    - None: working tree cleanliness cannot be determined (Git unavailable or status failed).
      Serializes to JSON as null.
    """
    run_id: str
    mode: str
    timestamp: str
    git_branch: str
    git_commit: str = "unavailable"
    is_dirty: Optional[bool] = None
    benchmark_version: str = "unknown"
    benchmark_path: str = ""
    selected_case_ids: List[str] = field(default_factory=list)
    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    empty_cases: int = 0
    metric_eligibility_status: str = "not_evaluable_no_reviewed_gold_labels"
    eligible_query_count: int = 0
    excluded_query_count: int = 0
    macro_metrics: Dict[str, Any] = field(default_factory=dict)
    latency_summary: Dict[str, Any] = field(default_factory=dict)
    channel_overlap_summary: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    evaluation_track: str = "official_human_gold"
    judgments_path: Optional[str] = None
    track_disclaimer: str = ""
    audit_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

