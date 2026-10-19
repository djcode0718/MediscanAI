"""
Unit tests for Step 2: Evaluation Sanitizer (evaluation/e2e/sanitize.py).
Tests answer_core extraction, warning stripping, markdown cleanup,
empty header removal, answer_full exposure, and fast-path exclusion detection.
"""
import pytest
from app.guardrail import MANDATORY_HEADER, MANDATORY_TEXT
from evaluation.e2e.sanitize import (
    remove_mandatory_warning,
    remove_empty_headers,
    strip_markdown,
    answer_core,
    answer_full,
    is_fast_path,
)


class TestSanitizer:
    def test_remove_mandatory_warning(self):
        raw = (
            "Based on your symptoms, Advil is suitable.\n\n"
            f"{MANDATORY_HEADER}\n"
            f"{MANDATORY_TEXT}"
        )
        cleaned = remove_mandatory_warning(raw)
        assert cleaned == "Based on your symptoms, Advil is suitable."
        assert MANDATORY_HEADER not in cleaned
        assert MANDATORY_TEXT not in cleaned

    def test_remove_empty_headers(self):
        raw = (
            "### Verdict\n"
            "Medicine is not suitable.\n\n"
            "### Empty Section\n"
            "### Suggested Alternatives\n"
            "* Ibuprofen\n"
            "### Trailing Header\n"
        )
        cleaned = remove_empty_headers(raw)
        assert "### Empty Section" not in cleaned
        assert "### Trailing Header" not in cleaned
        assert "### Verdict" in cleaned
        assert "### Suggested Alternatives" in cleaned

    def test_strip_markdown(self):
        md = "### Header\n**Bold text** and *italic text* with `code`.\n* Bullet item 1\n* Bullet item 2"
        plain = strip_markdown(md)
        assert "###" not in plain
        assert "**" not in plain
        assert "`" not in plain
        assert "*" not in plain
        assert "Bold text and italic text with code." in plain
        assert "Bullet item 1 Bullet item 2" in plain

    def test_answer_core_pipeline(self):
        raw_output = (
            "Based on the analysis, **Lipitor** is **suitable** for treating high cholesterol.\n\n"
            "### Explanation\n"
            "It is an HMG-CoA reductase inhibitor.\n\n"
            "### Empty Section\n\n"
            f"{MANDATORY_HEADER}\n"
            f"{MANDATORY_TEXT}"
        )
        core = answer_core(raw_output)
        assert "Lipitor is suitable for treating high cholesterol." in core
        assert "Explanation It is an HMG-CoA reductase inhibitor." in core
        assert "Empty Section" not in core
        assert MANDATORY_HEADER not in core
        assert "Important Warning" not in core

    def test_answer_full_exposure(self):
        final = "Some full response with disclaimers.\n\n### Warning\nBe careful."
        assert answer_full(final) == final.strip()
        assert answer_full(None) == ""

    def test_is_fast_path_detection(self):
        assert is_fast_path({"fast_path_fired": True}) is True
        assert is_fast_path({"fast_path_fired": False}) is False
        assert is_fast_path({}) is False
        assert is_fast_path(None) is False
