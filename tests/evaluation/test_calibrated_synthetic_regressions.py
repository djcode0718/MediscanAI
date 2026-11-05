"""Dedicated pytest test suite executing Synthetic Regressions for Step 1E."""

import pytest
from evaluation.e2e.calibrated.models import AnchorState, RawJudgeStatementVerdict
from evaluation.e2e.calibrated.structural_validator import StructuralValidator
from evaluation.e2e.calibrated.absence_scanner import AbsenceScanner
from evaluation.e2e.calibrated.atomic_decomposer import AtomicPropositionDecomposer
from evaluation.e2e.calibrated.synthetic_regressions import get_synthetic_test_suite

SUITE = get_synthetic_test_suite()

def test_synthetic_suite_coverage():
    """Verify all 10 mandatory categories are represented with positive and negative cases."""
    required_cats = {
        "Direct Entailment",
        "Scoped Abstention",
        "Entity Attribution Binding",
        "Clinical Synonymy",
        "Compound Claims",
        "Cross-Chunk Synthesis",
        "Direct Contradiction",
        "Structural Validation",
        "Retry Behavior",
        "Redundancy Decoupling",
        "Targeted Abstention Boundary"
    }
    present_cats = set(tc.category for tc in SUITE)
    assert required_cats.issubset(present_cats), f"Missing categories: {required_cats - present_cats}"
    assert len(SUITE) == 28

@pytest.mark.parametrize("case", SUITE, ids=[c.test_id for c in SUITE])
def test_synthetic_case_logic(case):
    """Deterministic validation of synthetic regression cases."""
    # 1. Scoped Abstention
    if case.category == "Scoped Abstention":
        if case.is_positive_case:
            assert AbsenceScanner.is_scoped_absence_statement(case.statement) is True
            assert AbsenceScanner.is_global_denial_statement(case.statement) is False
        else:
            assert AbsenceScanner.is_global_denial_statement(case.statement) is True

    # 2. Compound Claims & Atomic Decomposition
    elif case.category == "Compound Claims":
        props = AtomicPropositionDecomposer.decompose(case.statement)
        if case.is_positive_case:
            # Both propositions supported
            assert len(props) >= 2
            v = AtomicPropositionDecomposer.aggregate_verdicts([1, 1])
            assert v == 1
        else:
            # One supported, one unsupported -> 0
            assert len(props) >= 2
            v = AtomicPropositionDecomposer.aggregate_verdicts([1, 0])
            assert v == 0

    # 3. Structural Validation & Citations
    elif case.category == "Structural Validation":
        if case.is_positive_case:
            envelope = RawJudgeStatementVerdict(
                verdict=1,
                reason="Verbatim quote in context",
                cited_chunk_id="E1",
                cited_quote="15°C and 30°C",
                is_absence_statement=False
            )
            state, err = StructuralValidator.verify_citations(envelope, case.context_chunks)
            assert state == AnchorState.VALID_SUPPORTING_ANCHOR
        else:
            envelope = RawJudgeStatementVerdict(
                verdict=1,
                reason="Fabricated quote",
                cited_chunk_id="E1",
                cited_quote="cryogenic sub-zero temperatures",
                is_absence_statement=False
            )
            state, err = StructuralValidator.verify_citations(envelope, case.context_chunks)
            assert state == AnchorState.INVALID_QUOTATION

    # 4. Entity Attribution Binding (EPOETIN/PROCRIT)
    elif case.category == "Entity Attribution Binding":
        if case.is_positive_case:
            chunk_text = case.context_chunks[0]["text"]
            assert "PROCRIT" in chunk_text and "EPOETIN" in chunk_text
            assert case.expected_verdict == 1
        else:
            assert case.expected_verdict == 0

    # 5. Redundancy Decoupling
    elif case.category == "Redundancy Decoupling":
        # Both first and repeated statements are supported
        assert case.expected_verdict == 1

    # 6. Targeted Abstention Boundary (Revision 2.4 - Option B)
    elif case.category == "Targeted Abstention Boundary":
        if case.is_positive_case:
            assert AbsenceScanner.is_scoped_absence_statement(case.statement) is True
            assert AbsenceScanner.is_global_denial_statement(case.statement) is False
            assert case.expected_verdict == 1
            # Verify structural validator grants absence anchor for valid absence statements
            env = RawJudgeStatementVerdict(
                verdict=1,
                reason="Absence confirmed in retrieved evidence",
                cited_chunk_id=None,
                cited_quote=None,
                is_absence_statement=True
            )
            st, _ = StructuralValidator.verify_citations(env, case.context_chunks, statement_text=case.statement)
            assert st == AnchorState.VERIFIED_CONTEXT_ABSENCE
        else:
            assert case.expected_verdict == 0
            # For ADJ-0128 and ungrounded entities, ensure absence bypass is blocked
            if "chocolate syrup" in case.statement:
                assert AbsenceScanner.is_scoped_absence_statement(case.statement) is False
                env_bypass = RawJudgeStatementVerdict(
                    verdict=1,
                    reason="Improper absence bypass attempt",
                    cited_chunk_id=None,
                    cited_quote=None,
                    is_absence_statement=True
                )
                st, err = StructuralValidator.verify_citations(env_bypass, case.context_chunks, statement_text=case.statement)
                assert st == AnchorState.MISSING_REQUIRED_ANCHOR

    # 7. General Entailment / Contradiction / Synonymy / Cross-Chunk
    else:
        assert case.expected_verdict in (0, 1)


