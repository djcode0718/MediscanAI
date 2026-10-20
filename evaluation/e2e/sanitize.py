"""
MediScanAI — End-to-End Evaluation Response Sanitizer (Step 2)
Extracts answer_core from raw pre-guardrail output and exposes answer_full from final output.
Excludes guardrail injection, boilerplate warnings, and markdown syntax to ensure accurate RAGAS scoring.
"""
import re
from typing import Optional, Dict, Any

from app.guardrail import MANDATORY_HEADER, MANDATORY_TEXT


def remove_mandatory_warning(text: str) -> str:
    """
    Removes the mandatory warning section (from MANDATORY_HEADER onward).
    """
    if not text:
        return ""
    if MANDATORY_HEADER in text:
        text = text.split(MANDATORY_HEADER)[0]
    else:
        # Fallback regex for minor formatting alterations
        pattern = re.compile(r"#{1,6}\s*(?:⚠️\s*)?Important\s+Warning.*", re.IGNORECASE | re.DOTALL)
        text = pattern.sub("", text)
    return text.strip()


def remove_empty_headers(text: str) -> str:
    """
    Removes markdown headers that have no content following them before the next header or EOF.
    """
    if not text:
        return ""
    lines = text.split("\n")
    cleaned_lines = []
    i = 0
    header_pattern = re.compile(r"^\s*#{1,6}\s+.*$")
    while i < len(lines):
        line = lines[i]
        if header_pattern.match(line):
            # Check if there is non-header, non-blank content following
            j = i + 1
            has_content = False
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                if header_pattern.match(next_line):
                    # Next line is another header without content in between
                    break
                else:
                    has_content = True
                    break
            if has_content:
                cleaned_lines.append(line)
                i += 1
            else:
                # Skip this empty header
                i = j
        else:
            cleaned_lines.append(line)
            i += 1
    return "\n".join(cleaned_lines)


def strip_markdown(text: str) -> str:
    """
    Strips markdown syntax (bolding, italics, inline code, headers, list bullets).
    """
    if not text:
        return ""
    # Strip code blocks
    cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Strip headers marker but preserve header text
    cleaned = re.sub(r"^\s*#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    # Strip bold / italic markers
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    # Strip bullet and numbered list markers
    cleaned = re.sub(r"^\s*[\*\-\+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    # Normalize whitespace
    lines = [line.strip() for line in cleaned.split("\n")]
    lines = [line for line in lines if line]
    return " ".join(lines)


def strip_evidence_tags(text: str) -> str:
    """
    Strips [E#] citations from text for evaluation scoring.
    """
    if not text:
        return ""
    return re.sub(r"\[E\d+\]", "", text)


def strip_verdict_and_explanation_labels(text: str) -> str:
    """
    Strips 'Verdict:' and 'Explanation:' labels (including bold/markdown variants).
    """
    if not text:
        return ""
    return re.sub(r"(?i)\*{0,2}\b(?:Verdict|Explanation)\s*:\*{0,2}\s*", "", text)


def answer_core(raw_llm_output: Optional[str]) -> str:
    """
    Extracts the sanitized core answer from RAW pre-guardrail LLM output.
    1. Removes mandatory warning (MANDATORY_HEADER onward).
    2. Strips [E#] evidence tags.
    3. Strips 'Verdict:' and 'Explanation:' labels.
    4. Removes empty section headers.
    5. Strips markdown formatting.
    """
    if not raw_llm_output:
        return ""
    no_warning = remove_mandatory_warning(raw_llm_output)
    no_tags = strip_evidence_tags(no_warning)
    no_labels = strip_verdict_and_explanation_labels(no_tags)
    no_empty_headers = remove_empty_headers(no_labels)
    core = strip_markdown(no_empty_headers)
    return core.strip()


def answer_full(final_output: Optional[str]) -> str:
    """
    Exposes final output (post-guardrail response).
    """
    return (final_output or "").strip()


def is_fast_path(trace: Optional[Dict[str, Any]]) -> bool:
    """
    Identifies whether the emergency fast-path engaged.
    Cases where fast-path fired are excluded from RAGAS scoring.
    """
    if not trace:
        return False
    return bool(trace.get("fast_path_fired", False))
