#!/usr/bin/env python3
"""
MediScanAI — Phase B: Retrieval Evaluation & Evidence Pooling Harness
CLI runner executing baseline hybrid search and/or standalone Neo4j graph retrieval,
pooling evidence, deduplicating with provenance, and calculating deterministic metrics.

Strictly preserves:
1. No LLM generation or LLM judge.
2. candidate_judgments.jsonl is NOT treated as gold.
3. If gold_judgments.jsonl is empty, reports not_evaluable_no_reviewed_gold_labels.
4. No modification to production code, datasets, or indexes.
5. Absolute restriction: entity_resolution/ is completely off-limits.
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import subprocess

from evaluation.retrieval.schemas import (
    RetrievedItem,
    PooledEvidence,
    CaseEvaluationResult,
    EvaluationSummary,
)
from evaluation.retrieval.metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_reciprocal_rank,
    compute_false_positive_count_at_k,
    compute_rejection_accuracy,
    compute_graph_added_coverage,
    compute_latency_percentiles,
    is_relevant,
)
from evaluation.retrieval.pool_evidence import (
    parse_baseline_retrieval_tuple,
    load_existing_reviews,
    pool_evidence_for_case,
    export_pooled_evidence_to_csv,
    normalize_disease_chunk_id,
)

logger = logging.getLogger("mediscanai.evaluation.runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_git_metadata() -> Dict[str, Any]:
    """
    Safely retrieves git branch, commit SHA, and dirty status without network calls.

    is_dirty semantics:
    - True: working tree is known to be dirty (uncommitted modifications or untracked files).
    - False: working tree is confirmed clean by `git status --porcelain`.
    - None: working tree cleanliness cannot be determined (Git unavailable or status failed).
    """
    data: Dict[str, Any] = {
        "git_branch": "unknown",
        "git_commit": "unavailable",
        "is_dirty": None,
    }
    # 1. Try git CLI if available
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            data["git_branch"] = res.stdout.strip()

        res_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res_sha.returncode == 0 and res_sha.stdout.strip():
            data["git_commit"] = res_sha.stdout.strip()

        try:
            res_dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if res_dirty.returncode == 0:
                data["is_dirty"] = bool(res_dirty.stdout.strip())
            else:
                data["is_dirty"] = None
        except Exception:
            data["is_dirty"] = None

        if data["git_commit"] != "unavailable":
            return data
    except Exception:
        pass

    # 2. Filesystem fallback if git CLI is unavailable or failed
    try:
        head_file = Path(".git/HEAD")
        if head_file.exists():
            content = head_file.read_text(encoding="utf-8").strip()
            if content.startswith("ref: refs/heads/"):
                branch_name = content.replace("ref: refs/heads/", "")
                data["git_branch"] = branch_name
                ref_file = Path(f".git/refs/heads/{branch_name}")
                if ref_file.exists():
                    data["git_commit"] = ref_file.read_text(encoding="utf-8").strip()
                else:
                    packed_file = Path(".git/packed-refs")
                    if packed_file.exists():
                        for pline in packed_file.read_text(encoding="utf-8").splitlines():
                            pline = pline.strip()
                            if pline and not pline.startswith(("#", "^")):
                                parts = pline.split()
                                if len(parts) >= 2 and parts[1] == f"refs/heads/{branch_name}":
                                    data["git_commit"] = parts[0]
                                    break
            else:
                data["git_commit"] = content
                data["git_branch"] = content[:8]
    except Exception:
        pass

    return data


def get_benchmark_version(benchmark_dir: Path) -> str:
    """Reads benchmark_version from benchmark_metadata.json if available."""
    meta_path = benchmark_dir / "benchmark_metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    ver = data.get("benchmark_version")
                    if ver and isinstance(ver, str) and ver.strip():
                        return ver.strip()
        except Exception:
            pass
    return "unknown"


def load_candidate_queries(benchmark_dir: Path) -> List[Dict[str, Any]]:
    queries_file = benchmark_dir / "candidate_queries.jsonl"
    if not queries_file.exists():
        raise FileNotFoundError(f"Missing candidate queries file: {queries_file}")

    queries = []
    with open(queries_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries


def load_gold_judgments(benchmark_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Loads genuinely human-reviewed gold evidence IDs per case.
    Strictly filters for judgment_status == 'human_reviewed'.
    Differentiates between:
    - Cases with reviewed relevant evidence (relevance_grade >= 2)
    - Cases with reviewed judgments where 0 items are relevant (e.g. negative controls)
    """
    gold_file = benchmark_dir / "gold_judgments.jsonl"
    if not gold_file.exists():
        return {}

    gold_by_case: Dict[str, Dict[str, Any]] = {}
    with open(gold_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                if rec.get("judgment_status") == "human_reviewed":
                    cid = rec["case_id"]
                    if cid not in gold_by_case:
                        gold_by_case[cid] = {
                            "has_reviewed_judgments": True,
                            "relevant_ids": set(),
                            "all_reviewed_ids": set(),
                        }
                    eid = rec.get("evidence_id")
                    if eid:
                        gold_by_case[cid]["all_reviewed_ids"].add(eid)
                        if is_relevant(rec.get("relevance_grade")):
                            gold_by_case[cid]["relevant_ids"].add(eid)
    return gold_by_case


def load_evidence_verified_judgments(
    judgments_file: Path,
    canonical_queries: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Loads and validates AI-assisted evidence-verified judgments from Phase A.3.

    Strictly enforces:
    - Input file must exist (does not silently fall back to gold_judgments.jsonl)
    - human_reviewed must be False
    - adjudicator_type must be 'ai_assisted_external_evidence'
    - evidence_based_grade must be in {0, 1, 2, 3}
    - judgment_status must be in recognized valid statuses
    - case_id and evidence_id must be present and valid
    - Contradictory duplicate records raise ValueError

    Returns:
        (gold_by_case, audit_stats)
    """
    p = Path(judgments_file)
    if not p.exists():
        raise FileNotFoundError(f"Evidence judgments file not found: {p}")

    valid_evaluated_statuses = {
        "evidence_verified",
        "grade_changed_after_research",
        "negative_control_verified",
    }
    unresolved_statuses = {"unresolved", "insufficient_source_evidence"}

    canon_case_ids = set(q["case_id"] for q in canonical_queries) if canonical_queries else None

    gold_by_case: Dict[str, Dict[str, Any]] = {}
    seen_pairs: Dict[Tuple[str, str], int] = {}
    unresolved_case_ids: Set[str] = set()

    audit_stats = {
        "total_records": 0,
        "verified_count": 0,
        "grade_changed_count": 0,
        "negative_control_count": 0,
        "unresolved_count": 0,
        "excluded_count": 0,
        "source_path": str(p),
        "evaluation_track": "ai_assisted_evidence_verified",
    }

    with open(p, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {line_num} in {p} is malformed JSON: {exc}") from exc

            audit_stats["total_records"] += 1

            cid = rec.get("case_id")
            eid = rec.get("evidence_id")
            if not cid or not eid:
                raise ValueError(f"Line {line_num} in {p} missing required case_id or evidence_id")

            if canon_case_ids and cid not in canon_case_ids:
                raise ValueError(f"Line {line_num} in {p}: case_id '{cid}' not in canonical benchmark queries")

            # Provenance verification: must be AI-assisted research, not human gold
            if rec.get("human_reviewed") is not False:
                raise ValueError(
                    f"Line {line_num} in {p}: invalid provenance: human_reviewed must be False, got {rec.get('human_reviewed')}"
                )
            if rec.get("adjudicator_type") != "ai_assisted_external_evidence":
                raise ValueError(
                    f"Line {line_num} in {p}: invalid adjudicator_type: expected 'ai_assisted_external_evidence', got '{rec.get('adjudicator_type')}'"
                )

            grade = rec.get("evidence_based_grade")
            if grade not in (0, 1, 2, 3):
                raise ValueError(
                    f"Line {line_num} in {p}: invalid evidence_based_grade: {grade} (must be in {{0, 1, 2, 3}})"
                )

            # Duplicate checking
            pair = (cid, eid)
            if pair in seen_pairs:
                if seen_pairs[pair] != grade:
                    raise ValueError(
                        f"Line {line_num} in {p}: contradictory duplicate judgment for {pair}: prior grade {seen_pairs[pair]} vs current {grade}"
                    )
                # Identical duplicate: skip re-insertion
                continue
            seen_pairs[pair] = grade

            status = rec.get("judgment_status")
            if status in unresolved_statuses:
                audit_stats["unresolved_count"] += 1
                audit_stats["excluded_count"] += 1
                unresolved_case_ids.add(cid)
                continue
            elif status not in valid_evaluated_statuses:
                raise ValueError(f"Line {line_num} in {p}: unrecognized judgment_status '{status}'")

            if status == "evidence_verified":
                audit_stats["verified_count"] += 1
            elif status == "grade_changed_after_research":
                audit_stats["grade_changed_count"] += 1
            elif status == "negative_control_verified":
                audit_stats["negative_control_count"] += 1

            if cid not in gold_by_case:
                gold_by_case[cid] = {
                    "has_reviewed_judgments": True,
                    "relevant_ids": set(),
                    "all_reviewed_ids": set(),
                    "grades": {},
                    "raw_records": [],
                    "is_unresolved": False,
                }

            gold_by_case[cid]["all_reviewed_ids"].add(eid)
            gold_by_case[cid]["grades"][eid] = grade
            gold_by_case[cid]["raw_records"].append(rec)
            if is_relevant(grade):
                gold_by_case[cid]["relevant_ids"].add(eid)

    # For any case where ALL records were unresolved
    for cid in unresolved_case_ids:
        if cid not in gold_by_case:
            gold_by_case[cid] = {
                "has_reviewed_judgments": False,
                "relevant_ids": set(),
                "all_reviewed_ids": set(),
                "is_unresolved": True,
            }

    return gold_by_case, audit_stats


class EvaluationRunner:
    def __init__(
        self,
        mode: str = "both",
        top_k: int = 5,
        benchmark_dir: Path = Path("evaluation/benchmark"),
        output_dir: Optional[Path] = None,
        neo4j_enabled: Optional[bool] = None,
        evidence_judgments_path: Optional[Path] = None,
    ):
        self.mode = mode
        self.top_k = top_k
        self.benchmark_dir = Path(benchmark_dir)

        self.evidence_judgments_path = Path(evidence_judgments_path) if evidence_judgments_path is not None else None

        # Determine evaluation track
        if self.evidence_judgments_path is not None:
            self.evaluation_track = "ai_assisted_evidence_verified"
            self.judgments_path = self.evidence_judgments_path
            self.track_disclaimer = (
                "AI-Assisted Evidence-Verified Evaluation — Not Human-Adjudicated Gold. "
                "Relevance grades were verified against authoritative external sources "
                "(DailyMed, FDA, NIH, CDC, WHO) and do not constitute licensed clinical sign-off."
            )
        else:
            self.evaluation_track = "official_human_gold"
            self.judgments_path = self.benchmark_dir / "gold_judgments.jsonl"
            self.track_disclaimer = "Official human-gold ground truth. Quality metrics require licensed clinical review."

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if self.evaluation_track == "ai_assisted_evidence_verified":
            self.run_id = f"eval_evidence_verified_{self.mode}_{timestamp_str}"
        else:
            self.run_id = f"eval_{self.mode}_{timestamp_str}"

        self.output_dir = output_dir or Path(f"evaluation/results/{self.run_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.retriever = None
        self.graph_retriever = None

        # Load benchmark assets
        self.candidate_queries = load_candidate_queries(self.benchmark_dir)

        if self.evaluation_track == "ai_assisted_evidence_verified":
            self.gold_judgments, self.audit_counts = load_evidence_verified_judgments(
                self.judgments_path,
                canonical_queries=self.candidate_queries,
            )
        else:
            self.gold_judgments = load_gold_judgments(self.benchmark_dir)
            self.audit_counts = {
                "total_records": sum(len(v.get("all_reviewed_ids", [])) for v in self.gold_judgments.values()),
                "source_path": str(self.judgments_path),
                "evaluation_track": self.evaluation_track,
            }

        self.evidence_audit_counts = self.audit_counts if self.evaluation_track == "ai_assisted_evidence_verified" else None
        self.prior_reviews = load_existing_reviews(self.benchmark_dir / "review_template.csv")

        # Determine Neo4j setting
        from backend.core.config import get_settings
        self.settings = get_settings()
        if neo4j_enabled is not None:
            self.settings.NEO4J_ENABLED = neo4j_enabled


    def init_retrievers(self):
        """Initializes retrieval engines lazily per selected mode."""
        if self.mode in ("baseline", "both"):
            logger.info("Initializing production MultiRetriever for baseline hybrid search...")
            from app.retriever import MultiRetriever
            self.retriever = MultiRetriever()

        if self.mode in ("graph", "both"):
            logger.info("Initializing GraphRetriever for Neo4j graph search...")
            from app.graph.retriever import GraphRetriever
            self.graph_retriever = GraphRetriever(settings=self.settings)

    def execute_baseline(self, query: str, expected_types: List[str]) -> Tuple[List[RetrievedItem], int, Optional[str]]:
        """Executes MultiRetriever across the appropriate index based on expected evidence types."""
        if not self.retriever:
            return [], 0, "baseline_not_initialized"

        t0 = time.perf_counter()
        raw_results = []
        try:
            # Query selection routing
            if "drug_product" in expected_types and "disease_chunk" not in expected_types:
                raw_results = [(r, "drugs") for r in self.retriever.search_specific("drugs", query, top_k=self.top_k)]
            elif "disease_chunk" in expected_types and "drug_product" not in expected_types:
                raw_results = [(r, "diseases") for r in self.retriever.search_specific("diseases", query, top_k=self.top_k)]
            else:
                # Ambiguous / general query: search both indexes
                r_drugs = self.retriever.search_specific("drugs", query, top_k=self.top_k)
                r_diseases = self.retriever.search_specific("diseases", query, top_k=self.top_k)
                raw_results = [(r, "drugs") for r in r_drugs] + [(r, "diseases") for r in r_diseases]

            latency_ms = int((time.perf_counter() - t0) * 1000)
            items = []
            for rank_idx, (raw_tuple, index_name) in enumerate(raw_results, 1):
                items.append(parse_baseline_retrieval_tuple(raw_tuple, index_name, rank=rank_idx))

            return items, latency_ms, None
        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("Baseline retrieval error for query '%s': %s", query, e)
            return [], latency_ms, str(e)

    def execute_graph(self, query: str, expected_types: List[str], query_category: str) -> Tuple[List[RetrievedItem], int, Optional[str]]:
        """Executes GraphRetriever using existing query methods and extracts provenance."""
        if not self.graph_retriever:
            return [], 0, "graph_not_initialized"

        t0 = time.perf_counter()
        items: List[RetrievedItem] = []
        try:
            if "drug_product" in expected_types:
                resp = self.graph_retriever.find_drugs_by_name(query, limit=self.top_k)
                # If name lookup yielded empty and query might be an ingredient
                if resp.status == "empty" and query_category in ("active_ingredient_lookup", "brand_generic_ingredient_relationship"):
                    resp = self.graph_retriever.find_drugs_by_ingredient(query, limit=self.top_k)

                if resp.status == "success":
                    for rank_idx, d in enumerate(resp.drugs, 1):
                        eid = f"drug_{d.source_id}"
                        excerpt = f"Brand: {d.brand_name}; Generic: {d.generic_name}; Ingredients: {d.active_ingredients}"
                        items.append(
                            RetrievedItem(
                                evidence_id=eid,
                                evidence_type="drug_product",
                                source_record_id=d.source_id,
                                channel="graph",
                                rank=rank_idx,
                                score=1.0,
                                evidence_excerpt=excerpt,
                                provenance=d.provenance,
                                is_resolved=True,
                            )
                        )
                elif resp.status in ("error", "timeout", "disabled"):
                    latency_ms = int((time.perf_counter() - t0) * 1000)
                    return [], latency_ms, f"graph_{resp.status}:{resp.error_code or ''}"

            elif "disease_chunk" in expected_types:
                # Symptom query
                symptoms = [s.strip() for s in query.split(",") if s.strip()] or [query]
                resp = self.graph_retriever.find_diseases_by_symptoms(symptoms, limit=self.top_k, max_chunks_per_disease=2)

                if resp.status == "success":
                    rank_counter = 1
                    for dis in resp.diseases:
                        for chunk in dis.chunks:
                            eid = normalize_disease_chunk_id(chunk.chunk_id)
                            excerpt = f"Disease: {dis.disease_name}; Symptoms: {dis.all_symptoms[:5]}"
                            items.append(
                                RetrievedItem(
                                    evidence_id=eid,
                                    evidence_type="disease_chunk",
                                    source_record_id=chunk.source_id,
                                    channel="graph",
                                    rank=rank_counter,
                                    score=float(dis.overlap_count),
                                    evidence_excerpt=excerpt,
                                    provenance={
                                        "entity": "Disease",
                                        "disease_name": dis.disease_name,
                                        "chunk_id": chunk.chunk_id,
                                        "source_id": chunk.source_id,
                                    },
                                    is_resolved=True,
                                )
                            )
                            rank_counter += 1
                elif resp.status in ("error", "timeout", "disabled"):
                    latency_ms = int((time.perf_counter() - t0) * 1000)
                    return [], latency_ms, f"graph_{resp.status}:{resp.error_code or ''}"

            latency_ms = int((time.perf_counter() - t0) * 1000)
            return items, latency_ms, None
        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.error("Graph retrieval error for query '%s': %s", query, e)
            return [], latency_ms, str(e)

    def evaluate_case(self, case: Dict[str, Any]) -> CaseEvaluationResult:
        case_id = case["case_id"]
        query = case["query"]
        category = case["query_category"]
        expected_types = case.get("expected_evidence_types", [])

        b_items: List[RetrievedItem] = []
        g_items: List[RetrievedItem] = []
        b_latency = 0
        g_latency = 0
        err_msg = None

        t_case_start = time.perf_counter()

        # 1. Baseline retrieval
        if self.mode in ("baseline", "both"):
            b_items, b_latency, b_err = self.execute_baseline(query, expected_types)
            if b_err:
                err_msg = f"Baseline error: {b_err}"

        # 2. Graph retrieval
        if self.mode in ("graph", "both"):
            g_items, g_latency, g_err = self.execute_graph(query, expected_types, category)
            if g_err:
                err_msg = f"{err_msg or ''}; Graph error: {g_err}".strip("; ")

        # 3. Pooling and Deduplication
        t_pool_start = time.perf_counter()
        pooled_items, stats = pool_evidence_for_case(
            case_id=case_id,
            query=query,
            query_category=category,
            baseline_items=b_items,
            graph_items=g_items,
            existing_reviews=self.prior_reviews,
        )
        pool_latency = int((time.perf_counter() - t_pool_start) * 1000)
        total_latency = int((time.perf_counter() - t_case_start) * 1000)

        # 4. Deterministic Metric Calculation
        gold_status = self.gold_judgments.get(case_id)
        metrics: Dict[str, Any] = {}

        b_ids = [item.evidence_id for item in b_items]
        g_ids = [item.evidence_id for item in g_items]
        primary_ids = b_ids if self.mode in ("baseline", "both") else g_ids

        if gold_status is None or not gold_status.get("has_reviewed_judgments"):
            # State 1: No reviewed gold judgments exist for this case (or unresolved)
            eligibility_label = (
                "excluded_unresolved_evidence"
                if (gold_status and gold_status.get("is_unresolved"))
                else "not_evaluable_no_reviewed_gold_labels"
            )
            metrics = {
                "eligibility": eligibility_label,
                "recall_at_k": None,
                "precision_at_k": None,
                "baseline_mrr": None,
                "graph_mrr": None,
                "pooled_mrr": None,
                "false_positive_count_at_k": None,
                "rejection_accuracy": None,
                "graph_added_coverage": None,
            }
        else:
            relevant_gold = gold_status["relevant_ids"]
            if len(relevant_gold) > 0:
                # State 2: Case has verified relevant evidence
                case_elig = (
                    "eligible_evidence_verified"
                    if self.evaluation_track == "ai_assisted_evidence_verified"
                    else "eligible_reviewed_gold"
                )
                baseline_mrr = compute_reciprocal_rank(b_ids, relevant_gold, k=self.top_k) if b_ids else None
                metrics = {
                    "eligibility": case_elig,
                    "recall_at_k": compute_recall_at_k(primary_ids, relevant_gold, k=self.top_k),
                    "precision_at_k": compute_precision_at_k(primary_ids, relevant_gold, k=self.top_k),
                    "baseline_mrr": baseline_mrr,
                    "graph_mrr": None,   # Unordered candidate set (source_id ASC); no synthetic graph MRR
                    "pooled_mrr": None,  # Prohibited: no synthetic concatenated ranking
                    "false_positive_count_at_k": None,
                    "rejection_accuracy": None,
                    "graph_added_coverage": compute_graph_added_coverage(
                        baseline_ids=b_ids,
                        graph_ids=g_ids,
                        gold_relevant_ids=relevant_gold,
                    ),
                }
            else:
                # Reviewed case with zero relevant items
                # Formally designated negative control per benchmark schema and metric contract Section 5:
                # 1. query_category must be exactly "insufficient_evidence_unanswerable"
                # 2. expected_evidence_types must be formally specified as ["none"]
                is_formal_negative_control = (
                    category == "insufficient_evidence_unanswerable"
                    and expected_types == ["none"]
                )
                if is_formal_negative_control:
                    # State 3: Verified negative control / unanswerable case
                    metrics = {
                        "eligibility": "eligible_negative_control",
                        "recall_at_k": None,  # Ineligible for Recall@K per contract Section 3.1
                        "precision_at_k": None,
                        "baseline_mrr": None,  # Ineligible for MRR per contract Section 3.3
                        "graph_mrr": None,
                        "pooled_mrr": None,
                        "false_positive_count_at_k": compute_false_positive_count_at_k(primary_ids, k=self.top_k),
                        "rejection_accuracy": compute_rejection_accuracy(primary_ids, k=self.top_k),
                        "graph_added_coverage": compute_graph_added_coverage(
                            baseline_ids=b_ids,
                            graph_ids=g_ids,
                            gold_relevant_ids=set(),
                        ),
                    }
                else:
                    # State 4: Reviewed case with no relevant evidence not designated as negative control
                    metrics = {
                        "eligibility": "excluded_no_relevant_gold_evidence",
                        "recall_at_k": None,
                        "precision_at_k": None,
                        "baseline_mrr": None,
                        "graph_mrr": None,
                        "pooled_mrr": None,
                        "false_positive_count_at_k": None,
                        "rejection_accuracy": None,
                        "graph_added_coverage": None,
                    }

        status = "success"
        if err_msg:
            status = "error" if not (b_items or g_items) else "partial_success"
        elif not (b_items or g_items):
            status = "empty"

        return CaseEvaluationResult(
            case_id=case_id,
            query=query,
            query_category=category,
            mode=self.mode,
            status=status,
            baseline_count=stats["baseline_count"],
            graph_count=stats["graph_count"],
            pooled_count=stats["pooled_count"],
            overlap_count=stats["overlap_count"],
            graph_only_count=stats["graph_only_count"],
            baseline_latency_ms=b_latency,
            graph_latency_ms=g_latency,
            pooling_latency_ms=pool_latency,
            total_latency_ms=total_latency,
            retrieved_items=b_items + g_items,
            pooled_evidence=pooled_items,
            metrics=metrics,
            error_message=err_msg,
        )

    def run_benchmark(
        self,
        case_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
    ) -> EvaluationSummary:
        self.init_retrievers()

        target_cases = self.candidate_queries
        if case_filter:
            target_cases = [c for c in target_cases if c["case_id"] in case_filter]
        if category_filter:
            target_cases = [c for c in target_cases if c["query_category"] in category_filter]

        logger.info("Executing evaluation runner on %d benchmark cases (mode=%s)...", len(target_cases), self.mode)

        all_results: List[CaseEvaluationResult] = []
        all_pooled: List[PooledEvidence] = []
        errors: List[Dict[str, Any]] = []

        total_latencies = []
        base_latencies = []
        graph_latencies = []

        eligible_gold_count = 0
        eligible_neg_count = 0
        excluded_no_rel_count = 0
        excluded_unresolved_count = 0
        not_evaluable_count = 0

        for idx, case in enumerate(target_cases, 1):
            logger.info("[%d/%d] Case %s: '%s' (%s)", idx, len(target_cases), case["case_id"], case["query"], case["query_category"])
            res = self.evaluate_case(case)
            all_results.append(res)
            all_pooled.extend(res.pooled_evidence)

            elig = res.metrics.get("eligibility")
            if elig in ("eligible_reviewed_gold", "eligible_evidence_verified"):
                eligible_gold_count += 1
            elif elig == "eligible_negative_control":
                eligible_neg_count += 1
            elif elig == "excluded_no_relevant_gold_evidence":
                excluded_no_rel_count += 1
            elif elig == "excluded_unresolved_evidence":
                excluded_unresolved_count += 1
            else:
                not_evaluable_count += 1

            total_latencies.append(res.total_latency_ms)
            if res.baseline_latency_ms > 0:
                base_latencies.append(res.baseline_latency_ms)
            if res.graph_latency_ms > 0:
                graph_latencies.append(res.graph_latency_ms)

            if res.error_message:
                errors.append({
                    "case_id": res.case_id,
                    "query": res.query,
                    "mode": self.mode,
                    "status": res.status,
                    "error": res.error_message,
                })

        # Summarize macro metrics
        macro_metrics: Dict[str, Any] = {}
        if eligible_gold_count == 0 and eligible_neg_count == 0:
            overall_metric_status = "not_evaluable_no_reviewed_gold_labels"
        elif eligible_gold_count > 0:
            if self.evaluation_track == "ai_assisted_evidence_verified":
                overall_metric_status = "eligible_evidence_verified"
            else:
                overall_metric_status = "eligible_reviewed_gold"
        else:
            overall_metric_status = "eligible_negative_control"

        if eligible_gold_count > 0:
            gold_cases = [r for r in all_results if r.metrics.get("eligibility") in ("eligible_reviewed_gold", "eligible_evidence_verified")]
            eligible_recalls = [r.metrics["recall_at_k"] for r in gold_cases if r.metrics.get("recall_at_k") is not None]
            eligible_precisions = [r.metrics["precision_at_k"] for r in gold_cases if r.metrics.get("precision_at_k") is not None]
            eligible_mrrs = [r.metrics["baseline_mrr"] for r in gold_cases if r.metrics.get("baseline_mrr") is not None]

            macro_metrics = {
                f"macro_recall_at_{self.top_k}": round(sum(eligible_recalls) / len(eligible_recalls), 4) if eligible_recalls else None,
                f"macro_precision_at_{self.top_k}": round(sum(eligible_precisions) / len(eligible_precisions), 4) if eligible_precisions else None,
                "macro_baseline_mrr": round(sum(eligible_mrrs) / len(eligible_mrrs), 4) if eligible_mrrs else None,
                "macro_graph_mrr": None,   # Prohibited: graph retriever is unordered
                "macro_pooled_mrr": None,  # Prohibited: no synthetic pooled ranking
            }

        if eligible_neg_count > 0:
            neg_cases = [r for r in all_results if r.metrics.get("eligibility") == "eligible_negative_control"]
            rejections = [r.metrics["rejection_accuracy"] for r in neg_cases if r.metrics.get("rejection_accuracy") is not None]
            fps = [r.metrics["false_positive_count_at_k"] for r in neg_cases if r.metrics.get("false_positive_count_at_k") is not None]
            macro_metrics["negative_control_evaluated_count"] = len(neg_cases)
            macro_metrics[f"macro_rejection_accuracy_at_{self.top_k}"] = round(sum(rejections) / len(rejections), 4) if rejections else None
            macro_metrics[f"macro_false_positive_count_at_{self.top_k}"] = round(sum(fps) / len(fps), 4) if fps else None

        git_meta = get_git_metadata()
        benchmark_version = get_benchmark_version(self.benchmark_dir)

        summary = EvaluationSummary(
            run_id=self.run_id,
            mode=self.mode,
            timestamp=datetime.utcnow().isoformat() + "Z",
            git_branch=git_meta["git_branch"],
            git_commit=git_meta["git_commit"],
            is_dirty=git_meta["is_dirty"],
            benchmark_version=benchmark_version,
            benchmark_path=str(self.benchmark_dir),
            selected_case_ids=[c["case_id"] for c in target_cases],
            total_cases=len(target_cases),
            successful_cases=sum(1 for r in all_results if r.status in ("success", "partial_success")),
            failed_cases=sum(1 for r in all_results if r.status == "error"),
            empty_cases=sum(1 for r in all_results if r.status == "empty"),
            metric_eligibility_status=overall_metric_status,
            eligible_query_count=eligible_gold_count + eligible_neg_count,
            excluded_query_count=excluded_no_rel_count + not_evaluable_count + excluded_unresolved_count,
            macro_metrics=macro_metrics,
            latency_summary={
                "total_run_latency": compute_latency_percentiles(total_latencies),
                "baseline_latency": compute_latency_percentiles(base_latencies),
                "graph_latency": compute_latency_percentiles(graph_latencies),
            },
            channel_overlap_summary={
                "total_baseline_retrieved": sum(r.baseline_count for r in all_results),
                "total_graph_retrieved": sum(r.graph_count for r in all_results),
                "total_pooled_unique": sum(r.pooled_count for r in all_results),
                "total_channel_overlap": sum(r.overlap_count for r in all_results),
                "total_graph_only": sum(r.graph_only_count for r in all_results),
            },
            config={
                "mode": self.mode,
                "top_k": self.top_k,
                "neo4j_enabled": self.settings.NEO4J_ENABLED,
                "evaluation_track": self.evaluation_track,
                "judgments_path": str(self.judgments_path),
            },
            evaluation_track=self.evaluation_track,
            judgments_path=str(self.judgments_path),
            track_disclaimer=self.track_disclaimer,
            audit_counts=self.audit_counts,
        )

        # Write artifacts
        self._write_artifacts(all_results, all_pooled, summary, errors)
        return summary

    def _write_artifacts(
        self,
        results: List[CaseEvaluationResult],
        pooled_evidence: List[PooledEvidence],
        summary: EvaluationSummary,
        errors: List[Dict[str, Any]],
    ):
        logger.info("Writing machine-readable evaluation artifacts to %s...", self.output_dir)

        # 1. run_metadata.json
        with open(self.output_dir / "run_metadata.json", "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)

        # 2. per_case_results.jsonl
        with open(self.output_dir / "per_case_results.jsonl", "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

        # 3. retrieved_evidence.jsonl
        with open(self.output_dir / "retrieved_evidence.jsonl", "w", encoding="utf-8") as f:
            for r in results:
                for item in r.retrieved_items:
                    row_dict = item.to_dict()
                    row_dict["case_id"] = r.case_id
                    f.write(json.dumps(row_dict, ensure_ascii=False) + "\n")

        # 4. pooled_evidence_review.csv
        export_pooled_evidence_to_csv(pooled_evidence, self.output_dir / "pooled_evidence_review.csv")

        # 5. summary.json
        with open(self.output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)

        # 6. summary.csv
        with open(self.output_dir / "summary.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["case_id", "query", "category", "status", "baseline_count", "graph_count", "pooled_count", "overlap_count", "graph_only_count", "total_latency_ms", "eligibility", "baseline_mrr", "evaluation_track"])
            for r in results:
                writer.writerow([
                    r.case_id,
                    r.query,
                    r.query_category,
                    r.status,
                    r.baseline_count,
                    r.graph_count,
                    r.pooled_count,
                    r.overlap_count,
                    r.graph_only_count,
                    r.total_latency_ms,
                    r.metrics.get("eligibility", "unknown"),
                    r.metrics.get("baseline_mrr", ""),
                    self.evaluation_track,
                ])

        # 7. errors.jsonl (if errors occurred)
        if errors:
            with open(self.output_dir / "errors.jsonl", "w", encoding="utf-8") as f:
                for err in errors:
                    f.write(json.dumps(err, ensure_ascii=False) + "\n")

        # 8. README.md
        with open(self.output_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(f"# MediScanAI Evaluation Run: {self.run_id}\n\n")
            if self.evaluation_track == "ai_assisted_evidence_verified":
                f.write("> [!IMPORTANT]\n")
                f.write("> **AI-Assisted Evidence-Verified Evaluation — Not Human-Adjudicated Gold**\n")
                f.write(f"> Ground-truth relevance grades in this run originate from the Phase A.3 independent evidence-adjudication dataset (`{Path(summary.judgments_path).name if summary.judgments_path else 'evidence_verified_judgments.jsonl'}`).\n")
                f.write("> All labels represent AI-assisted research adjudication verified against authoritative external sources (FDA/DailyMed, NIH, CDC, WHO).\n")
                f.write("> **These scores do NOT constitute official human-gold or licensed clinical adjudication.**\n\n")
            f.write(f"- **Evaluation Track:** `{summary.evaluation_track}`\n")
            f.write(f"- **Judgments Source:** `{summary.judgments_path}`\n")
            f.write(f"- **Mode:** `{self.mode}`\n")
            f.write(f"- **Timestamp:** `{summary.timestamp}`\n")
            f.write(f"- **Git Branch:** `{summary.git_branch}` (Commit: `{summary.git_commit}`, Dirty: `{summary.is_dirty}`)\n")
            f.write(f"- **Benchmark Version:** `{summary.benchmark_version}` (Path: `{summary.benchmark_path}`)\n")
            f.write(f"- **Total Cases:** `{summary.total_cases}`\n")
            f.write(f"- **Metric Eligibility Status:** `{summary.metric_eligibility_status}`\n")
            f.write(f"- **Eligible Cases:** `{summary.eligible_query_count}` | **Excluded Cases:** `{summary.excluded_query_count}`\n\n")
            if self.evaluation_track == "ai_assisted_evidence_verified" and summary.audit_counts:
                f.write("## Evidence Adjudication Audit Counts\n")
                f.write(f"- Verified Unchanged Judgments: {summary.audit_counts.get('verified_count', 0)}\n")
                f.write(f"- Grade-Changed Judgments: {summary.audit_counts.get('grade_changed_count', 0)}\n")
                f.write(f"- Negative Control Judgments: {summary.audit_counts.get('negative_control_count', 0)}\n")
                f.write(f"- Unresolved / Insufficient Evidence: {summary.audit_counts.get('unresolved_count', 0)}\n\n")
            f.write("## Channel Overlap Summary\n")
            f.write(f"- Baseline items retrieved: {summary.channel_overlap_summary['total_baseline_retrieved']}\n")
            f.write(f"- Graph items retrieved: {summary.channel_overlap_summary['total_graph_retrieved']}\n")
            f.write(f"- Unique pooled items: {summary.channel_overlap_summary['total_pooled_unique']}\n")
            f.write(f"- Items returned by both channels: {summary.channel_overlap_summary['total_channel_overlap']}\n")
            f.write(f"- Graph-only items: {summary.channel_overlap_summary['total_graph_only']}\n\n")
            f.write("## Ground-Truth Disclaimer\n")
            if self.evaluation_track == "ai_assisted_evidence_verified":
                f.write("AI-Assisted Evidence-Verified Evaluation — Not Human-Adjudicated Gold. Official gold metrics remain blocked until certified human clinical review is completed in `gold_judgments.jsonl` under Phase A.2.\n")
            else:
                f.write("Official quality metrics (Recall@K, Precision@K, MRR) are strictly not evaluable until human clinical adjudication is completed in `gold_judgments.jsonl`. Operational retrieval and latency numbers above reflect descriptive pipeline telemetry only.\n")


def parse_args():
    parser = argparse.ArgumentParser(description="MediScanAI Phase B: Retrieval Evaluation & Pooling Harness (Official Gold & Evidence-Verified Tracks)")
    parser.add_argument("--mode", choices=["baseline", "graph", "both"], default="both", help="Retrieval mode to evaluate")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K cutoff for retrieval evaluation")
    parser.add_argument("--cases", nargs="*", help="Specific case IDs to run (e.g. --cases MED-BENCH-001 MED-BENCH-036)")
    parser.add_argument("--categories", nargs="*", help="Specific query categories to run")
    parser.add_argument("--output-dir", type=str, help="Custom output directory")
    parser.add_argument("--benchmark-dir", type=str, default="evaluation/benchmark", help="Directory containing benchmark files")
    parser.add_argument("--disable-neo4j", action="store_true", help="Force-disable Neo4j graph retrieval")
    parser.add_argument(
        "--evidence-judgments",
        nargs="?",
        const="evaluation/benchmark/evidence_adjudication/phase_a_3/evidence_verified_judgments.jsonl",
        default=None,
        help="Path to evidence-verified judgments JSONL for AI-assisted research evaluation track (defaults to Phase A.3 dataset if flag is passed without path)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    out_path = Path(args.output_dir) if args.output_dir else None
    bench_path = Path(args.benchmark_dir)
    evidence_path = Path(args.evidence_judgments) if args.evidence_judgments else None

    neo4j_override = False if args.disable_neo4j else None

    runner = EvaluationRunner(
        mode=args.mode,
        top_k=args.top_k,
        benchmark_dir=bench_path,
        output_dir=out_path,
        neo4j_enabled=neo4j_override,
        evidence_judgments_path=evidence_path,
    )

    summary = runner.run_benchmark(
        case_filter=args.cases,
        category_filter=args.categories,
    )

    print("\n" + "=" * 60)
    print(f"✅ Evaluation Run Complete: {summary.run_id}")
    print(f"Track: {summary.evaluation_track}")
    print(f"Mode: {summary.mode} | Total Cases: {summary.total_cases}")
    print(f"Metric Eligibility: {summary.metric_eligibility_status}")
    if summary.evaluation_track == "ai_assisted_evidence_verified":
        print("Disclaimer: AI-Assisted Evidence-Verified Evaluation — Not Human-Adjudicated Gold")
    print(f"Artifacts saved to: {runner.output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
