"""
MediScanAI — Phase D.1: OCR-to-Retrieval Pipeline & Evaluator

Implements Section 8 Requirements:
1. Separate raw OCR output from normalized search representation.
2. Structured entity extraction from OCR tokens: brand names, ingredients, strengths (e.g. 500mg), dosage forms (tablet, syrup).
3. Ambiguity and uncertainty communication for blurry/low-confidence labels.
4. Product identification intent resolution for OCR-only submissions (zero user text).
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from evaluation.retrieval.phase_d_1.medical_tokenizer import MedicalTokenizer, DOSAGE_PATTERN


# Standard pharmaceutical dosage forms
DOSAGE_FORMS = [
    "tablet", "tablets", "tab", "tabs",
    "capsule", "capsules", "cap", "caps",
    "syrup", "suspension", "solution", "elixir",
    "injection", "injectable", "vial", "ampoule",
    "cream", "ointment", "gel", "lotion",
    "inhaler", "spray", "drops", "patch", "suppository",
]

# Common pharmaceutical manufacturing/distributor terms to discount as drug names
EXCLUDE_TERMS = {
    "pharma", "pharmaceuticals", "laboratories", "labs", "ltd", "inc", "corp",
    "mfg", "lic", "exp", "mfg date", "batch", "lot", "b.no", "mrp", "rs",
    "keep out of reach of children", "store in a cool dry place", "rx only", "schedule h",
}


class MedicalOCRExtractor:
    """Extracts structured pharmaceutical features from raw OCR token lists."""

    @classmethod
    def parse_ocr_tokens(cls, tokens: List[str]) -> Dict[str, Any]:
        raw_lines = [t.strip() for t in tokens if t and t.strip()]
        full_text = " ".join(raw_lines)

        # 1. Extract dosage strengths
        strengths = MedicalTokenizer.extract_dosage_entities(full_text)

        # 2. Extract dosage forms
        found_forms = []
        lower_full = full_text.lower()
        for form in DOSAGE_FORMS:
            if re.search(r"\b" + re.escape(form) + r"\b", lower_full):
                found_forms.append(form)

        # 3. Candidate medicine names (filter out common packaging/legal boilerplate)
        candidate_names = []
        for line in raw_lines:
            line_clean = line.strip()
            line_lower = line_clean.lower()
            if any(term in line_lower for term in EXCLUDE_TERMS):
                continue
            # Must contain letters and have length >= 3
            if len(line_clean) >= 3 and re.search(r"[a-zA-Z]", line_clean):
                # Clean punctuation from edges
                cleaned_word = re.sub(r"^[^\w]+|[^\w]+$", "", line_clean)
                if len(cleaned_word) >= 3:
                    candidate_names.append(cleaned_word)

        # 4. Confidence / Readability assessment
        total_chars = sum(len(t) for t in raw_lines)
        alpha_chars = sum(len(re.findall(r"[a-zA-Z]", t)) for t in raw_lines)
        alpha_ratio = (alpha_chars / total_chars) if total_chars > 0 else 0.0

        is_readable = len(candidate_names) > 0 and alpha_ratio >= 0.50
        uncertainty_note = None
        if not is_readable:
            uncertainty_note = "Image text is partially unreadable, truncated, or lacks recognizable pharmaceutical identifiers."

        return {
            "raw_text": full_text,
            "normalized_search_text": MedicalTokenizer.normalize_whitespace_and_case(full_text),
            "candidate_names": candidate_names[:4],
            "strengths": list(dict.fromkeys(strengths)),
            "dosage_forms": list(dict.fromkeys(found_forms)),
            "is_readable": is_readable,
            "readability_score": round(alpha_ratio, 3),
            "uncertainty_note": uncertainty_note,
        }

    @classmethod
    def build_targeted_search_queries(cls, parsed_ocr: Dict[str, Any]) -> List[str]:
        """
        Builds ranked search queries from OCR features:
        1. Primary Brand/Name candidate + Strength (e.g. 'Lipitor 10mg')
        2. Primary Name alone (e.g. 'Lipitor')
        3. Normalized full search text
        """
        queries = []
        names = parsed_ocr.get("candidate_names", [])
        strengths = parsed_ocr.get("strengths", [])

        if names:
            primary_name = names[0]
            if strengths:
                queries.append(f"{primary_name} {strengths[0]}")
            queries.append(primary_name)
            if len(names) > 1:
                queries.append(names[1])

        norm_text = parsed_ocr.get("normalized_search_text", "")
        if norm_text and norm_text not in queries:
            queries.append(norm_text)

        return queries
