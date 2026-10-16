"""
MediScanAI — Phase D.2.b: Section-Aware Passage Reranker & Long-Document Bias Compensator

Implements:
1. Section-aware passage scoring: Scores distinct package-insert sections
   (active ingredients, indications, warnings, dosage, adverse reactions)
   with intent-adaptive weighting.
2. Long-document bias compensation via Section Max-Pooling:
   Score = max(section_scores) to prevent 4,500-token inserts from diluting
   exact active substance or indication matches.
3. Strict provenance tracking: Retains source record ID, winning section, and excerpt.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional

import numpy as np


@dataclass
class RerankedPassage:
    key: str
    record_id: int
    score: float
    best_section: str
    section_scores: Dict[str, float]
    excerpt: str
    record_obj: Dict[str, Any]
    provenance: Dict[str, Any] = field(default_factory=dict)


class SectionAwareReranker:
    """
    Reranks candidate documents by evaluating discrete clinical sections
    rather than monolithic document concatenations.
    """

    def __init__(self, cross_encoder_model):
        self.model = cross_encoder_model

    def extract_drug_sections(self, record: Dict[str, Any]) -> Dict[str, str]:
        """Extracts available structured sections from an FDA drug record."""
        sections = {}

        # 1. Product Metadata / Identity
        bname = record.get("brand_name") or ""
        gname = record.get("generic_name") or ""
        raw_subs = record.get("substance_name", [])
        subs_str = ", ".join(raw_subs) if isinstance(raw_subs, list) else str(raw_subs or "")
        meta_parts = []
        if bname:
            meta_parts.append(f"Brand Name: {bname}")
        if gname:
            meta_parts.append(f"Generic Name: {gname}")
        if subs_str:
            meta_parts.append(f"Active Substance: {subs_str}")
        sections["metadata"] = "\n".join(meta_parts) if meta_parts else "Product Identity: Unknown"

        # 2. Indications and Usage
        usage = record.get("indications_and_usage")
        if usage and usage != "unknown" and len(usage.strip()) > 10:
            sections["indications_and_usage"] = f"Indications and Usage: {usage.strip()}"

        # 3. Dosage and Administration
        dosage = record.get("dosage_and_administration")
        if dosage and dosage != "unknown" and len(dosage.strip()) > 10:
            sections["dosage_and_administration"] = f"Dosage and Administration: {dosage.strip()}"

        # 4. Warnings and Precautions
        warnings = record.get("warnings_and_cautions")
        if warnings and warnings != "unknown" and len(warnings.strip()) > 10:
            sections["warnings_and_cautions"] = f"Warnings and Cautions: {warnings.strip()}"

        # 5. Adverse Reactions
        adverse = record.get("adverse_reactions")
        if adverse and adverse != "unknown" and len(adverse.strip()) > 10:
            sections["adverse_reactions"] = f"Adverse Reactions: {adverse.strip()}"

        return sections

    def rerank_candidates(
        self,
        query_text: str,
        candidates: List[Tuple[str, float, Dict[str, Any]]],
        intent: str = "general",
        mode: str = "section_maxpool",  # "monolithic", "section_intent_weighted", "section_maxpool"
        threshold: Optional[float] = None,
    ) -> List[RerankedPassage]:
        """
        Reranks a candidate pool using section-aware scoring.
        """
        if not candidates:
            return []

        reranked_passages: List[RerankedPassage] = []

        # Prepare evaluation pairs
        pairs_to_predict: List[Tuple[str, str]] = []
        item_section_map: List[Tuple[int, str]] = []  # (cand_idx, section_name)

        for c_idx, (key, base_score, obj) in enumerate(candidates):
            if "chunk" in obj:
                # Disease record
                d = obj.get("chunk", {}).get("disease", "")
                syms = ", ".join(obj.get("chunk", {}).get("symptoms", [])[:6])
                text = f"Disease: {d}\nSymptoms: {syms}"
                pairs_to_predict.append((query_text, text))
                item_section_map.append((c_idx, "disease_chunk"))
            elif "drug_name" in obj and "indications_and_usage" not in obj:
                # drug_dict entry
                text = f"Drug Name: {obj.get('drug_name', '')}"
                pairs_to_predict.append((query_text, text))
                item_section_map.append((c_idx, "drug_dict"))
            else:
                # Drug record with sections
                sections = self.extract_drug_sections(obj)
                for sec_name, sec_text in sections.items():
                    pairs_to_predict.append((query_text, sec_text))
                    item_section_map.append((c_idx, sec_name))

        # Predict batch scores with cross-encoder
        raw_scores = self.model.predict(pairs_to_predict)

        # Collate scores per candidate
        cand_scores: Dict[int, Dict[str, float]] = {}
        for (c_idx, sec_name), sc in zip(item_section_map, raw_scores):
            cand_scores.setdefault(c_idx, {})[sec_name] = float(sc)

        # Score aggregation based on experimental mode
        for c_idx, (key, base_score, obj) in enumerate(candidates):
            scores_by_sec = cand_scores.get(c_idx, {})
            if not scores_by_sec:
                continue

            rec_id = int(obj.get("id", 0))

            if "disease_chunk" in scores_by_sec:
                final_score = scores_by_sec["disease_chunk"]
                best_sec = "disease_chunk"
                excerpt = f"Disease: {obj.get('chunk', {}).get('disease', '')}"
            elif "drug_dict" in scores_by_sec:
                final_score = scores_by_sec["drug_dict"]
                best_sec = "drug_dict"
                excerpt = f"Drug Dict: {obj.get('drug_name', '')}"
            else:
                # Drug record
                if mode == "section_maxpool":
                    # Max-pooling: winner takes all, immune to document length bias
                    best_sec = max(scores_by_sec, key=scores_by_sec.get)
                    final_score = scores_by_sec[best_sec]
                elif mode == "section_intent_weighted":
                    # Intent-guided section weighting
                    if intent == "drug_purpose_indications":
                        weights = {"indications_and_usage": 1.5, "metadata": 1.0, "warnings_and_cautions": 0.5}
                    elif intent in ["brand_lookup", "generic_lookup", "active_ingredient_lookup"]:
                        weights = {"metadata": 2.0, "indications_and_usage": 0.5}
                    else:
                        weights = {"metadata": 1.2, "indications_and_usage": 1.0}

                    weighted_sum = 0.0
                    total_w = 0.0
                    for s_name, s_val in scores_by_sec.items():
                        w = weights.get(s_name, 0.5)
                        weighted_sum += w * s_val
                        total_w += w
                    final_score = weighted_sum / total_w if total_w > 0 else list(scores_by_sec.values())[0]
                    best_sec = max(scores_by_sec, key=scores_by_sec.get)
                else:
                    # Default: metadata score
                    best_sec = "metadata"
                    final_score = scores_by_sec.get("metadata", list(scores_by_sec.values())[0])

                sections_text = self.extract_drug_sections(obj)
                excerpt = sections_text.get(best_sec, "")[:200]

            passage = RerankedPassage(
                key=key,
                record_id=rec_id,
                score=final_score,
                best_section=best_sec,
                section_scores=scores_by_sec,
                excerpt=excerpt,
                record_obj=obj,
                provenance={
                    "record_id": rec_id,
                    "winning_section": best_sec,
                    "section_score": scores_by_sec.get(best_sec),
                    "aggregation_mode": mode,
                },
            )
            reranked_passages.append(passage)

        reranked_passages.sort(key=lambda p: p.score, reverse=True)

        if threshold is not None:
            reranked_passages = [p for p in reranked_passages if p.score >= threshold]

        return reranked_passages
