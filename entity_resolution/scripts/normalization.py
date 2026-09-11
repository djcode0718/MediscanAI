#!/usr/bin/env python3
"""
MediScanAI 2.0 — Biomedical Text Normalization & Entity Representation (v2.3).
Lossless multi-representation parser preserving drug codes (5FU, 3TC, PF-04995274),
radiolabels, stereochemistry, combinations, and computing query retention.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Set

# 1. Radiolabels:
# Must be bracketed [89Zr], [11C], [123I] OR hyphenated: 11C-xxx, 177Lu-xxx, 68Ga-xxx, 90Y-xxx
# This prevents slicing 5FU into '5F' + 'U' or 3TC into '3T' + 'C'.
RADIOLABEL_RE = re.compile(
    r"\[\s*(\d{1,3}[A-Za-z]{1,2})\s*\][\s\-]*|\b(\d{1,3}[A-Za-z]{1,2})\s*-(?=[A-Za-z])",
    re.IGNORECASE
)

# 2. Stereochemical prefixes: (+)-, (-)-, (+/-)-, (±)-, (R)-, (S)-, dl-, etc.
STEREO_RE = re.compile(
    r"(?:\(\s*[+\-±/]+\s*\)|\b[dDlL]\b[\s\-]+|\(\s*[RSrs]\s*\)[\s\-]*|[+\-±]\s*[\-]\s*)",
    re.IGNORECASE
)

# 3. Known Alphanumeric Drug Development Identifiers & Standard Abbreviations
# e.g. 5FU, 3TC, PF-04995274, NX-1207, JNJ-42491293, SJ000557733
CODE_IDENTIFIER_RE = re.compile(
    r"\b(?:[A-Za-z]{1,4}-\d{3,9}[A-Za-z0-9\-]*|[A-Za-z]{2,5}\d{3,9}[A-Za-z0-9]*|\d{1,2}[A-Za-z]{2,4}|\d{1,2}-[A-Za-z]{2,4})\b",
    re.IGNORECASE
)

# 4. Strict Measurements & Units
MEASUREMENT_RE = re.compile(
    r"""
    (?<![A-Za-z0-9\-])
    \d+(?:[.,]\d+)?
    \s*
    (?:
        (?:mg|mcg|ug|g|kg|ml|mmol|mol|nmol|pmol|iu|mci|uci|kbq|mbq|gbq|gy|cgy|ppm)
        (?:/(?:kg|m2|ml|l|h|hr|day|d|dose|min))?
        |
        %
        |
        cc\b
        |
        mg/m2\b
        |
        ml\.kg-1\b
    )
    (?![A-Za-z0-9\-])
    """,
    re.VERBOSE | re.IGNORECASE
)

# 5. Standalone isolated numbers only
STANDALONE_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9\-])\d+(?:[.,]\d+)?(?![A-Za-z0-9\-])"
)

# 6. Combination separators: '+' or '/' or 'and'
COMBINATION_SPLIT_RE = re.compile(
    r"(?:\s*\+\s*|\s*/\s*|(?<=[a-zA-Z0-9])/(?=[a-zA-Z0-9])|\s+and\s+)",
    re.IGNORECASE
)

HTML_ENTITY_RE = re.compile(r"&[a-zA-Z0-9#]+;")


@dataclass
class ParsedIntervention:
    original: str
    normalized: str
    compact: str
    tokens: Set[str]
    identifiers: List[str]
    measurements: List[str]
    radiolabels: List[str]
    stereochemistry: List[str]
    is_combination: bool
    components: List[str]
    retention_ratio: float
    is_empty: bool = False


def clean_unicode(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    replacements = {
        "µ": "u", "μ": "u", "β": "beta", "α": "alpha", "γ": "gamma",
        "–": "-", "—": "-", "−": "-", "‐": "-",
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "\u00a0": " ", "®": "", "™": "", "©": ""
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def parse_intervention(text: str) -> ParsedIntervention:
    if not text or not str(text).strip():
        return ParsedIntervention(
            original="", normalized="", compact="", tokens=set(),
            identifiers=[], measurements=[], radiolabels=[],
            stereochemistry=[], is_combination=False, components=[],
            retention_ratio=0.0, is_empty=True
        )

    raw = clean_unicode(str(text).strip())

    # Step 1: Detect Multi-Component Interventions ('+', '/', 'and')
    is_combination = False
    components = []
    if COMBINATION_SPLIT_RE.search(raw):
        parts = [p.strip() for p in COMBINATION_SPLIT_RE.split(raw) if len(p.strip()) >= 2]
        if len(parts) >= 2:
            is_combination = True
            components = parts

    # Step 2: Extract Radiolabels safely
    radiolabels = []
    for m in RADIOLABEL_RE.finditer(raw):
        val = m.group(1) or m.group(2)
        if val:
            radiolabels.append(val.lower())
    text_work = RADIOLABEL_RE.sub(" ", raw)

    # Step 3: Extract Stereochemistry
    stereos = [m.group(0).strip() for m in STEREO_RE.finditer(text_work)]
    text_work = STEREO_RE.sub(" ", text_work)

    # Step 4: Extract and SHIELD Alphanumeric Identifiers (5FU, 3TC, PF-04995274, etc.)
    identifiers = [m.group(0).lower() for m in CODE_IDENTIFIER_RE.finditer(text_work)]
    shield_map = {}
    for idx, ident in enumerate(identifiers):
        placeholder = f"__DRUGID{idx}__"
        shield_map[placeholder] = ident
        pattern = re.compile(re.escape(ident), re.IGNORECASE)
        text_work = pattern.sub(placeholder, text_work)

    # Step 5: Extract Measurements
    measurements = [m.group(0).strip() for m in MEASUREMENT_RE.finditer(text_work)]
    text_work = MEASUREMENT_RE.sub(" ", text_work)

    # Step 6: Remove HTML entities
    text_clean = HTML_ENTITY_RE.sub(" ", text_work)

    # Step 7: Remove isolated standalone numbers
    text_clean = STANDALONE_NUMBER_RE.sub(" ", text_clean)

    # Step 8: Restore Shielded Identifiers
    for placeholder, ident in shield_map.items():
        text_clean = text_clean.replace(placeholder.lower(), ident)
        text_clean = text_clean.replace(placeholder, ident)

    # Step 9: Clean punctuation while preserving hyphens within identifiers
    text_clean = re.sub(r"[/\\|,;:_()\[\]{}*+?#]+", " ", text_clean)
    text_clean = re.sub(r"[^a-zA-Z0-9\-\s]", " ", text_clean)

    # Remove dangling hyphens
    text_clean = re.sub(
        r"(?<=\s)-(?=\s)|^-(?=\s)|(?<=\s)-(?=[a-zA-Z0-9])|(?<=[a-zA-Z0-9])-(?=\s)|-(?=$)",
        " ",
        text_clean
    )
    text_clean = re.sub(r"\s+", " ", text_clean).strip().lower()

    # Step 10: Tokens & Compact form
    tokens = {t for t in text_clean.split() if len(t) >= 2}
    for ident in identifiers:
        clean_id = ident.lower().replace(" ", "")
        if clean_id:
            tokens.add(clean_id)

    compact = re.sub(r"[^a-z0-9]+", "", text_clean)

    # Step 11: Query Information Retention Ratio
    raw_alpha = re.sub(r"[^a-zA-Z0-9]+", "", raw).lower()
    surviving_alpha = re.sub(r"[^a-zA-Z0-9]+", "", text_clean)
    retention_ratio = (len(surviving_alpha) / max(len(raw_alpha), 1)) if raw_alpha else 0.0

    return ParsedIntervention(
        original=raw,
        normalized=text_clean,
        compact=compact,
        tokens=tokens,
        identifiers=identifiers,
        measurements=measurements,
        radiolabels=radiolabels,
        is_combination=is_combination,
        components=components,
        stereochemistry=stereos,
        retention_ratio=round(min(retention_ratio, 1.0), 4),
        is_empty=(len(text_clean) == 0)
    )