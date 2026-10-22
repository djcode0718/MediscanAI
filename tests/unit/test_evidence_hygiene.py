"""
Unit tests for Step 3: Compact Evidence Formatter (app/evidence.py).
Tests sentence-boundary cuts, token budget enforcement, drug deduplication,
placeholder omission, corrupted key handling, and backwards compatibility.
"""

import pytest
from app.evidence import (
    cut_at_sentence_boundary,
    strip_boilerplate_prefix,
    clean_text_field,
    deduplicate_drug_items,
    CompactEvidenceFormatter,
    estimate_tokens,
)
from app.core import Pipeline


def test_clean_text_field_and_placeholders():
    assert clean_text_field("   ") is None
    assert clean_text_field(None) is None
    assert clean_text_field("N/A") is None
    assert clean_text_field("None") is None
    assert clean_text_field("null") is None
    assert clean_text_field("none reported") is None
    assert clean_text_field("  Aspirin 81mg  ") == "Aspirin 81mg"


def test_strip_boilerplate_prefix():
    assert strip_boilerplate_prefix("1 INDICATIONS AND USAGE: For the relief of pain.") == "For the relief of pain."
    assert strip_boilerplate_prefix("INDICATIONS: Temporary relief of cough.") == "Temporary relief of cough."
    assert strip_boilerplate_prefix("DOSAGE AND ADMINISTRATION Take 2 tablets daily.") == "Take 2 tablets daily."
    assert strip_boilerplate_prefix("ADVERSE REACTIONS Common side effects include nausea.") == "Common side effects include nausea."


def test_no_mid_sentence_cuts():
    # Long text with 3 full sentences
    s1 = "This is the first sentence about medication safety."
    s2 = "This is the second sentence explaining indications and dosage."
    s3 = "This is the third sentence warning about possible adverse events."
    full = f"{s1} {s2} {s3}"

    # Cap set between sentence 1 and sentence 2
    cut = cut_at_sentence_boundary(full, max_chars=len(s1) + 15)
    assert cut == s1
    assert cut.endswith(".")

    # Cap set between sentence 2 and sentence 3
    cut2 = cut_at_sentence_boundary(full, max_chars=len(s1) + len(s2) + 10)
    assert cut2 == f"{s1} {s2}"
    assert cut2.endswith(".")

    # Cap smaller than first sentence preserves first sentence rather than mid-sentence cut
    cut3 = cut_at_sentence_boundary(full, max_chars=20)
    assert cut3 == s1


def test_dedup_keeps_rank_order_and_covers_ids():
    items = [
        ("drug_101", 0.95, {
            "id": 101,
            "brand_name": "Tylenol Extra Strength",
            "generic_name": "Acetaminophen",
            "substance_name": ["Acetaminophen"],
            "indications_and_usage": "For temporary relief of minor aches and pains."
        }),
        ("drug_102", 0.90, {
            "id": 102,
            "brand_name": "Panadol Rapid",
            "generic_name": "Acetaminophen",
            "substance_name": ["Acetaminophen"],
            "indications_and_usage": "For relief of headache."
        }),
        ("drug_103", 0.85, {
            "id": 103,
            "brand_name": "Advil Liqui-Gels",
            "generic_name": "Ibuprofen",
            "substance_name": ["Ibuprofen"],
            "indications_and_usage": "For relief of inflammation."
        }),
        ("drug_104", 0.80, {
            "id": 104,
            "brand_name": "Mapap",
            "generic_name": "Acetaminophen",
            "substance_name": ["Acetaminophen"],
            "indications_and_usage": "Pain reliever."
        }),
    ]

    deduped, omitted = deduplicate_drug_items(items, max_items=3)

    # We should have 2 unique generic records: Acetaminophen and Ibuprofen
    assert len(deduped) == 2
    rep_acetaminophen = deduped[0]
    assert rep_acetaminophen["raw_id"] == "101"
    assert rep_acetaminophen["primary_brand"] == "Tylenol Extra Strength"
    assert "Panadol Rapid" in rep_acetaminophen["also_marketed_as"]
    assert "Mapap" in rep_acetaminophen["also_marketed_as"]
    assert rep_acetaminophen["covers_ids"] == ["101", "102", "104"]

    rep_ibuprofen = deduped[1]
    assert rep_ibuprofen["raw_id"] == "103"
    assert rep_ibuprofen["primary_brand"] == "Advil Liqui-Gels"
    assert rep_ibuprofen["covers_ids"] == ["103"]

    assert "102" in omitted
    assert "104" in omitted


