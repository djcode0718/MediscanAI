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


def test_query_aware_disease_omission():
    """
    Tests that when query_aware_filtering is enabled on medicine-directed queries,
    disease symptom blocks with no overlap to user symptoms are omitted from shown evidence.
    When query_aware_filtering is disabled (default/legacy), they remain included.
    """
    formatter = CompactEvidenceFormatter()
    disease_rec = {
        "id": 10,
        "chunk": {
            "id": "chunk_11",
            "disease": "Acute Chest Syndrome",
            "symptoms": ["chest pain", "shortness of breath", "fever"]
        }
    }
    drug_rec = {
        "id": 101,
        "brand_name": "Tylenol",
        "generic_name": "Acetaminophen",
        "substance_name": ["Acetaminophen"],
        "indications_and_usage": "Pain reliever and fever reducer."
    }
    retrievals = {
        "diseases": [("chunk_11", 0.9, disease_rec)],
        "drugs": [("drug_101", 0.95, drug_rec)]
    }

    # 1. Default / legacy behavior: disease block is included even for medicine queries
    rendered_default, trace_default = formatter.format(retrievals, query_aware_filtering=False)
    types_default = [it["item_type"] for it in trace_default["evidence_items"]]
    assert "DISEASE" in types_default
    assert "DRUG" in types_default

    # 2. Query-aware filtering on medicine-directed query with no user symptoms:
    # Disease block with no symptom overlap is omitted
    med_user_text = "Please provide the therapeutic indications, active ingredients, and important warnings for this scanned drug label."
    rendered_filtered, trace_filtered = formatter.format(
        retrievals,
        query_aware_filtering=True,
        user_text=med_user_text,
        is_medicine_directed=True,
    )
    types_filtered = [it["item_type"] for it in trace_filtered["evidence_items"]]
    assert "DISEASE" not in types_filtered
    assert "DRUG" in types_filtered
    assert "disease_chunk_11" in trace_filtered["retrieved_but_omitted_ids"]

    # 3. Query-aware filtering when user DOES have symptoms matching the disease:
    # Disease block IS kept
    sym_user_text = "I am experiencing severe chest pain and high fever. Can I take this?"
    rendered_sym, trace_sym = formatter.format(
        retrievals,
        query_aware_filtering=True,
        user_text=sym_user_text,
        is_medicine_directed=True,
    )
    types_sym = [it["item_type"] for it in trace_sym["evidence_items"]]
    assert "DISEASE" in types_sym
    assert "DRUG" in types_sym


def test_parse_multi_ingredient_formulations():
    from app.evidence import parse_multi_ingredient_formulations

    text = "ACTIVE INGREDIENTS (HPUS*) PURPOSE**: ABROTANUM 6C (intestines), ACONITUM NAPELLUS 1M (shock), AETHUSA CYNAPIUM 200C (dairy intolerance), AMBRA GRISEA 30C (confusion/memory), ANTIMONIUM CRUDUM 6C (rash)"
    # Without query tokens: preserves all valid formulation-purpose mappings
    parsed = parse_multi_ingredient_formulations(text)
    assert parsed is not None
    assert "ABROTANUM 6C (purpose: intestines)" in parsed
    assert "AMBRA GRISEA 30C (purpose: confusion/memory)" in parsed

    # With query token 'confusion': prioritizes matching formulation first
    parsed_prioritized = parse_multi_ingredient_formulations(text, query_tokens={"confusion"})
    assert parsed_prioritized is not None
    assert parsed_prioritized.startswith("AMBRA GRISEA 30C (purpose: confusion/memory)")

    # Standard non-kit text returns None
    assert parse_multi_ingredient_formulations("For temporary relief of minor aches and pains.") is None
    assert parse_multi_ingredient_formulations(None) is None