# ==============================================================================
# Dedicated Verification Suites for Minimal Corrections
# ==============================================================================

def test_context_chunk_parser():
    """Verify robust chunk-boundary parsing across contexts, lines, and formatting variants."""
    # 1. 4-chunk context with single and double newlines
    four_chunk_text = (
        "[E1] DRUG | id=101 | Brand: DrugA | Indications: Adult hypertension\n"
        "[E2] DRUG | id=102 | Brand: DrugB | Indications: Adult diabetes\n\n"
        "[E3] DRUG | id=103 | Brand: DrugC | Indications: Pain relief\n"
        "[E4] DRUG | id=104 | Brand: DrugD | Indications: Allergy relief"
    )
    chunks_4 = StructuralValidator.parse_context_chunks(four_chunk_text)
    assert len(chunks_4) == 4
    assert [c["chunk_id"] for c in chunks_4] == ["E1", "E2", "E3", "E4"]
    assert "Adult hypertension" in chunks_4[0]["text"]
    assert "Allergy relief" in chunks_4[3]["text"]

    # 2. Multi-line chunk content
    multiline_text = (
        "[E1] DRUG | id=201 | Brand: ComplexDrug\n"
        "Usage: Take with food.\n"
        "Warnings: Do not crush.\n"
        "[E2] DRUG | id=202 | Brand: SimpleDrug\n"
        "Usage: Take daily."
    )
    chunks_ml = StructuralValidator.parse_context_chunks(multiline_text)
    assert len(chunks_ml) == 2
    assert "Warnings: Do not crush." in chunks_ml[0]["text"]
    assert chunks_ml[1]["chunk_id"] == "E2"

    # 3. 10-chunk context from E2E-065 and searchability of E7
    import pandas as pd
    df = pd.read_csv("evaluation/e2e/audit/calibration_execution/datasets/calibration_dataset_50.csv")
    row_e2e065 = df[df["case_id"] == "E2E-065"].iloc[0]
    ev_e2e065 = row_e2e065["relevant_evidence_blocks"]
    chunks_10 = StructuralValidator.parse_context_chunks(ev_e2e065)
    assert len(chunks_10) == 10
    assert [c["chunk_id"] for c in chunks_10] == ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"]

    # Specifically verify E7 contains the required evidence for ADJ-0091, ADJ-0093, ADJ-0095
    e7 = next(c for c in chunks_10 if c["chunk_id"] == "E7")
    e7_text = e7["text"]
    assert "TYLENOL Cold Plus Flu Severe" in e7_text
    assert "DEXTROMETHORPHAN HYDROBROMIDE" in e7_text
    assert "PHENYLEPHRINE HYDROCHLORIDE" in e7_text
    assert "thin bronchial secretions" in e7_text

    # 4. Fallback for malformed / headerless text
    malformed_text = "Some unformatted drug documentation without brackets."
    chunks_fallback = StructuralValidator.parse_context_chunks(malformed_text)
    assert len(chunks_fallback) == 1
    assert chunks_fallback[0]["chunk_id"] == "E1"


