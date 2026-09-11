#!/usr/bin/env python3
"""MediScanAI 2.0 — v3.4 precision-first scoring and formulation compatibility."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from rapidfuzz import fuzz
from normalization import parse_intervention

@dataclass
class MatchVerdict:
    status: str; method: str; canonical_drug_id: Optional[str]; all_canonical_ids: List[str]
    matched_fda_name: Optional[str]; confidence: float; margin: float; features: Dict[str, object]


def idf_weighted_overlap(q_tokens:Set[str], c_tokens:Set[str], token_idf:Dict[str,float])->float:
    if not q_tokens: return 0.0
    total=sum(token_idf.get(t,1.0) for t in q_tokens)
    return sum(token_idf.get(t,1.0) for t in q_tokens & c_tokens)/max(total,1e-9)


def _strength_compatibility(q, c)->str:
    """Return compatible / mismatch / query_unspecified / candidate_unspecified / dimension_mismatch."""
    qs=[x for x in q.strength_values if x.get("value") is not None]
    cs=[x for x in c.strength_values if x.get("value") is not None]
    # FDA names may encode formulation strength as a bare number.
    if not cs and c.bare_strengths: cs=[{"value":v,"dimension":"concentration","unit":"bare"} for v in c.bare_strengths]
    if not qs: return "query_unspecified"
    if not cs: return "candidate_unspecified"
    # Compare concentration strengths. Other dimensions are only compatible if exact same dimension/unit/value.
    for qv in qs:
        matched=False
        for cv in cs:
            if qv["dimension"] != cv["dimension"] and not ({qv["dimension"],cv["dimension"]} <= {"concentration","concentration_mass_volume"}):
                continue
            if abs(float(qv["value"])-float(cv["value"])) <= max(1e-9, 1e-6*max(abs(float(qv["value"])),abs(float(cv["value"])),1.0)):
                matched=True; break
        if not matched: return "mismatch"
    return "compatible"


def evaluate_candidate(query_parsed,candidate_name,cand_normalized,cand_compact,cand_tokens,cand_identifiers,cand_radiolabels,token_idf,candidate_strengths=None,candidate_bare_strengths=None):
    q=query_parsed
    c = parse_intervention(candidate_name, candidate_mode=True) if candidate_strengths is None else None
    c_strengths = candidate_strengths if candidate_strengths is not None else c.strength_values
    c_bare = candidate_bare_strengths if candidate_bare_strengths is not None else c.bare_strengths
    class C: pass
    cp=C(); cp.strength_values=c_strengths; cp.bare_strengths=c_bare
    strength_status=_strength_compatibility(q,cp)
    ratio=fuzz.ratio(q.normalized,cand_normalized)/100; token_sort=fuzz.token_sort_ratio(q.normalized,cand_normalized)/100; token_set=fuzz.token_set_ratio(q.normalized,cand_normalized)/100
    compact_ratio=fuzz.ratio(q.compact,cand_compact)/100
    overlap=idf_weighted_overlap(q.tokens,cand_tokens,token_idf)
    inter=q.tokens & cand_tokens; qcov=len(inter)/max(len(q.tokens),1); ccov=len(inter)/max(len(cand_tokens),1)
    shared=bool(set(q.identifiers)&set(cand_identifiers))
    qr=set(q.radiolabels); cr=set(cand_radiolabels); radio=bool(qr and cr and not(qr&cr)) or bool((qr and not cr) or (cr and not qr))
    score=.25*ratio+.15*token_sort+.15*token_set+.30*overlap+.15*compact_ratio
    # Shared identifier is strong evidence, but never overrides conflicting strength/isotope evidence.
    if shared: score=max(score,.94)
    if strength_status=="mismatch": score=min(score,.55)
    return {"composite_score":round(score,4),"ratio":round(ratio,4),"token_sort":round(token_sort,4),"weighted_overlap":round(overlap,4),"compact_ratio":round(compact_ratio,4),"query_coverage":round(qcov,4),"cand_coverage":round(ccov,4),"shared_code":1.0 if shared else 0.0,"radio_mismatch":1.0 if radio else 0.0,"strength_status":strength_status,"query_measurements":q.measurements,"candidate_measurements":[x.get("raw") for x in c_strengths],"candidate_bare_strengths":c_bare}


def classify_match(q, scored, fda_records, min_high_score=.88,min_med_score=.82,high_margin=.06,med_margin=.08):
    if not scored: return MatchVerdict("unresolved","no_candidates",None,[],None,0,0,{})
    best_name,b= scored[0]; second=scored[1][1]["composite_score"] if len(scored)>1 else 0; margin=round(b["composite_score"]-second,4); conf=b["composite_score"]; ids=fda_records.get(best_name,[])
    def v(status,method,confidence=None,allids=ids): return MatchVerdict(status,method,allids[0] if status.startswith("resolved") and len(allids)==1 else None,allids,best_name,round(confidence if confidence is not None else conf,4),margin,b)
    if b["radio_mismatch"]: return v("unresolved","radiolabel_mismatch")
    if b["strength_status"]=="mismatch": return v("unresolved","strength_mismatch")
    if q.is_combination and b["ratio"]<.95 and not b["shared_code"]: return v("unresolved","unresolved_combination_regimen")
    if q.retention_ratio<.40 and not b["shared_code"]: return v("unresolved","failed_retention_safeguard")
    if len(q.tokens)==1 and b["ratio"]<.90 and not b["shared_code"]: return v("unresolved","single_token_low_similarity")
    # Exact normalized text is only high confidence when formulation evidence does not conflict.
    if b["ratio"]==1.0:
        if b["strength_status"]=="candidate_unspecified" and q.strength_values: return v("unresolved","measurement_missing_candidate")
        return v("resolved_high" if len(ids)==1 else "name_ambiguous","exact_normalized" if len(ids)==1 else "exact_normalized_multidrug",1.0)
    if b["shared_code"] and b["weighted_overlap"]>=.50 and b["strength_status"]!="mismatch": return v("resolved_high" if len(ids)==1 else "name_ambiguous","exact_identifier" if len(ids)==1 else "exact_identifier_multidrug",.98)
    if b["compact_ratio"]==1.0 and b["weighted_overlap"]>=.70 and b["strength_status"] not in {"mismatch","candidate_unspecified"}:
        return v("resolved_high" if len(ids)==1 else "name_ambiguous","compact_exact" if len(ids)==1 else "compact_exact_multidrug",.95)
    if margin < high_margin/2 and conf>=min_med_score: return v("query_ambiguous","low_candidate_margin")
    if conf>=min_high_score and margin>=high_margin and b["ratio"]>=.80 and b["query_coverage"]>=.75 and b["weighted_overlap"]>=.70 and b["strength_status"] not in {"mismatch","candidate_unspecified"}:
        return v("resolved_high" if len(ids)==1 else "name_ambiguous","fuzzy_high" if len(ids)==1 else "fuzzy_high_multidrug")
    if conf>=min_med_score and margin>=med_margin and b["ratio"]>=.75 and b["query_coverage"]>=.65 and b["weighted_overlap"]>=.60 and b["strength_status"] not in {"mismatch"}:
        return v("resolved_medium" if len(ids)==1 else "name_ambiguous","fuzzy_medium" if len(ids)==1 else "fuzzy_medium_multidrug")
    return v("unresolved","below_confidence_gate",None,[])
