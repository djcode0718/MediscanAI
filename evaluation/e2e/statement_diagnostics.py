"""
Statement-level diagnostics helpers (moved verbatim from evaluation/e2e/run_eval.py; re-exported there).
Pure functions: no Pipeline / cache / network side effects on import.
"""
import re
import difflib
from typing import List

BOILERPLATE_PATTERNS = [
    re.compile(r"consult\s+(?:a|your)\s+(?:doctor|physician|healthcare\s+provider|pharmacist)", re.IGNORECASE),
    re.compile(r"informational\s+purposes\s+only", re.IGNORECASE),
    re.compile(r"not\s+a\s+substitute\s+for\s+professional\s+medical\s+advice", re.IGNORECASE),
    re.compile(r"emergency\s+(?:medical\s+)?attention", re.IGNORECASE),
    re.compile(r"call\s+(?:911|112)", re.IGNORECASE),
    re.compile(r"do\s+not\s+take\s+any\s+medication\s+without", re.IGNORECASE),
]


def is_boilerplate_statement(statement: str) -> bool:
    for pat in BOILERPLATE_PATTERNS:
        if pat.search(statement):
            return True
    return False


def compute_best_fuzzy_match(statement: str, contexts: List[str]) -> float:
    if not statement or not contexts:
        return 0.0
    stmt_clean = statement.lower().strip()
    best_score = 0.0
    for ctx in contexts:
        # Check against context sentences or chunks
        sentences = re.split(r"[.\n;]", ctx)
        for s in sentences:
            s_clean = s.lower().strip()
            if not s_clean:
                continue
            ratio = difflib.SequenceMatcher(None, stmt_clean, s_clean).ratio()
            if ratio > best_score:
                best_score = ratio
    return round(best_score, 4)
