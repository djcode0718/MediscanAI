"""
Deterministic Abstention Checker (Revision 2.4).
Verifies canonical abstention compliance for unanswerable queries without LLM inference.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AbstentionCheckResult:
    is_valid_abstention: bool
    errors: List[str] = field(default_factory=list)
    has_canonical_abstention: bool = False
    has_entity_echo: bool = False
    has_duplicated_sentences: bool = False
    has_existence_claims: bool = False


CANONICAL_ABSTENTION_PATTERNS = [
    r"could\s+not\s+be\s+verified\s+from\s+the\s+available\s+sources",
    r"available\s+(?:clinical\s+)?sources\s+do\s+not\s+state",
    r"not\s+stated\s+in\s+the\s+available\s+sources",
    r"the\s+medicine\s+could\s+not\s+be\s+identified",
    r"not\s+applicable",
]

EXISTENCE_CLAIM_PATTERNS = [
    r"\bdoes\s+not\s+exist\b",
    r"\bdo\s+not\s+exist\b",
    r"\bno\s+such\s+(?:medicine|drug|product)\b",
    r"\bfictitious\b",
    r"\bfake\b",
    r"\bnot\s+a\s+real\b",
]


def check_abstention(
    answer_text: str,
    query_entity_name: Optional[str] = None,
    user_text: Optional[str] = None,
    ocr_text: Optional[str] = None,
) -> AbstentionCheckResult:
    """
    Evaluates unanswerable inquiry outputs:
    1. Canonical abstention phrasing present.
    2. No echo of query's entity name in negative claims or explanation.
    3. No duplicated sentences.
    4. No non-existence claims.
    """
    errors = []

    if not answer_text or not answer_text.strip():
        return AbstentionCheckResult(is_valid_abstention=False, errors=["Empty answer text."])

    # Isolate content body before disclaimer
    body = answer_text.split("### ⚠️ Important Warning")[0].strip()

    # 1. Canonical abstention check
    has_canonical = any(re.search(pat, body, flags=re.I) for pat in CANONICAL_ABSTENTION_PATTERNS)
    if not has_canonical:
        errors.append("Output lacks canonical grounded abstention phrasing.")

    # 2. Check for echo of query's entity name
    entities_to_check = set()
    if query_entity_name and len(query_entity_name.strip()) >= 3:
        entities_to_check.add(query_entity_name.strip())

    # Extract potential entity candidates from user_text / ocr_text
    if user_text:
        # Check for quoted names or distinctive drug-like tokens
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", user_text)
        for q in quoted:
            if len(q.strip()) >= 4:
                entities_to_check.add(q.strip())

    has_echo = False
    for ent in entities_to_check:
        # Ignore common non-entity stopwords
        if ent.lower() in ("pill", "container", "label", "medicine", "medication", "dose", "tablet"):
            continue
        # Check if entity appears in body (case-insensitive word boundary)
        if re.search(rf"\b{re.escape(ent)}\b", body, flags=re.I):
            has_echo = True
            errors.append(f"Entity echo detected: output mentions query entity '{ent}' in abstention.")

    # 3. Check for duplicated sentences
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", body) if len(s.strip()) > 10]
    seen_sentences = set()
    has_duplicates = False
    for s in sentences:
        norm_s = re.sub(r"[^\w\s]", "", s.lower()).strip()
        norm_s = re.sub(r"\s+", " ", norm_s)
        if norm_s in seen_sentences:
            has_duplicates = True
            errors.append(f"Duplicated sentence detected: '{s}'")
        seen_sentences.add(norm_s)

    # 4. Check for existence claims
    has_existence = False
    for pat in EXISTENCE_CLAIM_PATTERNS:
        matches = re.findall(pat, body, flags=re.I)
        if matches:
            has_existence = True
            errors.append(f"Prohibited non-existence claim detected: {matches}")

    is_valid = (len(errors) == 0)
    return AbstentionCheckResult(
        is_valid_abstention=is_valid,
        errors=errors,
        has_canonical_abstention=has_canonical,
        has_entity_echo=has_echo,
        has_duplicated_sentences=has_duplicates,
        has_existence_claims=has_existence,
    )
