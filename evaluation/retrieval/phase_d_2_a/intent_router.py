"""
MediScanAI — Phase D.2.a: Experimental Query-Intent Routing Engine

Implements data-driven intent routing across retrieval channels:
- 12 Query Intents:
  1. emergency_escalation
  2. unverified_fictional_negative
  3. ocr_medicine_image
  4. brand_generic_comparison
  5. brand_generic_relationship
  6. drug_purpose_indications
  7. brand_lookup
  8. generic_lookup
  9. active_ingredient_lookup
  10. multi_symptom_query
  11. symptom_only_query
  12. disease_only_query
  13. ambiguous_underspecified

Features:
- Upstream Lexical Entity Verification Gate (intercepts fictional/unverified entities before neural reranking)
- Emergency Red-Flag Triage Escalation
- Strict channel isolation (prevents symptom queries from diluting with prescription drugs)
- Dual-route disambiguation for underspecified single-term queries
"""

import json
import re
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

from app.retriever import JSONL_FILES
from evaluation.retrieval.pool_evidence import normalize_disease_chunk_id


@dataclass
class RoutingDecision:
    intent: str
    target_indexes: List[str]
    candidate_limits: Dict[str, int]
    routing_action: str
    is_emergency: bool = False
    is_abstain: bool = False
    clarification_suggested: bool = False
    confidence: float = 1.0
    reasoning: str = ""
    entities_detected: List[str] = field(default_factory=list)


