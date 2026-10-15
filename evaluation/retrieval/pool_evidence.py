"""
MediScanAI — Phase B: Evidence Pooling & Normalization
Combines results from baseline hybrid search and graph retrieval,
deduplicates by stable composite evidence identity, preserves channel origins
and ranks, and safely merges with prior human review work without overwriting it.
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from evaluation.retrieval.schemas import RetrievedItem, PooledEvidence


def normalize_disease_chunk_id(chunk_id_str: str) -> str:
    """Extracts chunk number from chunk_X or disease_chunk_X and returns disease_chunk_X."""
    match = re.search(r"\d+", str(chunk_id_str))
    if match:
        return f"disease_chunk_{match.group(0)}"
    return str(chunk_id_str)


def parse_baseline_retrieval_tuple(
    raw_tuple: Tuple[str, float, dict],
    index_name: str,
    rank: int,
) -> RetrievedItem:
    """Normalizes a raw (key, score, obj) tuple from MultiRetriever into RetrievedItem."""
    key, score, obj = raw_tuple
    if not isinstance(obj, dict):
        obj = {}

    if index_name == "drugs":
        source_id = int(obj.get("id", key.replace("drug_", "")))
        evidence_id = f"drug_{source_id}"
        evidence_type = "drug_product"
        bname = obj.get("brand_name", "")
        gname = obj.get("generic_name", "")
        subs = ", ".join(obj.get("substance_name", []))
        excerpt = f"Brand: {bname}; Generic: {gname}; Substances: [{subs}]"
        provenance = {"channel": "baseline", "index": "drugs", "source_id": source_id}
    elif index_name == "diseases":
        source_id = int(obj.get("id", 0))
        raw_chunk_id = obj.get("chunk", {}).get("id", f"chunk_{source_id + 1}")
        evidence_id = normalize_disease_chunk_id(raw_chunk_id)
        evidence_type = "disease_chunk"
        dname = obj.get("chunk", {}).get("disease", "")
        syms = ", ".join(obj.get("chunk", {}).get("symptoms", [])[:6])
        excerpt = f"Disease: {dname}; Symptoms: [{syms}]"
        provenance = {
            "channel": "baseline",
            "index": "diseases",
            "source_id": source_id,
            "chunk_id": raw_chunk_id,
        }
    else:
        # Generic fallback
        source_id = int(obj.get("id", 0)) if "id" in obj else 0
        evidence_id = f"item_{source_id}"
        evidence_type = "unknown"
        excerpt = str(obj)[:120]
        provenance = {"channel": "baseline", "index": index_name, "source_id": source_id}

    return RetrievedItem(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_record_id=source_id,
        channel="baseline",
        rank=rank,
        score=float(score) if score is not None else None,
        evidence_excerpt=excerpt,
        provenance=provenance,
        is_resolved=True,
    )


def load_existing_reviews(review_csv_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Loads existing reviews from review_template.csv or previous run into a lookup table."""
    if not review_csv_path.exists():
        return {}

    reviews = {}
    with open(review_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("case_id")
            eid = row.get("evidence_id")
            if cid and eid:
                reviews[(cid, eid)] = row
    return reviews


def pool_evidence_for_case(
    case_id: str,
    query: str,
    query_category: str,
    baseline_items: List[RetrievedItem],
    graph_items: List[RetrievedItem],
    existing_reviews: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
) -> Tuple[List[PooledEvidence], Dict[str, int]]:
    """
    Deduplicates and pools evidence from baseline and graph channels for a single case.
    Merges with prior review history if available.
    """
    existing_lookup = existing_reviews or {}

    # Map by evidence_id
    base_map: Dict[str, RetrievedItem] = {}
    for item in baseline_items:
        if item.evidence_id not in base_map:
            base_map[item.evidence_id] = item

    graph_map: Dict[str, RetrievedItem] = {}
    for item in graph_items:
        if item.evidence_id not in graph_map:
            graph_map[item.evidence_id] = item

    # Order of presentation: baseline ranks first, followed by graph-only items
    ordered_evidence_ids = []
    for item in baseline_items:
        if item.evidence_id not in ordered_evidence_ids:
            ordered_evidence_ids.append(item.evidence_id)
    for item in graph_items:
        if item.evidence_id not in ordered_evidence_ids:
            ordered_evidence_ids.append(item.evidence_id)

    pooled_list: List[PooledEvidence] = []
    overlap_count = 0
    graph_only_count = 0

    for eid in ordered_evidence_ids:
        in_base = eid in base_map
        in_graph = eid in graph_map

        b_item = base_map.get(eid)
        g_item = graph_map.get(eid)

        primary_item = b_item or g_item

        channels = []
        if in_base:
            channels.append("baseline")
        if in_graph:
            channels.append("graph")

        if in_base and in_graph:
            overlap_count += 1
        elif in_graph and not in_base:
            graph_only_count += 1

        b_rank = b_item.rank if b_item else None
        g_rank = g_item.rank if g_item else None

        # Check existing review work
        prior = existing_lookup.get((case_id, eid))
        if prior:
            raw_grade = prior.get("reviewed_grade", "")
            reviewed_grade = int(raw_grade) if raw_grade and raw_grade.strip().isdigit() else None
            raw_proposed = prior.get("proposed_grade", "")
            proposed_grade = int(raw_proposed) if raw_proposed and raw_proposed.strip().isdigit() else None

            rev_id = prior.get("reviewer_id")
            rev_at = prior.get("reviewed_at")
            rationale = prior.get("judgment_rationale", "")
            notes = prior.get("adjudication_notes", "")
            status = prior.get("judgment_status", "preliminary_reviewed")
        else:
            proposed_grade = None
            reviewed_grade = None
            rev_id = None
            rev_at = None
            rationale = "Newly retrieved candidate from live pooling run."
            notes = "Unreviewed pooled candidate."
            status = "unreviewed_pooled_candidate"

        combined_provenance = {
            "baseline": b_item.provenance if b_item else None,
            "graph": g_item.provenance if g_item else None,
        }

        pooled_list.append(
            PooledEvidence(
                case_id=case_id,
                query=query,
                query_category=query_category,
                evidence_id=eid,
                evidence_type=primary_item.evidence_type,
                source_record_id=primary_item.source_record_id,
                retrieval_channels=channels,
                baseline_rank=b_rank,
                graph_rank=g_rank,
                source_excerpt=primary_item.evidence_excerpt,
                proposed_grade=proposed_grade,
                reviewed_grade=reviewed_grade,
                judgment_status=status,
                reviewer_id=rev_id,
                reviewed_at=rev_at,
                judgment_rationale=rationale,
                adjudication_notes=notes,
                is_resolved=primary_item.is_resolved,
                provenance=combined_provenance,
            )
        )

    stats = {
        "baseline_count": len(base_map),
        "graph_count": len(graph_map),
        "pooled_count": len(pooled_list),
        "overlap_count": overlap_count,
        "graph_only_count": graph_only_count,
    }

    return pooled_list, stats


def export_pooled_evidence_to_csv(
    pooled_items: List[PooledEvidence],
    output_path: Path,
) -> None:
    """Exports pooled evidence list to CSV without modifying original files."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "case_id",
        "query",
        "query_category",
        "evidence_id",
        "evidence_type",
        "source_record_id",
        "retrieval_channels",
        "baseline_rank",
        "graph_rank",
        "source_excerpt",
        "proposed_grade",
        "reviewed_grade",
        "judgment_status",
        "reviewer_id",
        "reviewed_at",
        "judgment_rationale",
        "adjudication_notes",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for item in pooled_items:
            writer.writerow([
                item.case_id,
                item.query,
                item.query_category,
                item.evidence_id,
                item.evidence_type,
                item.source_record_id,
                ";".join(item.retrieval_channels),
                str(item.baseline_rank) if item.baseline_rank is not None else "",
                str(item.graph_rank) if item.graph_rank is not None else "",
                item.source_excerpt,
                str(item.proposed_grade) if item.proposed_grade is not None else "",
                str(item.reviewed_grade) if item.reviewed_grade is not None else "",
                item.judgment_status,
                item.reviewer_id or "",
                item.reviewed_at or "",
                item.judgment_rationale,
                item.adjudication_notes,
            ])
