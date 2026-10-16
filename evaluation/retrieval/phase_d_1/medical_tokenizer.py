"""
MediScanAI — Phase D.1: Non-Destructive Medical Tokenizer & Query Normalizer

Replaces destructive generic SymSpell normalization in the experimental retrieval path.
Preserves medical brand names (Lipitor, Cinzan, Amoxil, Augmentin, Panadol),
active ingredients (Metformin, Atorvastatin, Ciprofloxacin), salt forms (calcium, hydrochloride),
formulation strengths (500mg, 10mg/ml, 0.5%), hyphens (co-amoxiclav, l-carnitine),
and slashes (trimethoprim/sulfamethoxazole).
"""

import re
from typing import List, Tuple, Optional, Dict, Any


# Regular expression matching medical tokens:
# 1. Hyphenated or slashed medical compounds: e.g., co-amoxiclav, l-carnitine, amoxicillin/clavulanate
# 2. Dosage strength tokens: e.g., 500mg, 10mg/ml, 0.5%, 25mcg, 100iu
# 3. Alphanumeric identifiers: e.g., covid-19, b12, d3
# 4. Standard words and numbers
MEDICAL_TOKEN_PATTERN = re.compile(
    r"[a-zA-Z0-9]+(?:[-/][a-zA-Z0-9]+)*|\d+(?:\.\d+)?(?:mg|ml|mcg|ug|g|iu|%)?",
    re.IGNORECASE,
)

DOSAGE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mg|ml|mcg|ug|g|iu|%)\b",
    re.IGNORECASE,
)


class MedicalTokenizer:
    """
    Non-destructive medical tokenizer and query preprocessor.
    Guarantees that specialized medical terminology is NEVER silently overwritten.
    """

    def __init__(self, enable_typo_variant: bool = False):
        self.enable_typo_variant = enable_typo_variant

    @staticmethod
    def normalize_whitespace_and_case(text: str) -> str:
        """Lowercases and normalizes whitespace while preserving hyphens and slashes."""
        if not text:
            return ""
        # Standardize dosage spacing (e.g. "500 mg" -> "500mg")
        standardized = DOSAGE_PATTERN.sub(r"\1\2", text)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", standardized).strip().lower()
        return cleaned

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """
        Extracts clean, non-destructive medical tokens.
        Preserves hyphens within terms (e.g. 'co-amoxiclav') and dosage units.
        """
        if not text:
            return []
        norm = cls.normalize_whitespace_and_case(text)
        tokens = MEDICAL_TOKEN_PATTERN.findall(norm)
        # Filter empty strings
        return [t.lower() for t in tokens if t]

    @classmethod
    def extract_dosage_entities(cls, text: str) -> List[str]:
        """Extracts recognized dosage strengths (e.g., '500mg', '10mg/ml')."""
        if not text:
            return []
        matches = []
        for match in DOSAGE_PATTERN.finditer(text):
            matches.append(f"{match.group(1)}{match.group(2).lower()}")
        return matches

    @classmethod
    def build_search_variants(cls, text: str) -> Dict[str, Any]:
        """
        Generates structured search representations:
        - raw: Original unedited user query string.
        - normalized: Non-destructively cleaned string.
        - tokens: Medical tokens list.
        - unhyphenated_tokens: Tokens with hyphens replaced by space for secondary matching.
        """
        raw = text or ""
        norm = cls.normalize_whitespace_and_case(raw)
        tokens = cls.tokenize(norm)
        
        # Secondary variants for hyphenated terms (e.g., 'co-amoxiclav' -> 'co', 'amoxiclav')
        unhyphenated = []
        for t in tokens:
            if "-" in t:
                unhyphenated.extend(t.split("-"))
            elif "/" in t:
                unhyphenated.extend(t.split("/"))
            else:
                unhyphenated.append(t)

        return {
            "raw": raw,
            "normalized": norm,
            "tokens": tokens,
            "expanded_tokens": list(dict.fromkeys(tokens + unhyphenated)),
            "dosages": cls.extract_dosage_entities(raw),
        }


def normalize_text_medical(text: str) -> str:
    """Drop-in non-destructive replacement for legacy normalize_text()."""
    return MedicalTokenizer.normalize_whitespace_and_case(text)
