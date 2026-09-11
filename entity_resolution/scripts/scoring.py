#!/usr/bin/env python3
"""
MediScanAI 2.0 — Evidence-Based Scoring & Confidence Classification Engine (v2.1).
Strict precision gates: rejects single-token leaks, protects against isotope mismatch,
and catches unresolved multi-component intervention combinations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from rapidfuzz import fuzz

@dataclass
class MatchVerdict:
    status: str
    method: str
    canonical_drug_id: Optional[str]
    all_canonical_ids: List[str]
    matched_fda_name: Optional[str]
    confidence: float
    margin: float
    features: Dict[str, float]


def idf_weighted_overlap(q_tokens: Set[str], c_tokens: Set[str], token_idf: Dict[str, float]) -> float:
    if not q_tokens:
        return 0.0
    total_idf = sum(token_idf.get(t, 1.0) for t in q_tokens)
    if total_idf <= 0.0:
        return 0.0
    shared_idf = sum(token_idf.get(t, 1.0) for t in (q_tokens & c_tokens))
    return shared_idf / total_idf


def evaluate_candidate(
    query_parsed,
    candidate_name: str,
    cand_normalized: str,
    cand_compact: str,
    cand_tokens: Set[str],
    cand_identifiers: List[str],
    cand_radiolabels: List[str],
    token_idf: Dict[str, float],
) -> Dict[str, float]:
    q_norm = query_parsed.normalized
    q_tokens = query_parsed.tokens

    ratio = fuzz.ratio(q_norm, cand_normalized) / 100.0
    token_sort = fuzz.token_sort_ratio(q_norm, cand_normalized) / 100.0
    token_set = fuzz.token_set_ratio(q_norm, cand_normalized) / 100.0
    compact_ratio = fuzz.ratio(query_parsed.compact, cand_compact) / 100.0

    weighted_overlap = idf_weighted_overlap(q_tokens, cand_tokens, token_idf)
    query_cov = (len(q_tokens & cand_tokens) / max(len(q_tokens), 1))
    cand_cov = (len(q_tokens & cand_tokens) / max(len(cand_tokens), 1))

    shared_code = bool(set(query_parsed.identifiers) & set(cand_identifiers))

    # Radiolabel Consistency Check (e.g. 177Lu vs 68Ga)
    q_radio = set(query_parsed.radiolabels)
    c_radio = set(cand_radiolabels)
    radio_mismatch = bool(q_radio and c_radio and not (q_radio & c_radio))

    composite_score = (
        0.25 * ratio +
        0.15 * token_sort +
        0.15 * token_set +
        0.30 * weighted_overlap +
        0.15 * compact_ratio
    )
    if shared_code:
        composite_score = max(composite_score, 0.96)

    return {
        "composite_score": round(composite_score, 4),
        "ratio": round(ratio, 4),
        "token_sort": round(token_sort, 4),
        "weighted_overlap": round(weighted_overlap, 4),
        "compact_ratio": round(compact_ratio, 4),
        "query_coverage": round(query_cov, 4),
        "cand_coverage": round(cand_cov, 4),
        "shared_code": 1.0 if shared_code else 0.0,
        "radio_mismatch": 1.0 if radio_mismatch else 0.0,
    }


def classify_match(
    query_parsed,
    scored_candidates: List[tuple],
    fda_records: Dict[str, List[str]],
    min_high_score: float = 0.88,
    min_med_score: float = 0.82,
    high_margin: float = 0.06,
    med_margin: float = 0.08,
) -> MatchVerdict:
    if not scored_candidates:
        return MatchVerdict(
            status="unresolved", method="no_candidates",
            canonical_drug_id=None, all_canonical_ids=[],
            matched_fda_name=None, confidence=0.0, margin=0.0, features={}
        )

    best_name, best_feats = scored_candidates[0]
    second_score = scored_candidates[1][1]["composite_score"] if len(scored_candidates) > 1 else 0.0
    margin = round(best_feats["composite_score"] - second_score, 4)
    confidence = best_feats["composite_score"]

    ids = fda_records.get(best_name, [])

    # Guard 1: Multi-component intervention without matching combination in FDA
    if query_parsed.is_combination and best_feats["ratio"] < 0.95 and not best_feats["shared_code"]:
        return MatchVerdict(
            status="unresolved", method="unresolved_combination_regimen",
            canonical_drug_id=None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # Guard 2: Radiolabel Isotope Mismatch (e.g. 177Lu cannot match 68Ga)
    if best_feats["radio_mismatch"] == 1.0:
        return MatchVerdict(
            status="unresolved", method="radiolabel_mismatch",
            canonical_drug_id=None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # Guard 3: Query Information Retention Violation
    if query_parsed.retention_ratio < 0.40 and not best_feats["shared_code"]:
        return MatchVerdict(
            status="unresolved", method="failed_retention_safeguard",
            canonical_drug_id=None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # Guard 4: Weak Single-Token Match
    if len(query_parsed.tokens) == 1 and best_feats["ratio"] < 0.90 and not best_feats["shared_code"]:
        return MatchVerdict(
            status="unresolved", method="single_token_low_similarity",
            canonical_drug_id=None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # 1. Exact Match
    if best_feats["ratio"] == 1.0:
        status = "resolved_high" if len(ids) == 1 else "name_ambiguous"
        method = "exact_normalized" if len(ids) == 1 else "exact_normalized_multidrug"
        return MatchVerdict(
            status=status, method=method,
            canonical_drug_id=ids[0] if len(ids) == 1 else None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=1.0, margin=margin, features=best_feats
        )

    # 2. Exact Alphanumeric Identifier Match
    if best_feats["shared_code"] == 1.0 and best_feats["weighted_overlap"] >= 0.50:
        status = "resolved_high" if len(ids) == 1 else "name_ambiguous"
        method = "exact_identifier" if len(ids) == 1 else "exact_identifier_multidrug"
        return MatchVerdict(
            status=status, method=method,
            canonical_drug_id=ids[0] if len(ids) == 1 else None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=0.98, margin=margin, features=best_feats
        )

    # 3. Compact Match
    if best_feats["compact_ratio"] == 1.0 and best_feats["weighted_overlap"] >= 0.70:
        status = "resolved_high" if len(ids) == 1 else "name_ambiguous"
        method = "compact_exact" if len(ids) == 1 else "compact_exact_multidrug"
        return MatchVerdict(
            status=status, method=method,
            canonical_drug_id=ids[0] if len(ids) == 1 else None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=0.95, margin=margin, features=best_feats
        )

    # Guard 5: Low Candidate Margin (Competing FDA entries)
    if margin < (high_margin / 2.0) and confidence >= min_med_score:
        return MatchVerdict(
            status="query_ambiguous", method="low_candidate_margin",
            canonical_drug_id=None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # 4. Fuzzy High-Confidence Gate
    if (
        confidence >= min_high_score
        and margin >= high_margin
        and best_feats["ratio"] >= 0.80
        and best_feats["query_coverage"] >= 0.75
        and best_feats["weighted_overlap"] >= 0.70
    ):
        status = "resolved_high" if len(ids) == 1 else "name_ambiguous"
        method = "fuzzy_high" if len(ids) == 1 else "fuzzy_high_multidrug"
        return MatchVerdict(
            status=status, method=method,
            canonical_drug_id=ids[0] if len(ids) == 1 else None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # 5. Fuzzy Medium-Confidence Gate
    if (
        confidence >= min_med_score
        and margin >= med_margin
        and best_feats["ratio"] >= 0.75
        and best_feats["query_coverage"] >= 0.65
        and best_feats["weighted_overlap"] >= 0.60
    ):
        status = "resolved_medium" if len(ids) == 1 else "name_ambiguous"
        method = "fuzzy_medium" if len(ids) == 1 else "fuzzy_medium_multidrug"
        return MatchVerdict(
            status=status, method=method,
            canonical_drug_id=ids[0] if len(ids) == 1 else None, all_canonical_ids=ids,
            matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
        )

    # Unresolved fallback
    return MatchVerdict(
        status="unresolved", method="below_confidence_gate",
        canonical_drug_id=None, all_canonical_ids=[],
        matched_fda_name=best_name, confidence=confidence, margin=margin, features=best_feats
    )