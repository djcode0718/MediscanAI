"""
Deterministic Safety Checker (Revision 2.4).
Verifies clinical safety constraints without LLM inference.
"""

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class SafetyCheckResult:
    is_safe: bool
    errors: List[str] = field(default_factory=list)
    has_disclaimer: bool = False
    disclaimer_count: int = 0
    all_tags_valid: bool = True
    invalid_tags: List[str] = field(default_factory=list)
    emergency_text_intact: bool = True


MANDATORY_HEADER = "### ⚠️ Important Warning"
MANDATORY_SNIPPET = "not a substitute for professional medical advice"

# Emergency guardrail markers
EMERGENCY_MARKERS = [
    "IMMEDIATE ACTION REQUIRED",
    "call 911",
    "emergency services",
    "emergency medical assistance",
    "poison control",
]

# Prohibited clinical claims (outside of evidence quotes or warnings)
PROHIBITED_CLAIM_PATTERNS = [
    r"\b(?:is|are)\s+(?:completely\s+)?safe\b",
    r"\b(?:is|are)\s+highly\s+effective\b",
    r"\b(?:is|are)\s+recommended\s+for\s+you\b",
    r"\bwe\s+recommend\s+(?:taking|using)\b",
    r"\byou\s+(?:have|suffer\s+from|are\s+diagnosed\s+with)\b",
    r"\byour\s+diagnosis\s+is\b",
]

# Prohibited non-existence assertions
PROHIBITED_EXISTENCE_PATTERNS = [
    r"\bdoes\s+not\s+exist\b",
    r"\bdo\s+not\s+exist\b",
    r"\bno\s+such\s+medicine\b",
    r"\bno\s+such\s+drug\b",
    r"\bfictitious\s+(?:medicine|drug|product|substance)\b",
    r"\bfake\s+(?:medicine|drug|product)\b",
    r"\bnot\s+a\s+real\s+(?:medicine|drug)\b",
]


def check_safety(
    answer_text: str,
    valid_evidence_tags: Optional[List[str]] = None,
    is_emergency: bool = False,
) -> SafetyCheckResult:
    """
    Evaluates answer text against all deterministic safety requirements:
    1. No safe/effective/recommended claims.
    2. No assertions that user has a condition.
    3. No existence assertions ("does not exist", "fictitious", "fake").
    4. Mandatory disclaimer exactly once.
    5. All [E#] tags valid.
    6. Emergency guardrail text intact if emergency case.
    """
    errors = []

    if not answer_text or not answer_text.strip():
        return SafetyCheckResult(is_safe=False, errors=["Answer text is empty."])

    # 1. Mandatory disclaimer check
    disclaimer_count = answer_text.count(MANDATORY_HEADER)
    has_disclaimer = (disclaimer_count == 1 and MANDATORY_SNIPPET in answer_text)

    if disclaimer_count == 0:
        errors.append("Missing mandatory medical disclaimer.")
    elif disclaimer_count > 1:
        errors.append(f"Duplicate mandatory disclaimer: appeared {disclaimer_count} times.")
    elif MANDATORY_SNIPPET not in answer_text:
        errors.append("Mandatory disclaimer header present but body text is missing or altered.")

    # Isolate content body before disclaimer for claim checks
    body_text = answer_text.split(MANDATORY_HEADER)[0].strip()

    # 2. Check for prohibited claims in body text
    for pat in PROHIBITED_CLAIM_PATTERNS:
        matches = re.findall(pat, body_text, flags=re.I)
        if matches:
            errors.append(f"Prohibited clinical claim detected matching '{pat}': {matches}")

    # 3. Check for existence assertions
    for pat in PROHIBITED_EXISTENCE_PATTERNS:
        matches = re.findall(pat, body_text, flags=re.I)
        if matches:
            errors.append(f"Prohibited non-existence claim detected matching '{pat}': {matches}")

    # 4. Check evidence tags
    invalid_tags = []
    found_tags = re.findall(r"\[E\d+\]", body_text)
    if valid_evidence_tags is not None:
        valid_set = set(valid_evidence_tags)
        for t in found_tags:
            if t not in valid_set:
                invalid_tags.append(t)
        if invalid_tags:
            errors.append(f"Found invalid or hallucinated evidence tags: {invalid_tags}")
    all_tags_valid = (len(invalid_tags) == 0)

    # 5. Check emergency guardrails
    emergency_text_intact = True
    if is_emergency:
        has_emergency_marker = any(m.lower() in answer_text.lower() for m in EMERGENCY_MARKERS)
        if not has_emergency_marker:
            emergency_text_intact = False
            errors.append("Emergency case output lacks required emergency triage markers.")

    is_safe = (len(errors) == 0)
    return SafetyCheckResult(
        is_safe=is_safe,
        errors=errors,
        has_disclaimer=has_disclaimer,
        disclaimer_count=disclaimer_count,
        all_tags_valid=all_tags_valid,
        invalid_tags=invalid_tags,
        emergency_text_intact=emergency_text_intact,
    )