def test_corrupted_key_adreactions_fallback():
    formatter = CompactEvidenceFormatter(drug_fields="brand_name,adverse_reactions")
    retrievals = {
        "drugs": [
            ("drug_501", 0.9, {
                "id": 501,
                "brand_name": "CorruptedDrug",
                "generic_name": "TestDrug",
                "substance_name": ["Test"],
                # Standard key missing, corrupted key present
                "adréactions": "Common reactions include dizziness and fatigue."
            })
        ]
    }
    rendered, trace = formatter.format(retrievals)
    assert "[E1] DRUG" in rendered
    assert "Adverse_reactions: Common reactions include dizziness and fatigue." in rendered


def test_empty_channels_omitted():
    formatter = CompactEvidenceFormatter()
    retrievals = {
        "diseases": [],
        "drugs": [
            ("drug_1", 0.9, {
                "id": 1,
                "brand_name": "Aspirin",
                "generic_name": "Aspirin",
                "substance_name": ["Aspirin"],
                "indications_and_usage": "Pain relief."
            })
        ],
        "drug_dict": [],
    }
    rendered, trace = formatter.format(retrievals)
    assert "No results found" not in rendered
    assert "[E1] DRUG" in rendered
    assert len(trace["evidence_items"]) == 1


def test_budget_never_exceeded_and_trims_recorded():
    formatter = CompactEvidenceFormatter()
    # Create large retrieval items
    retrievals = {
        "diseases": [
            ("dis_1", 0.9, {
                "chunk": {
                    "chunk_id": 1,
                    "disease": "Hypertension",
                    "symptoms": ["headache", "shortness of breath", "nosebleeds"]
                }
            })
        ],
        "drugs": [
            (f"drug_{i}", 0.8, {
                "id": i,
                "brand_name": f"LongDrugName_{i}",
                "generic_name": f"GenericName_{i}",
                "substance_name": [f"Ingredient_{i}"],
                "indications_and_usage": "This is a detailed sentence describing clinical indications. " * 15
            })
            for i in range(1, 4)
        ]
    }

    # Set strict token budget
    strict_budget = 100
    rendered, trace = formatter.format(retrievals, token_budget=strict_budget)

    total_tokens = trace["total_evidence_tokens"]
    assert total_tokens <= strict_budget
    assert len(trace["trims"]) > 0
    assert trace["cap_multiplier"] < 1.0 or len(trace["retrieved_but_omitted_ids"]) > 0


def test_legacy_format_remains_unchanged():
    pipeline = Pipeline()
    sample_retrievals = {
        "diseases": [("dis_1", 0.95, {"chunk": {"disease": "Flu", "symptoms": ["fever"]}})]
    }
    legacy_text = pipeline._format_retrievals(sample_retrievals)
    assert "-- Retrieved from DISEASES --" in legacy_text
    assert "* Result: {'chunk': {'disease': 'Flu', 'symptoms': ['fever']}} (Score: 0.9500)" in legacy_text


def test_disease_chunk_id_extract_matches_corpus_and_reference():
    """
    Regression test for the 0-based vs 1-based disease chunk ID mismatch.
    In data/diseases_faiss_data.jsonl, line 0 has id=0 and chunk={'id': 'chunk_1', ...}.
    The corpus and dataset reference use 'disease_chunk_1', not 'disease_chunk_0'.
    """
    from app.evidence import extract_item_id

    # Case 1: Record has chunk.id = "chunk_1" and record id = 0
    rec_with_chunk = {
        "id": 0,
        "chunk": {
            "id": "chunk_1",
            "disease": "Gestational Cholestasis",
            "symptoms": ["Itchy skin"]
        }
    }
    canonical_id = extract_item_id(rec_with_chunk, "line_0", "diseases")
    assert canonical_id == "disease_chunk_1"

    # Case 2: E2E-035 disease chunk (record id=2111, chunk.id="chunk_2112")
    e2e_35_rec = {
        "id": 2111,
        "chunk": {
            "id": "chunk_2112",
            "disease": "Chest Pain",
            "symptoms": ["Chest Pain"]
        }
    }
    assert extract_item_id(e2e_35_rec, "line_2111", "diseases") == "disease_chunk_2112"

    # Case 3: Formatted compact block uses canonical ID
    formatter = CompactEvidenceFormatter()
    retrievals = {"diseases": [("line_0", 0.95, rec_with_chunk)]}
    rendered, trace = formatter.format(retrievals)
    assert "[E1] DISEASE | id=disease_chunk_1 |" in rendered
    assert trace["evidence_items"][0]["id"] == "disease_chunk_1"
    assert trace["evidence_items"][0]["covers_ids"] == ["disease_chunk_1"]