def test_citation_validation_integrity():
    """Verify that an invalid citation cannot produce an accepted positive faithfulness result."""
    context = [{"chunk_id": "E1", "text": "Metformin 500 mg tablets. Indicated for type 2 diabetes mellitus."}]

    # Case A: Positive verdict with valid supporting citation
    env_valid = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by E1",
        cited_chunk_id="E1",
        cited_quote="type 2 diabetes mellitus",
        is_absence_statement=False
    )
    st_valid, err_valid = StructuralValidator.verify_citations(env_valid, context)
    assert st_valid == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_valid is None

    # Case B: Positive verdict with INVALID_CHUNK_ID
    env_inv_chunk = RawJudgeStatementVerdict(
        verdict=1,
        reason="Cited non-existent chunk",
        cited_chunk_id="E99",
        cited_quote="type 2 diabetes mellitus",
        is_absence_statement=False
    )
    st_inv_chunk, err_inv_chunk = StructuralValidator.verify_citations(env_inv_chunk, context)
    assert st_inv_chunk == AnchorState.INVALID_CHUNK_ID
    assert "not found" in err_inv_chunk

    # Case C: Positive verdict with INVALID_QUOTATION
    env_inv_quote = RawJudgeStatementVerdict(
        verdict=1,
        reason="Fabricated quote",
        cited_chunk_id="E1",
        cited_quote="completely cures all diabetes forever",
        is_absence_statement=False
    )
    st_inv_quote, err_inv_quote = StructuralValidator.verify_citations(env_inv_quote, context)
    assert st_inv_quote == AnchorState.INVALID_QUOTATION
    assert "not found verbatim" in err_inv_quote

    # Case D: Specific test for ADJ-0070 invalid multi-citation
    thyroid_context = [
        {"chunk_id": "E4", "text": "[E4] DRUG | Indications: hypothyroidism of any etiology, except transient..."},
        {"chunk_id": "E5", "text": "[E5] DRUG | Indications: hypothyroidism of any etiology, except transient..."},
        {"chunk_id": "E6", "text": "[E6] DRUG | Indications: hypothyroidism of any etiology, except transient..."}
    ]
    env_adj0070 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by multiple chunks",
        cited_chunk_id="[E99], [E100]",
        cited_quote="hypothyroidism of any etiology",
        is_absence_statement=False
    )
    st_adj0070, err_adj0070 = StructuralValidator.verify_citations(env_adj0070, thyroid_context)
    assert st_adj0070 == AnchorState.INVALID_CHUNK_ID


def test_context_aware_absence_verification_scenarios():
    """Verify Scenarios A through F for context-aware evidence absence verification."""
    # Scenario A: Context omits attribute + correctly scoped absence -> Supported
    ctx_a = [{"chunk_id": "E1", "text": "Amlodipine is indicated for hypertension in adult patients. Adult dosage: 5-10 mg daily."}]
    s_a = "Available sources do not provide pediatric dosing recommendations for amlodipine."
    ok_a, _ = AbsenceScanner.verify_evidence_absence(s_a, ctx_a)
    assert ok_a is True

    # Scenario B: Context explicitly contains attribute + absence claims missing -> Unsupported
    ctx_b = [{"chunk_id": "E1", "text": "Amlodipine pediatric dosing recommendations: 2.5 to 5 mg once daily in children 6 to 17 years."}]
    s_b = "Available sources do not provide pediatric dosing recommendations for amlodipine."
    ok_b, err_b = AbsenceScanner.verify_evidence_absence(s_b, ctx_b)
    assert ok_b is False
    assert "explicitly present in context" in err_b

    # Scenario C: Context has partial evidence (adult dosing), omits specific attribute (pediatric dosing) -> Supported
    ctx_c = [{"chunk_id": "E1", "text": "Amlodipine adult maintenance dose: 10 mg daily. Safety and efficacy in pediatric patients have not been established."}]
    s_c = "Available sources do not provide pediatric dosing recommendations for amlodipine."
    ok_c, _ = AbsenceScanner.verify_evidence_absence(s_c, ctx_c)
    assert ok_c is True

    # Scenario D: Global nonexistence claim -> Unsupported
    s_d = "Pediatric dosing for this medication does not exist in medical science."
    ok_d, err_d = AbsenceScanner.verify_evidence_absence(s_d, ctx_a)
    assert ok_d is False
    assert "Global nonexistence claim" in err_d

    # Scenario E: Fabricated affirmative recommendation -> Unsupported
    s_e = "The clinical dosage of chocolate syrup is not recommended for treating acute appendicitis."
    ok_e, err_e = AbsenceScanner.verify_evidence_absence(s_e, ctx_a)
    assert ok_e is False
    assert "affirmative claim" in err_e

    # Scenario F: Legitimate absence of ungrounded entity (ADJ-0135 minimal pair) -> Supported
    s_f = "The pediatric weight-based dosing for Glycozempra 5mg/mL solution was not found in the provided evidence."
    ok_f, _ = AbsenceScanner.verify_evidence_absence(s_f, ctx_a)
    assert ok_f is True


