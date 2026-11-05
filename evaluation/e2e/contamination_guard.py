"""
Contamination guard for RAGAS faithfulness scoring (P1 / eval-repair).

A case is `invalid_contaminated` when the judge's extracted statements are not about the judged answer:
  (1) any extracted statement matches a few-shot EXAMPLE string of the INSTALLED RAGAS faithfulness prompts
      (normalised, similarity >= 0.9) -- strong evidence the judge echoed the prompt's example, OR
  (2) >= 50% of the extracted statements share no content word with the judged answer.
A single (or minority of) zero-overlap statement(s) is only a warning ("low_overlap_statement"); the case stays valid.

Example strings are loaded from the installed ragas prompt objects at runtime. They are NEVER hard-copied here
(the E2E-080 regression strings live only in tests/fixtures).
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

EVAL_GUARD_VERSION = "1"

SIMILARITY_THRESHOLD = 0.9
ZERO_OVERLAP_FRACTION_THRESHOLD = 0.5

_STOPWORDS = frozenset(
    """a an the and or but if then else of to in on at by for with from as is are was were be been being it its this that
    these those there here which who whom whose what when where why how not no nor can could may might must shall should
    will would do does did done has have had having also into than over under about after before between such any all
    some more most other their his her they them he she you your we our i me my us per via only both each very""".split()
)


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (s or "").lower())).strip()


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def content_words(s: str) -> set:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) >= 3 and w not in _STOPWORDS}


def load_example_strings(faithfulness_metric: Any = None) -> List[str]:
    """All few-shot example strings (statement-generation outputs + NLI example statements) of the INSTALLED ragas."""
    if faithfulness_metric is None:
        from ragas.metrics._faithfulness import Faithfulness
        faithfulness_metric = Faithfulness()
    out: List[str] = []
    for _inp, outp in getattr(faithfulness_metric.statement_generator_prompt, "examples", []):
        out.extend(list(outp.statements))
    for inp, outp in getattr(faithfulness_metric.nli_statements_prompt, "examples", []):
        out.extend(list(inp.statements))
        out.extend(a.statement for a in outp.statements)
    seen, uniq = set(), []
    for s in out:
        n = normalize_text(s)
        if n and n not in seen:
            seen.add(n)
            uniq.append(s)
    return uniq


@dataclass
class GuardOutcome:
    contaminated: bool = False
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    example_matches: List[Dict[str, Any]] = field(default_factory=list)
    zero_overlap_statements: List[str] = field(default_factory=list)
    zero_overlap_fraction: float = 0.0
    guard_version: str = EVAL_GUARD_VERSION


def check_contamination(statements: Iterable[str], answer_text: str, example_strings: Optional[List[str]] = None) -> GuardOutcome:
    statements = [s for s in statements if isinstance(s, str) and s.strip()]
    examples = example_strings if example_strings is not None else load_example_strings()
    ex_norm = [(e, normalize_text(e)) for e in examples]
    ans_norm = normalize_text(answer_text)
    ans_words = content_words(answer_text)
    out = GuardOutcome()

    # (1) reproduction of an evaluator example output
    for st in statements:
        n = normalize_text(st)
        best_e, best_sim = None, 0.0
        for e, en in ex_norm:
            sim = difflib.SequenceMatcher(None, n, en).ratio()
            if sim > best_sim:
                best_e, best_sim = e, sim
        if best_e is not None and best_sim >= SIMILARITY_THRESHOLD:
            # An example string that the judged answer itself genuinely contains is not evidence of an echo.
            if normalize_text(best_e) in ans_norm:
                out.warnings.append(f"statement_matches_example_but_present_in_answer: {st[:80]}")
                continue
            out.example_matches.append({"statement": st, "example": best_e, "similarity": round(best_sim, 4)})
    if out.example_matches:
        out.contaminated = True
        out.reasons.append(f"example_statement_reproduced ({len(out.example_matches)}/{len(statements)} statements)")

    # (2) lexical overlap with the judged answer
    for st in statements:
        if not (content_words(st) & ans_words):
            out.zero_overlap_statements.append(st)
    if statements:
        out.zero_overlap_fraction = len(out.zero_overlap_statements) / len(statements)
    if statements and out.zero_overlap_fraction >= ZERO_OVERLAP_FRACTION_THRESHOLD:
        out.contaminated = True
        out.reasons.append(
            f"zero_overlap_majority ({len(out.zero_overlap_statements)}/{len(statements)} statements share no content word with the answer)"
        )
    else:
        for st in out.zero_overlap_statements:
            out.warnings.append(f"low_overlap_statement: {st[:120]}")
    return out
