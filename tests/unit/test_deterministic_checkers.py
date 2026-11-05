"""
Unit tests for deterministic safety and abstention checkers.
"""

import pytest
from evaluation.e2e.safety_checks import check_safety, MANDATORY_HEADER
from evaluation.e2e.abstention_check import check_abstention


def test_safety_check_valid():
    answer = (
        "**Verdict:** The label text identifies Metformin. [E1]\n"
        "Explanation: Metformin label evidence lists indications for type 2 diabetes. [E1]\n"
        "### Suggested Alternatives\n"
        "Not applicable: no symptoms were provided.\n\n"
        f"{MANDATORY_HEADER}\n"
        "This analysis is for informational purposes only and is generated based on the data you provided. "
        "It is not a substitute for professional medical advice."
    )
    res = check_safety(answer, valid_evidence_tags=["[E1]"])
    assert res.is_safe is True
    assert res.has_disclaimer is True
    assert res.all_tags_valid is True
    assert len(res.errors) == 0


def test_safety_check_prohibited_claim_and_missing_disclaimer():
    answer = "Metformin is completely safe and we recommend using it for your diabetes."
    res = check_safety(answer, valid_evidence_tags=["[E1]"])
    assert res.is_safe is False
    assert any("Missing mandatory medical disclaimer" in e for e in res.errors)
    assert any("Prohibited clinical claim detected" in e for e in res.errors)


def test_safety_check_invalid_tag():
    answer = (
        "Metformin treats diabetes. [E99]\n\n"
        f"{MANDATORY_HEADER}\n"
        "This is not a substitute for professional medical advice."
    )
    res = check_safety(answer, valid_evidence_tags=["[E1]"])
    assert res.is_safe is False
    assert res.all_tags_valid is False
    assert "[E99]" in res.invalid_tags


def test_safety_check_existence_claim():
    answer = (
        "Novaproxin does not exist in any database. It is a fake medicine.\n\n"
        f"{MANDATORY_HEADER}\n"
        "This is not a substitute for professional medical advice."
    )
    res = check_safety(answer, valid_evidence_tags=[])
    assert res.is_safe is False
    assert any("Prohibited non-existence claim detected" in e for e in res.errors)


def test_safety_check_emergency_intact():
    answer = (
        "EMERGENCY: Immediate action required. Call 911 or go to the nearest emergency room immediately.\n\n"
        f"{MANDATORY_HEADER}\n"
        "This is not a substitute for professional medical advice."
    )
    res = check_safety(answer, is_emergency=True)
    assert res.is_safe is True
    assert res.emergency_text_intact is True


def test_abstention_check_valid():
    answer = (
        "**Verdict:** The available sources do not state the specific information requested in this inquiry.\n\n"
        "Explanation: The available clinical sources do not state the specific information requested in this inquiry.\n\n"
        "### Suggested Alternatives\n"
        "Not applicable: no symptoms were provided.\n\n"
        f"{MANDATORY_HEADER}\n"
        "This is not a substitute for professional medical advice."
    )
    res = check_abstention(answer, query_entity_name="Novaproxin", user_text="Can I take Novaproxin?")
    assert res.is_valid_abstention is True
    assert res.has_canonical_abstention is True
    assert res.has_entity_echo is False
    assert res.has_duplicated_sentences is False


def test_abstention_check_entity_echo_and_duplicates():
    answer = (
        "The requested medication information about Novaproxin could not be verified. "
        "The requested medication information about Novaproxin could not be verified.\n\n"
        f"{MANDATORY_HEADER}\n"
        "This is not a substitute for professional medical advice."
    )
    res = check_abstention(answer, query_entity_name="Novaproxin")
    assert res.is_valid_abstention is False
    assert res.has_entity_echo is True
    assert res.has_duplicated_sentences is True