def test_multi_ingredient_kit_attribution_and_ocr_brand_filtering():
    formatter = CompactEvidenceFormatter()

    kit_rec = {
        "id": 41438,
        "brand_name": "Joette Calabrese Survivalist Kit",
        "generic_name": "ABROT ACON AGN AIL AMBR AMBRO AM-C ANT-C APIS ARN ARS AUR-A AUR BAPT BAR-C BELL BB",
        "substance_name": ["ACONITUM NAPELLUS", "AETHUSA CYNAPIUM", "AMBERGRIS", "AMBRA GRISEA", "APIS MELLIFERA", "ARNICA MONTANA", "BELLADONNA", "CHAMOMILLA"],
        "indications_and_usage": "ACTIVE INGREDIENTS (HPUS*) PURPOSE**: ACONITUM NAPELLUS 1M (shock), AMBRA GRISEA 30C (confusion/memory), ANTIMONIUM CRUDUM 6C (rash)"
    }
    unrelated_drug = {
        "id": 7378,
        "brand_name": "Throat Care",
        "generic_name": "ECHINACEA, ACONITUM NAP., APIS MEL.",
        "substance_name": ["ACONITUM NAPELLUS", "ECHINACEA"],
        "indications_and_usage": "Formulated for associated symptoms such as dryness and hoarseness."
    }

    retrievals = {
        "drugs_from_ocr": [
            ("drug_41438", 0.95, kit_rec),
            ("drug_7378", 0.85, unrelated_drug),
        ]
    }

    # 1. When OCR clearly contains the brand "Joette Calabrese Survivalist Kit":
    # Strong-brand filtering keeps the Kit and omits unrelated "Throat Care"
    rendered, trace = formatter.format(
        retrievals,
        query_aware_filtering=True,
        user_text="I am experiencing Confusion.",
        ocr_text="Joette Calabrese Survivalist Kit 500mg Rx Only",
    )

    items = trace["evidence_items"]
    assert len(items) == 1
    assert items[0]["id"] == "41438"
    assert "7378" in trace["retrieved_but_omitted_ids"]
    assert "Throat Care" not in rendered

    # Formulation parsing prioritized the matching confusion formulation
    assert "AMBRA GRISEA 30C (purpose: confusion/memory)" in rendered

    # 2. Fallback behavior: when OCR text does not match any brand, keep all retrieved drugs
    rendered_fallback, trace_fallback = formatter.format(
        retrievals,
        query_aware_filtering=True,
        user_text="I am experiencing symptoms.",
        ocr_text="Unreadable label 500mg",
    )
    assert len(trace_fallback["evidence_items"]) == 2


def test_validate_and_sanitize_claims():
    from app.evidence import validate_and_sanitize_claims

    # 1. Normalizes syntax
    raw = "Condition A [E#1] and Condition B E#2 are listed [E#]."
    res = validate_and_sanitize_claims(raw, valid_evidence_tags=["[E1]", "[E2]"])
    assert "[E1]" in res
    assert "[E2]" in res
    assert "[E#1]" not in res
    assert "[E#]" not in res

    # 2. Removes invalid tags not present in evidence
    raw2 = "This statement cites [E1] and hallucinated [E99]."
    res2 = validate_and_sanitize_claims(raw2, valid_evidence_tags=["[E1]"])
    assert "[E1]" in res2
    assert "[E99]" not in res2

    # 3. Strips additive narrative modifiers ("also includes")
    raw3 = "Atrial fibrillation also includes dizziness. Coronary atherosclerosis additionally includes chest pain."
    res3 = validate_and_sanitize_claims(raw3)
    assert "also includes" not in res3
    assert "additionally includes" not in res3
    assert "Atrial fibrillation includes dizziness." in res3
    assert "Coronary atherosclerosis includes chest pain." in res3

    # 4. Strips negative alternative disclaimers
    raw4 = "Asthma is documented with shortness of breath. [E1] No alternative conditions were identified in the available sources."
    res4 = validate_and_sanitize_claims(raw4, valid_evidence_tags=["[E1]"])
    assert "No alternative conditions" not in res4
    assert res4.strip() == "Asthma is documented with shortness of breath. [E1]"


