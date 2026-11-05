"""
Unit tests for F6 cross-field guard and evidence sufficiency key normalization.
"""

import pytest
from app.evidence import (
    validate_and_sanitize_claims,
    evaluate_evidence_sufficiency,
    EvidenceSufficiencyState,
    EvidenceItem,
)
from backend.core.config import get_settings


def test_crossfield_guard_with_trace_dicts(monkeypatch):
    monkeypatch.setenv("CROSSFIELD_GUARD", "True")

    evidence_items = [
        {
            "type": "DISEASE",
            "item_type": "DISEASE",
            "fields": {"condition": "Hypertension"},
        },
        {
            "type": "DRUG",
            "item_type": "DRUG",
            "fields": {
                "brand_name": "Adrenalinum",
                "generic_name": "EPINEPHRINE",
                "indications": "Rx Only*",
            },
        },
    ]

    answer_dirty = "Adrenalinum is labeled for treatment of Hypertension. [E2]"
    sanitized = validate_and_sanitize_claims(
        answer_dirty,
        valid_evidence_tags=["[E1]", "[E2]"],
        evidence_items=evidence_items,
    )

    assert "does not state labeled indications" in sanitized
    assert "is labeled for treatment of Hypertension" not in sanitized


def test_evaluate_evidence_sufficiency_with_normalized_keys():
    items = [
        EvidenceItem(
            channel="drugs",
            raw_id="123",
            covers_ids=["123"],
            item_type="DRUG",
            fields={
                "brand_name": "Metformin",
                "generic_name": "METFORMIN HYDROCHLORIDE",
                "active_ingredients": "METFORMIN",
                "indications": "Indicated as an adjunct to diet and exercise to improve glycemic control.",
            },
        )
    ]

    state, meta = evaluate_evidence_sufficiency(
        user_text="What is this medicine?",
        ocr_text="Metformin 500mg tablets",
        evidence_items=items,
        case_type="MEDICINE_ONLY",
    )

    assert state == EvidenceSufficiencyState.SUFFICIENT
    assert "metformin" in meta["matched_brands"]