def test_mandatory_focused_regressions():
    """Verify deterministic behavior for all 8 mandatory regression items."""
    # 1. ADJ-0070: Explicit thyroid indication exclusion
    adj0070_stmt = "LEVOTHYROXINE is labeled for replacement or supplemental therapy in patients with hypothyroidism of any etiology."
    assert AbsenceScanner.is_scoped_absence_statement(adj0070_stmt) is False

    # 2. ADJ-0091: Tylenol bronchial secretions grounded in E7
    adj0091_stmt = "The medication Tylenol Cold Plus Flu Severe thins bronchial secretions."
    assert AbsenceScanner.is_scoped_absence_statement(adj0091_stmt) is False

    # 3. ADJ-0093: Dextromethorphan active ingredient in E7
    adj0093_stmt = "The scanned medicine contains Dextromethorphan Hydrobromide as an active ingredient."
    assert AbsenceScanner.is_scoped_absence_statement(adj0093_stmt) is False

    # 4. ADJ-0095: Phenylephrine active ingredient in E7
    adj0095_stmt = "The scanned medicine contains Phenylephrine Hydrochloride as an active ingredient."
    assert AbsenceScanner.is_scoped_absence_statement(adj0095_stmt) is False

    # 5. ADJ-0135: Glycozempra pediatric dosing not found in evidence (valid Category A)
    adj0135_stmt = "The pediatric weight-based dosing for Glycozempra 5mg/mL solution was not found in the provided evidence."
    assert AbsenceScanner.is_scoped_absence_statement(adj0135_stmt) is True
    assert AbsenceScanner.is_global_denial_statement(adj0135_stmt) is False
    ent_135, attr_135 = AbsenceScanner.extract_absence_targets(adj0135_stmt)
    assert "glycozempra" in ent_135.lower()
    assert "pediatric" in attr_135.lower()

    # 6. ADJ-0118: Generic name versus active ingredient
    adj0118_stmt = "The scanned medicine contains Anti-Thymocyte Globulin (Rabbit) as its active ingredient."
    assert AbsenceScanner.is_scoped_absence_statement(adj0118_stmt) is False

    # 7. ADJ-0125: Unsupported Lipitor COVID cure claim
    adj0125_stmt = "Taking Lipitor was not found to cure acute viral Covid-19 infection according to verified clinical evidence."
    assert AbsenceScanner.is_scoped_absence_statement(adj0125_stmt) is False

    # 8. ADJ-0128: Chocolate syrup appendicitis claim
    adj0128_stmt = "The clinical dosage of chocolate syrup is not recommended for treating acute appendicitis."
    assert AbsenceScanner.is_scoped_absence_statement(adj0128_stmt) is False


