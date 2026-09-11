#!/usr/bin/env python3
"""MediScanAI 2.0 — v3.4 biomedical intervention parser.

Designed for precision-first entity resolution while preserving useful structure:
- explicit measurements/strengths
- conservative bare numeric strengths (mainly FDA names)
- development identifiers
- radiolabels
- stereochemistry
- combinations
- retention ratio
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Set

# Radiolabels are intentionally conservative. A generic pattern such as
# ``\d+-[A-Za-z]+`` incorrectly classified ordinary development/drug
# identifiers like ``5-FU`` as isotope labels.  Bracketed isotope notation
# is unambiguous; unbracketed notation is accepted only for a plausible
# isotope mass + chemical element symbol, or for known CT-style forms such as
# ``131-MIBG``.  This is chemical-format logic, not a drug vocabulary.
RADIOLABEL_RE = re.compile(
    r"(?:"
    r"\[\s*(?:\d{1,3}[A-Za-z]{1,2})\s*\][\s\-]*"
    r"|\b(?:3H|11C|13N|15O|18F|22Na|32P|35S|45Ca|51Cr|57Co|58Co|59Fe|67Ga|68Ga|75Se|76Br|77Br|81mKr|82Rb|89Zr|90Y|99mTc|111In|123I|124I|125I|131I|153Sm|177Lu|186Re|188Re|201Tl|223Ra|225Ac)\s*-\s*(?=[A-Za-z])"
    r"|\b\d{2,3}\s*-\s*[A-Za-z]{3,8}(?=\s|$|\+)"
    r")",
    re.IGNORECASE,
)
STEREO_RE = re.compile(
    r"(?:\(\s*[+\-±/]+\s*\)\s*[-–]?|\(\s*[RSrs]\s*\)\s*[-–]?|\b[dDlL]\b\s*[-–]\s*)"
)
CODE_IDENTIFIER_RE = re.compile(
    r"\b(?:[A-Za-z]{1,4}-\d{3,9}[A-Za-z0-9\-]*|[A-Za-z]{2,5}\d{3,9}[A-Za-z0-9]*|\d{1,2}[A-Za-z]{2,4}|\d{1,2}-[A-Za-z]{2,4})\b",
    re.IGNORECASE,
)
MEASUREMENT_RE = re.compile(r"""
(?<![A-Za-z0-9\-])
\d+(?:[.,]\d+)?\s*
(?:
  (?:mg|mcg|ug|g|kg|ml|l|mmol|mol|nmol|pmol|iu|mci|uci|kbq|mbq|gbq|gy|cgy|ppm)
  (?:\s*/\s*(?:kg|m2|mL|ml|l|h|hr|day|d|dose|min))?
 |%
 |cc\b
 |mg\s*/\s*m2\b
 |ml\.kg-1\b
)
(?![A-Za-z0-9\-])
""", re.VERBOSE | re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9\-])\d+(?:[.,]\d+)?(?![A-Za-z0-9\-])")
# Bare numeric strengths in FDA names, e.g. '0.25 bupivacaine hcl' or '50 dextrose'.
# We only use these as candidate metadata; query-side bare numbers are NOT assumed to be strengths.
BARE_STRENGTH_RE = re.compile(r"(?<![A-Za-z0-9\-])\d+(?:[.,]\d+)?(?=\s+[A-Za-z])")
COMBINATION_SPLIT_RE = re.compile(r"(?:\s*\+\s*|(?<=[A-Za-z0-9])\s*/\s*(?=[A-Za-z0-9])|\s+and\s+)", re.IGNORECASE)
HTML_ENTITY_RE = re.compile(r"&[a-zA-Z0-9#]+;")

@dataclass
class ParsedIntervention:
    original: str
    normalized: str
    compact: str
    tokens: Set[str]
    identifiers: List[str]
    measurements: List[str]
    strength_values: List[Dict[str, object]] = field(default_factory=list)
    bare_strengths: List[float] = field(default_factory=list)
    radiolabels: List[str] = field(default_factory=list)
    stereochemistry: List[str] = field(default_factory=list)
    is_combination: bool = False
    components: List[str] = field(default_factory=list)
    retention_ratio: float = 0.0
    is_empty: bool = False


def clean_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or ""))
    for a, b in {"µ":"u","μ":"u","β":"beta","α":"alpha","γ":"gamma","–":"-","—":"-","−":"-","‐":"-","’":"'","‘":"'","“":"\"","”":"\"","\u00a0":" ","®":"","™":"","©":""}.items():
        text = text.replace(a, b)
    return text


def _num(s: str) -> float:
    return float(s.strip().replace(",", "."))


def _measurement_info(raw: str) -> Dict[str, object]:
    s = raw.strip().lower().replace(" ", "")
    m = re.match(r"^(\d+(?:[.,]\d+)?)(.*)$", s)
    if not m:
        return {"raw": raw, "value": None, "unit": "unknown", "dimension": "unknown"}
    value = _num(m.group(1)); unit = m.group(2)
    if unit == "%": dim = "concentration"
    elif unit in {"mg/ml","mg/ml"}: dim = "concentration_mass_volume"
    elif "/kg" in unit or unit in {"mg/kg","mcg/kg","ug/kg"}: dim = "dose_weight"
    elif unit in {"mg","mcg","ug","g","kg","mmol","mol","nmol","pmol","iu","mci","uci","kbq","mbq","gbq","gy","cgy","ppm"} or "/m2" in unit or "/dose" in unit or "/day" in unit or "/h" in unit or "/hr" in unit or "/min" in unit: dim = "dose_or_activity"
    elif unit in {"ml","l","cc"}: dim = "volume"
    else: dim = "other"
    return {"raw": raw, "value": value, "unit": unit, "dimension": dim}


def _empty(original=""):
    return ParsedIntervention(original, "", "", set(), [], [], [], [], [], [], False, [], 0.0, True)


def parse_intervention(text: str, candidate_mode: bool = False) -> ParsedIntervention:
    if not text or not str(text).strip(): return _empty("")
    raw = clean_unicode(text).strip()

    # ClinicalTrials exports frequently prefix intervention entries with a list
    # marker such as "+ Folic acid" or "-Oxaliplatin".  These are NOT
    # stereochemistry.  Preserve genuine stereo forms like (+)-, (-)- and
    # (+/-), but strip an ordinary leading +/-.
    if not re.match(r"^\(\s*[+\-±/]+\s*\)\s*[-–]?", raw) and not re.match(r"^\(\s*[RSrs]\s*\)\s*[-–]?", raw):
        raw = re.sub(r"^[+\-]\s*(?=[A-Za-z0-9\[])", "", raw, count=1)

    is_combination = False; components: List[str] = []

    # Keep a radiolabel placeholder for combination detection.  This must happen
    # BEFORE removing radiolabels from `work`; otherwise `131-MIBG + Vorinostat`
    # collapses to only `Vorinostat` and loses its combination structure.
    combo_probe = raw
    combo_probe = STEREO_RE.sub(" ", combo_probe)
    measurements_probe = MEASUREMENT_RE.sub(" ", combo_probe)
    combo_probe = RADIOLABEL_RE.sub(" RADIOCOMP ", measurements_probe)
    combo_probe = re.sub(r"^\s*\(\s*[+\-±/]+\s*\)\s*[-–]?\s*", "", combo_probe)

    radiolabels = []
    for m in RADIOLABEL_RE.finditer(raw):
        val = m.group(0).strip().strip("[]").replace(" ", "").rstrip("-")
        if val: radiolabels.append(val.lower())
    work = RADIOLABEL_RE.sub(" ", raw)

    stereos = [m.group(0).strip() for m in STEREO_RE.finditer(work)]
    work = STEREO_RE.sub(" ", work)

    # Measurements must be removed BEFORE identifier detection so values such as 15mg
    # are not misclassified as an alphanumeric drug code.
    measurements = [m.group(0).strip() for m in MEASUREMENT_RE.finditer(work)]
    strength_values = [_measurement_info(x) for x in measurements if _measurement_info(x)["dimension"] in {"concentration","concentration_mass_volume"}]
    work = MEASUREMENT_RE.sub(" ", work)

    # Detect combinations after measurement shielding but before identifier shielding.
    # RADIOCOMP preserves a removed radiolabeled component as evidence that the
    # intervention contains more than one component.

    if COMBINATION_SPLIT_RE.search(combo_probe):
        parts = [p.strip() for p in COMBINATION_SPLIT_RE.split(combo_probe) if len(p.strip()) >= 2]
        if len(parts) >= 2:
            is_combination, components = True, parts

    identifiers = [m.group(0).lower() for m in CODE_IDENTIFIER_RE.finditer(work)]
    shields = {}
    for i, ident in enumerate(identifiers):
        ph = f"__DRUGID{i}__"; shields[ph] = ident
        work = re.sub(re.escape(ident), ph, work, flags=re.IGNORECASE)

    # Candidate FDA names often encode strengths as bare numbers. Never infer this on query text.
    bare_strengths: List[float] = []
    if candidate_mode:
        for m in BARE_STRENGTH_RE.finditer(work):
            try: bare_strengths.append(_num(m.group(0)))
            except ValueError: pass

    work = HTML_ENTITY_RE.sub(" ", work)
    work = NUMBER_RE.sub(" ", work)
    for ph, ident in shields.items(): work = work.replace(ph.lower(), ident).replace(ph, ident)
    work = re.sub(r"[/\\|,;:_()\[\]{}*+?#]+", " ", work)
    work = re.sub(r"[^a-zA-Z0-9\-\s]", " ", work)
    work = re.sub(r"(?<![A-Za-z0-9])-(?![A-Za-z0-9])", " ", work)
    work = re.sub(r"\s+", " ", work).strip().lower()

    tokens = {t for t in work.split() if len(t) >= 2}
    tokens.update(i.lower() for i in identifiers if i)
    compact = re.sub(r"[^a-z0-9]+", "", work)
    raw_alpha = re.sub(r"[^a-zA-Z0-9]+", "", raw).lower()
    surviving = re.sub(r"[^a-zA-Z0-9]+", "", work)
    retention = len(surviving) / max(len(raw_alpha), 1) if raw_alpha else 0.0
    return ParsedIntervention(raw, work, compact, tokens, identifiers, measurements, strength_values, bare_strengths, radiolabels, stereos, is_combination, components, round(min(retention,1.0),4), not bool(work))