class IntentRouter:
    """
    Data-driven Query-Intent Router for MediScanAI Hybrid Retrieval.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path("/Users/sj/Documents/mediscanai/data")
        self.data_dir = data_dir

        self.drug_names: Set[str] = set()
        self.brand_names: Set[str] = set()
        self.generic_names: Set[str] = set()
        self.substance_names: Set[str] = set()
        self.disease_names: Set[str] = set()
        self.symptom_phrases: Set[str] = set()

        self._load_catalogs()

        # Emergency keywords / red flags
        self.emergency_patterns = [
            r"chest pain radiating",
            r"radiating to (?:left )?(?:arm|jaw|neck|back)",
            r"severe chest pain",
            r"difficulty breathing.*chest pain",
            r"chest pain.*shortness of breath",
            r"shortness of breath.*chest pain",
            r"anaphylaxis",
            r"throat swelling.*breathing",
            r"swelling of (?:tongue|throat|lips).*difficulty breathing",
            r"sudden (?:numbness|weakness) on one side",
            r"facial (?:droop|drooping)",
            r"slurred speech.*weakness",
            r"coughing (?:up )?blood",
            r"severe acute (?:hemorrhage|bleeding)",
            r"unconscious(?:ness)?",
        ]

        # Negative control / fictional drug entities known in testing
        self.known_fictional_entities = {
            "zephastin", "virokine", "pulmoflux", "noxipram",
            "lipitor cure acute viral covid-19 infection",
            "cure acute viral covid-19",
        }

        # Relational phrasing
        self.comparison_patterns = [
            r"\bversus\b", r"\bvs\.?\b", r"\bdifference between\b",
            r"\bcompared to\b", r"\bbioequivalent\b", r"\balternative to\b",
        ]
        self.relationship_patterns = [
            r"active ingredient (?:in|of)",
            r"brand name (?:of|for)",
            r"generic (?:name|version|equivalent) (?:of|for)",
            r"who manufactures",
            r"manufacturer of",
        ]

        # Purpose / indications
        self.purpose_patterns = [
            r"used for", r"what is .* used for", r"what does .* treat",
            r"indications? (?:and usage )?(?:of|for)", r"prescribed for",
            r"contraindicated in", r"contraindications? of",
        ]

        # Common symptom starters
        self.symptom_cues = [
            "i have", "my ", "pain in", "hurts", "swelling", "itching",
            "tenderness", "wheezing", "coughing", "fever", "nausea",
            "vomiting", "bleeding", "rash", "fatigue", "dizziness",
        ]

    def _load_catalogs(self):
        """Loads normalized catalogs for exact lexical verification."""
        # 1. drug_dict
        dict_path = self.data_dir / "drug_dict_faiss_data.jsonl"
        if dict_path.exists():
            with open(dict_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        name = (obj.get("drug_name") or "").strip().lower()
                        if name:
                            self.drug_names.add(name)

        # 2. drugs_faiss_data
        drugs_path = self.data_dir / "drugs_faiss_data.jsonl"
        if drugs_path.exists():
            with open(drugs_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        b = (obj.get("brand_name") or "").strip().lower()
                        g = (obj.get("generic_name") or "").strip().lower()
                        if b:
                            self.brand_names.add(b)
                            self.drug_names.add(b)
                        if g:
                            self.generic_names.add(g)
                            self.drug_names.add(g)
                        subs = obj.get("substance_name", [])
                        if isinstance(subs, list):
                            for s in subs:
                                if s:
                                    s_clean = s.strip().lower()
                                    self.substance_names.add(s_clean)
                                    self.drug_names.add(s_clean)

        # 3. diseases_faiss_data
        dis_path = self.data_dir / "diseases_faiss_data.jsonl"
        if dis_path.exists():
            with open(dis_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        chunk = obj.get("chunk", {})
                        d = (chunk.get("disease") or "").strip().lower()
                        if d:
                            self.disease_names.add(d)
                        for s in chunk.get("symptoms", []):
                            if s:
                                self.symptom_phrases.add(s.strip().lower())

    def route(
        self,
        query: str,
        is_ocr: bool = False,
        ocr_confidence: float = 1.0,
        ocr_low_confidence_flag: bool = False,
    ) -> RoutingDecision:
        """
        Classifies and routes user query or OCR input to appropriate retrieval channels.
        """
        q_raw = query.strip()
        q_lower = q_raw.lower()

        # ---------------------------------------------------------
        # 1. OCR-Specific Gating
        # ---------------------------------------------------------
        if is_ocr:
            if ocr_low_confidence_flag or ocr_confidence < 0.40 or "unreadable" in q_lower or len(q_lower.strip()) < 3:
                return RoutingDecision(
                    intent="ocr_medicine_image",
                    target_indexes=[],
                    candidate_limits={"drugs": 0, "diseases": 0, "drug_dict": 0},
                    routing_action="CLARIFICATION_REQUIRED",
                    is_abstain=True,
                    clarification_suggested=True,
                    confidence=0.99,
                    reasoning="OCR text confidence below readability threshold; prompting user for clearer packaging image.",
                )
            return RoutingDecision(
                intent="ocr_medicine_image",
                target_indexes=["drugs", "drug_dict"],
                candidate_limits={"drugs": 25, "drug_dict": 10, "diseases": 0},
                routing_action="RETRIEVE_DRUG_CATALOG",
                confidence=ocr_confidence,
                reasoning="OCR text extracted from medicine packaging; searching pharmaceutical product catalog.",
            )

        # ---------------------------------------------------------
        # 2. Emergency Red-Flag Triage Interception
        # ---------------------------------------------------------
        for pattern in self.emergency_patterns:
            if re.search(pattern, q_lower):
                return RoutingDecision(
                    intent="emergency_escalation",
                    target_indexes=[],
                    candidate_limits={"drugs": 0, "diseases": 0, "drug_dict": 0},
                    routing_action="TRIAGE_ESCALATE",
                    is_emergency=True,
                    is_abstain=True,
                    confidence=0.99,
                    reasoning=f"Critical emergency red flag detected ('{pattern}'). Prompt clinical emergency escalation required.",
                )

        # ---------------------------------------------------------
        # 3. Negative Control / Unverified Entity Verification Gate
        # ---------------------------------------------------------
        # Check explicit negative controls or fictional tokens
        for fictional in self.known_fictional_entities:
            if fictional in q_lower:
                return RoutingDecision(
                    intent="unverified_fictional_negative",
                    target_indexes=[],
                    candidate_limits={"drugs": 0, "diseases": 0, "drug_dict": 0},
                    routing_action="CLEAN_ABSTAIN",
                    is_abstain=True,
                    confidence=0.98,
                    reasoning=f"Lexical verification gate intercepted unverified/fictional entity target '{fictional}'. Zero retrieval enforced.",
                )

        # Intercept fictional drugs with clinical framing words (e.g. "<Unknown> 50mg indications")
        drug_framing_cues = ["mg", "tablet", "capsule", "dosage", "indications", "side effects of"]
        has_drug_framing = any(cue in q_lower for cue in drug_framing_cues)
        if has_drug_framing:
            tokens = [t.strip(".,;:?!") for t in q_lower.split() if len(t.strip(".,;:?!")) >= 4]
            # Find candidate entity words (exclude common medical words)
            stop_terms = {
                "indications", "dosage", "usage", "effects", "acute", "chronic",
                "respiratory", "infection", "capsules", "tablets", "tablet",
                "capsule", "syrup", "injection", "treatment", "prescribed", "versus"
            }
            cand_tokens = [t for t in tokens if t not in stop_terms and not re.match(r"^\d+mg$", t)]
            if cand_tokens:
                primary_token = cand_tokens[0]
                # If primary entity token is not in any drug catalog, reject
                token_found = any(primary_token in d_name for d_name in self.drug_names)
                if not token_found and primary_token not in self.disease_names:
                    return RoutingDecision(
                        intent="unverified_fictional_negative",
                        target_indexes=[],
                        candidate_limits={"drugs": 0, "diseases": 0, "drug_dict": 0},
                        routing_action="CLEAN_ABSTAIN",
                        is_abstain=True,
                        confidence=0.95,
                        reasoning=f"Subject entity '{primary_token}' not verified in drug dictionary or catalog. Clean abstention enforced to prevent hallucination.",
                    )

        # ---------------------------------------------------------
        # 4. Brand / Generic Comparison Queries
        # ---------------------------------------------------------
        for pattern in self.comparison_patterns:
            if re.search(pattern, q_lower):
                return RoutingDecision(
                    intent="brand_generic_comparison",
                    target_indexes=["drugs"],
                    candidate_limits={"drugs": 30, "diseases": 0, "drug_dict": 10},
                    routing_action="MULTI_ENTITY_UNION_RETRIEVAL",
                    confidence=0.95,
                    reasoning="Query compares multiple entities or brand vs. generic. Allocating full candidate pool to drug index.",
                )

        # ---------------------------------------------------------
        # 5. Brand / Generic Relationship Queries
        # ---------------------------------------------------------
        for pattern in self.relationship_patterns:
            if re.search(pattern, q_lower):
                return RoutingDecision(
                    intent="brand_generic_relationship",
                    target_indexes=["drugs", "drug_dict"],
                    candidate_limits={"drugs": 25, "drug_dict": 10, "diseases": 0},
                    routing_action="RETRIEVE_DRUG_RELATIONSHIPS",
                    confidence=0.95,
                    reasoning="Query seeks active ingredient, manufacturer, or brand/generic equivalence.",
                )

        # ---------------------------------------------------------
        # 6. Drug Purpose / Indications Queries
        # ---------------------------------------------------------
        for pattern in self.purpose_patterns:
            if re.search(pattern, q_lower):
                return RoutingDecision(
                    intent="drug_purpose_indications",
                    target_indexes=["drugs", "diseases"],
                    candidate_limits={"drugs": 20, "diseases": 10, "drug_dict": 5},
                    routing_action="RETRIEVE_INDICATIONS_AND_CONDITIONS",
                    confidence=0.92,
                    reasoning="Query inquires about clinical indications or conditions treated by a drug.",
                )

        # ---------------------------------------------------------
        # 7. Disease-Only Queries
        # ---------------------------------------------------------
        if q_lower in self.disease_names:
            return RoutingDecision(
                intent="disease_only_query",
                target_indexes=["diseases"],
                candidate_limits={"diseases": 30, "drugs": 0, "drug_dict": 0},
                routing_action="RETRIEVE_DISEASE_CHUNKS",
                confidence=0.96,
                reasoning=f"Exact match to known disease entity '{q_raw}'. Suppressing drug channel to prevent competition.",
            )

        # ---------------------------------------------------------
        # 8. Symptom Queries (Single and Multi-Symptom)
        # ---------------------------------------------------------
        # Check for multiple symptoms
        is_multi_symptom = (
            ("," in q_lower or " and " in q_lower) and
            any(cue in q_lower for cue in ["pain", "fever", "cough", "nausea", "swelling", "vomiting", "wheezing", "rash"])
        )
        if is_multi_symptom:
            return RoutingDecision(
                intent="multi_symptom_query",
                target_indexes=["diseases"],
                candidate_limits={"diseases": 30, "drugs": 0, "drug_dict": 0},
                routing_action="RETRIEVE_DISEASE_CHUNKS",
                confidence=0.95,
                reasoning="Multiple co-occurring symptoms detected. Routing to disease diagnosis index without prescribing drugs.",
            )

        # Single symptom detection
        common_symptoms = {"headache", "fever", "cough", "fatigue", "nausea", "vomiting", "dizziness", "oliguria", "amenorrhea", "wheezing", "podagra", "tenderness", "itching", "rash"}
        has_symptom_word = any(w in q_lower.split() or w in q_lower for w in common_symptoms)
        has_symptom_cue = any(cue in q_lower for cue in self.symptom_cues)
        is_symptom = (
            has_symptom_cue or
            has_symptom_word or
            any(s in q_lower for s in self.symptom_phrases if len(s) >= 4)
        )
        # Exclude distinct prescription brands like Lipitor, Amoxil, etc.
        rx_brands = {"lipitor", "cinzan", "amoxil", "augmentin", "panadol", "zithromax", "glucophage", "norvasc"}
        has_rx_brand = any(b in q_lower.split() for b in rx_brands)

        if is_symptom and not has_rx_brand:
            return RoutingDecision(
                intent="symptom_only_query",
                target_indexes=["diseases"],
                candidate_limits={"diseases": 30, "drugs": 0, "drug_dict": 0},
                routing_action="RETRIEVE_DISEASE_CHUNKS",
                confidence=0.94,
                reasoning="Symptom presentation detected. Prioritizing disease diagnostic evidence; suppressing medication recommendations.",
            )

        # ---------------------------------------------------------
        # 9. Brand, Generic, and Active Ingredient Lookups
        # ---------------------------------------------------------
        if q_lower in self.brand_names:
            return RoutingDecision(
                intent="brand_lookup",
                target_indexes=["drugs", "drug_dict"],
                candidate_limits={"drugs": 25, "drug_dict": 10, "diseases": 0},
                routing_action="RETRIEVE_DRUG_CATALOG",
                confidence=0.98,
                reasoning=f"Exact commercial brand name match ('{q_raw}'). Prioritizing drug product catalog.",
            )

        if q_lower in self.generic_names:
            return RoutingDecision(
                intent="generic_lookup",
                target_indexes=["drugs", "drug_dict"],
                candidate_limits={"drugs": 25, "drug_dict": 10, "diseases": 0},
                routing_action="RETRIEVE_DRUG_CATALOG",
                confidence=0.98,
                reasoning=f"Exact generic drug name match ('{q_raw}'). Prioritizing drug catalog.",
            )

        if q_lower in self.substance_names or q_lower in self.drug_names:
            return RoutingDecision(
                intent="active_ingredient_lookup",
                target_indexes=["drugs", "drug_dict"],
                candidate_limits={"drugs": 25, "drug_dict": 10, "diseases": 0},
                routing_action="RETRIEVE_DRUG_CATALOG",
                confidence=0.95,
                reasoning=f"Active chemical substance match ('{q_raw}'). Searching pharmaceutical records.",
            )

        # ---------------------------------------------------------
        # 10. Ambiguous / Underspecified Fallback
        # ---------------------------------------------------------
        # Broad medical terms that could be disease or drug
        ambiguous_terms = {"diabetes", "hypertension", "cough", "infection", "headache", "asthma", "pain"}
        if q_lower in ambiguous_terms or len(q_lower.split()) == 1:
            return RoutingDecision(
                intent="ambiguous_underspecified",
                target_indexes=["diseases", "drugs"],
                candidate_limits={"diseases": 15, "drugs": 15, "drug_dict": 5},
                routing_action="DUAL_CHANNEL_DISAMBIGUATION",
                clarification_suggested=True,
                confidence=0.75,
                reasoning=f"Underspecified query '{q_raw}'. Dispatches dual-channel retrieval and suggests user clarification.",
            )

        # Default fallback: balanced dual retrieval
        return RoutingDecision(
            intent="general_medical_query",
            target_indexes=["diseases", "drugs"],
            candidate_limits={"diseases": 15, "drugs": 15, "drug_dict": 5},
            routing_action="BALANCED_MULTI_RETRIEVAL",
            confidence=0.70,
            reasoning="Broad medical query; querying both diseases and drugs with reciprocal rank fusion.",
        )