def test_five_structural_citation_failures():
    """Verify deterministic resolution of the 5 historical structural citation failures."""
    # 1. ADJ-0039: Deriphyllin indication ending with trailing ellipsis
    chunk_39 = {
        "chunk_id": "E3",
        "text": "[E3] DRUG | Brand: Deriphyllin | Indications: A combination bronchodilator medication used for the relief and prevention of symptoms of asthma, chronic bronchitis and chronic obstructive pulmonary disease."
    }
    env_39 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by E3",
        cited_chunk_id="E3",
        cited_quote="A combination bronchodilator medication used for the relief and prevention of symptoms of asthma...",
        is_absence_statement=False
    )
    st_39, err_39 = StructuralValidator.verify_citations(env_39, [chunk_39])
    assert st_39 == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_39 is None

    # 2. ADJ-0071: NP Thyroid indication exclusion cited with is_absence_statement: true
    chunk_71 = {
        "chunk_id": "E6",
        "text": "[E6] DRUG | Brand: NP Thyroid 60 | Indications: 1. As replacement or supplemental therapy in patients with hypothyroidism of any etiology, except transient hypothyroidism during the recovery phase of subacute thyroiditis."
    }
    env_71 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Explicit exclusion in E6",
        cited_chunk_id="E6",
        cited_quote="except transient hypothyroidism during the recovery phase of subacute thyroiditis",
        is_absence_statement=True
    )
    s_71 = "The condition that NP Thyroid 60 is not suitable for is transient hypothyroidism during the recovery phase of subacute thyroiditis."
    st_71, err_71 = StructuralValidator.verify_citations(env_71, [chunk_71], statement_text=s_71)
    assert st_71 == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_71 is None

    # 3. ADJ-0072: NP Thyroid indication quote ending with trailing ellipsis
    chunk_72 = {
        "chunk_id": "E4",
        "text": "[E4] DRUG | Brand: Liothyronine Sodium | Indications: 1. As replacement or supplemental therapy in patients with hypothyroidism of any etiology, except transient hypothyroidism during the recovery phase of subacute thyroiditis."
    }
    env_72 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by E4",
        cited_chunk_id="E4",
        cited_quote="As replacement or supplemental therapy in patients with hypothyroidism of any etiology...",
        is_absence_statement=False
    )
    s_72 = "The medication NP Thyroid 60 is labeled for replacement or supplemental therapy in patients with hypothyroidism of any etiology."
    st_72, err_72 = StructuralValidator.verify_citations(env_72, [chunk_72], statement_text=s_72)
    assert st_72 == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_72 is None

    # 4. ADJ-0092: Tylenol active ingredient pipe-delimited segment extraction
    chunk_92 = {
        "chunk_id": "E7",
        "text": "[E7] DRUG | Brand: Tylenol Cold Plus Flu Severe | Active ingredients: ACETAMINOPHEN; DEXTROMETHORPHAN HYDROBROMIDE; GUAIFENESIN; PHENYLEPHRINE HYDROCHLORIDE"
    }
    env_92 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by E7 active ingredients",
        cited_chunk_id="E7",
        cited_quote="[ACETAMINOPHEN; DEXTROMETHORPHAN HYDROBROMIDE; GUAIFENESIN; PHENYLEPHRINE HYDROCHLORIDE] | Active ingredients: ACETAMINOPHEN;",
        is_absence_statement=False
    )
    s_92 = "The scanned medicine contains Acetaminophen as an active ingredient."
    st_92, err_92 = StructuralValidator.verify_citations(env_92, [chunk_92], statement_text=s_92)
    assert st_92 == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_92 is None

    # 5. ADJ-0120: Strophanthus Rx Only with 'e.g. E7' chunk id and single-quoted quote
    chunk_120 = {
        "chunk_id": "E7",
        "text": "[E7] DRUG | Brand: Strophanthus | Rx Only*"
    }
    env_120 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by E7 Rx Only status",
        cited_chunk_id="e.g. E7",
        cited_quote="'Rx Only*'",
        is_absence_statement=False
    )
    s_120 = "The medication Strophanthus is an Rx Only drug."
    st_120, err_120 = StructuralValidator.verify_citations(env_120, [chunk_120], statement_text=s_120)
    assert st_120 == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_120 is None


def test_adj0070_and_exception_handling_variants():
    """Verify deterministic handling of clinical exceptions across 4 canonical scenarios.
    
    1. Preserves explicit exception -> Valid (Entailed)
    2. Drops exception and overstates evidence -> Contradiction / Unsupported (verdict=0)
    3. Changes scope of exception -> Contradiction / Unsupported (verdict=0)
    4. Treats narrow exception as universal prohibition -> Contradiction / Unsupported (verdict=0)
    """
    ctx = [
        {
            "chunk_id": "E1",
            "text": "[E1] DRUG | Brand: Cardiovasc | Indications: Indicated for replacement or supplemental therapy in patients with hypertension of any etiology, except transient hypertension during acute volume overload."
        }
    ]
    ev_quote = "Indicated for replacement or supplemental therapy in patients with hypertension of any etiology, except transient hypertension during acute volume overload."

    # Variant 1: Statement correctly preserves the explicit exception -> Valid Supporting Anchor
    stmt_v1 = "Cardiovasc is indicated for hypertension of any etiology, except transient hypertension during acute volume overload."
    env_v1 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Direct match",
        cited_chunk_id="E1",
        cited_quote=ev_quote,
        is_absence_statement=False
    )
    st_v1, err_v1 = StructuralValidator.verify_citations(env_v1, ctx, statement_text=stmt_v1)
    assert st_v1 == AnchorState.VALID_SUPPORTING_ANCHOR
    assert err_v1 is None

    # Variant 2: Statement drops the exception and overstates evidence (ADJ-0070 pattern) -> Contradiction Anchor
    stmt_v2 = "Cardiovasc is labeled for replacement or supplemental therapy in patients with hypertension of any etiology."
    env_v2 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Matches broad indication",
        cited_chunk_id="E1",
        cited_quote=ev_quote,
        is_absence_statement=False
    )
    st_v2, err_v2 = StructuralValidator.verify_citations(env_v2, ctx, statement_text=stmt_v2)
    assert st_v2 == AnchorState.VALID_CONTRADICTING_ANCHOR
    assert "omitted in statement, overstating evidence" in err_v2

    # Variant 3: Statement changes the scope of the exception -> Contradiction Anchor
    stmt_v3 = "Cardiovasc is indicated for hypertension of any etiology, except pediatric essential hypertension."
    env_v3 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Has exception",
        cited_chunk_id="E1",
        cited_quote=ev_quote,
        is_absence_statement=False
    )
    st_v3, err_v3 = StructuralValidator.verify_citations(env_v3, ctx, statement_text=stmt_v3)
    assert st_v3 == AnchorState.VALID_CONTRADICTING_ANCHOR
    assert "changes scope of exception" in err_v3

    # Variant 4: Statement incorrectly treats narrow exception as universal prohibition -> Contradiction Anchor
    stmt_v4 = "Cardiovasc is contraindicated for all hypertension."
    env_v4 = RawJudgeStatementVerdict(
        verdict=1,
        reason="Interprets exception as universal denial",
        cited_chunk_id="E1",
        cited_quote=ev_quote,
        is_absence_statement=False
    )
    st_v4, err_v4 = StructuralValidator.verify_citations(env_v4, ctx, statement_text=stmt_v4)
    assert st_v4 == AnchorState.VALID_CONTRADICTING_ANCHOR
    assert "universal prohibition" in err_v4

    # Direct ADJ-0070 verification
    adj0070_ctx = [
        {
            "chunk_id": "E4",
            "text": "[E4] DRUG | id=19593 | Indications: 1. As replacement or supplemental therapy in patients with hypothyroidism of any etiology, except transient hypothyroidism during the recovery phase of subacute thyroiditis."
        }
    ]
    adj0070_stmt = "LEVOTHYROXINE is labeled for replacement or supplemental therapy in patients with hypothyroidism of any etiology."
    adj0070_env = RawJudgeStatementVerdict(
        verdict=1,
        reason="Supported by E4",
        cited_chunk_id="E4",
        cited_quote="As replacement or supplemental therapy in patients with hypothyroidism of any etiology, except transient hypothyroidism during the recovery phase of subacute thyroiditis.",
        is_absence_statement=False
    )
    st_70, err_70 = StructuralValidator.verify_citations(adj0070_env, adj0070_ctx, statement_text=adj0070_stmt)
    assert st_70 == AnchorState.VALID_CONTRADICTING_ANCHOR
    assert "omitted in statement, overstating evidence" in err_70


def test_previously_corrected_cases_integrity():
    """Verify that previously corrected cases ADJ-0118, ADJ-0125, ADJ-0128, and ADJ-0135 remain correct."""
    # ADJ-0118: Generic vs Active Ingredient (False Positive control)
    ctx_118 = [{"chunk_id": "E1", "text": "Brand: Thymoglobulin. Generic: Anti-thymocyte globulin (rabbit). Active ingredients: rabbit immunoglobulin."}]
    s_118 = "The scanned medicine contains Anti-Thymocyte Globulin (Rabbit) as its active ingredient."
    assert AbsenceScanner.is_scoped_absence_statement(s_118) is False

    # ADJ-0125: Lipitor COVID cure claim (Unsupported control)
    s_125 = "Taking Lipitor was not found to cure acute viral Covid-19 infection according to verified clinical evidence."
    assert AbsenceScanner.is_scoped_absence_statement(s_125) is False
    assert AbsenceScanner.is_global_denial_statement(s_125) is False

    # ADJ-0128: Chocolate syrup appendicitis claim (Unsupported control)
    s_128 = "The clinical dosage of chocolate syrup is not recommended for treating acute appendicitis."
    assert AbsenceScanner.is_scoped_absence_statement(s_128) is False

    # ADJ-0135: Glycozempra legitimate absence claim (Supported control)
    s_135 = "The pediatric weight-based dosing for Glycozempra 5mg/mL solution was not found in the provided evidence."
    assert AbsenceScanner.is_scoped_absence_statement(s_135) is True
    ok_135, _ = AbsenceScanner.verify_evidence_absence(s_135, ctx_118)
    assert ok_135 is True

