"""Comprehensive unit and integration tests for MediScanAI Calibrated Evaluator (Revision 2.4)."""

import pytest
import math
from evaluation.e2e.calibrated.models import (
    AnchorState,
    RawJudgeStatementVerdict,
    EvaluatorExecutionTrace,
    RetryEvent
)
from evaluation.e2e.calibrated.structural_validator import StructuralValidator
from evaluation.e2e.calibrated.absence_scanner import AbsenceScanner
from evaluation.e2e.calibrated.atomic_decomposer import AtomicPropositionDecomposer
from evaluation.e2e.calibrated.clinical_correctness import ClinicalCorrectnessAssessor
from evaluation.e2e.calibrated.clustered_bootstrap import (
    compute_binary_metrics,
    mcnemar_test,
    case_clustered_bootstrap,
    holm_bonferroni_correction
)

# ---------------------------------------------------------------------------
# 1. Structural Validation & Schema Conformance Tests
# ---------------------------------------------------------------------------
def test_schema_validation_valid():
    raw_json = '{"verdict": 1, "reason": "Explicitly stated in monograph", "cited_chunk_id": "E1", "cited_quote": "Store at 20C to 25C", "is_absence_statement": false}'
    envelope, err = StructuralValidator.validate_raw_json(raw_json)
    assert err is None
    assert envelope is not None
    assert envelope.verdict == 1
    assert envelope.cited_chunk_id == "E1"
    assert envelope.cited_quote == "Store at 20C to 25C"

def test_schema_validation_markdown_codeblock():
    raw_json = '```json\n{"verdict": 0, "reason": "Not mentioned", "cited_chunk_id": null, "cited_quote": null, "is_absence_statement": false}\n```'
    envelope, err = StructuralValidator.validate_raw_json(raw_json)
    assert err is None
    assert envelope is not None
    assert envelope.verdict == 0

def test_schema_validation_malformed():
    raw_json = 'This is not json at all'
    envelope, err = StructuralValidator.validate_raw_json(raw_json)
    assert envelope is None
    assert err is not None

# ---------------------------------------------------------------------------
# 2. Citation Verification: Chunk IDs & Verbatim Quotations
# ---------------------------------------------------------------------------
def test_citation_verification_valid():
    context_chunks = [
        {"chunk_id": "E1", "text": "NP Thyroid consists of levothyroxine (T4) and liothyronine (T3). Rx Only*"},
        {"chunk_id": "disease_chunk_60", "text": "Atrial Fibrillation is an irregular rhythm."}
    ]
    envelope = RawJudgeStatementVerdict(
        verdict=1,
        reason="Found in E1",
        cited_chunk_id="E1",
        cited_quote="NP Thyroid consists of levothyroxine",
        is_absence_statement=False
    )
    anchor_state, err = StructuralValidator.verify_citations(envelope, context_chunks)
    assert err is None
    assert anchor_state == AnchorState.VALID_SUPPORTING_ANCHOR

def test_citation_verification_invalid_chunk_id():
    context_chunks = [
        {"chunk_id": "E1", "text": "NP Thyroid consists of levothyroxine."}
    ]
    envelope = RawJudgeStatementVerdict(
        verdict=1,
        reason="Claims found in E99",
        cited_chunk_id="E99",
        cited_quote="NP Thyroid consists of levothyroxine",
        is_absence_statement=False
    )
    anchor_state, err = StructuralValidator.verify_citations(envelope, context_chunks)
    assert anchor_state == AnchorState.INVALID_CHUNK_ID
    assert "not found" in err

def test_citation_verification_invalid_quote():
    context_chunks = [
        {"chunk_id": "E1", "text": "The recommended adult starting dose is 10 mg daily."}
    ]
    envelope = RawJudgeStatementVerdict(
        verdict=1,
        reason="Claims starting dose is 50 mg",
        cited_chunk_id="E1",
        cited_quote="The recommended adult starting dose is 50 mg daily",
        is_absence_statement=False
    )
    anchor_state, err = StructuralValidator.verify_citations(envelope, context_chunks)
    assert anchor_state == AnchorState.INVALID_QUOTATION
    assert "not found verbatim" in err

def test_missing_required_anchor_for_verdict_1():
    context_chunks = [{"chunk_id": "E1", "text": "Some text"}]
    envelope = RawJudgeStatementVerdict(
        verdict=1,
        reason="I believe it",
        cited_chunk_id=None,
        cited_quote=None,
        is_absence_statement=False
    )
    anchor_state, err = StructuralValidator.verify_citations(envelope, context_chunks)
    assert anchor_state == AnchorState.MISSING_REQUIRED_ANCHOR

# ---------------------------------------------------------------------------
# 3. Absence Scanner & Scoped Limitations
# ---------------------------------------------------------------------------
def test_absence_scanner_scoped():
    scoped_text = "The available sources do not mention pediatric dosing for this medication."
    assert AbsenceScanner.is_scoped_absence_statement(scoped_text) is True
    assert AbsenceScanner.is_global_denial_statement(scoped_text) is False

def test_absence_scanner_global_denial():
    global_text = "Valerionex does not exist as a medication."
    assert AbsenceScanner.is_global_denial_statement(global_text) is True

def test_absence_scanner_entity_scan():
    chunks = [
        {"chunk_id": "E1", "text": "Metformin hydrochloride is an oral antihyperglycemic drug."},
        {"chunk_id": "E2", "text": "Insulin glargine should be administered subcutaneously."}
    ]
    m1 = AbsenceScanner.scan_context_for_entity("Metformin", chunks)
    assert len(m1) == 1
    assert m1[0][0] == "E1"
    
    m2 = AbsenceScanner.scan_context_for_entity("Lisinopril", chunks)
    assert len(m2) == 0

# ---------------------------------------------------------------------------
# 4. Atomic Proposition Decomposition & Conjunction
# ---------------------------------------------------------------------------
def test_atomic_decomposition_compound():
    stmt = "Epilepsy causes abnormal involuntary movements and insomnia."
    props = AtomicPropositionDecomposer.decompose(stmt)
    assert len(props) == 2
    assert "abnormal involuntary movements" in props[0]
    assert "insomnia" in props[1]

def test_atomic_decomposition_atomic():
    stmt = "Atrial Fibrillation is documented and overlaps with symptoms."
    props = AtomicPropositionDecomposer.decompose(stmt)
    assert len(props) >= 1

def test_conjunction_aggregation():
    # Conjunction: 1 iff all 1
    assert AtomicPropositionDecomposer.aggregate_verdicts([1, 1, 1]) == 1
    assert AtomicPropositionDecomposer.aggregate_verdicts([1, 0, 1]) == 0
    assert AtomicPropositionDecomposer.aggregate_verdicts([0, 0]) == 0
    assert AtomicPropositionDecomposer.aggregate_verdicts([1]) == 1

# ---------------------------------------------------------------------------
# 5. Layer C Clinical Correctness & Orthogonal Grid
# ---------------------------------------------------------------------------
def test_clinical_correctness_quadrants():
    # Q1: Faithful & True
    res_q1 = ClinicalCorrectnessAssessor.classify_quadrant("ITEM-1", "Statement 1", 1, 1)
    assert res_q1.quadrant == "Q1_FAITHFUL_AND_TRUE"

    # Q2: Faithful but False (Retrieval corruption)
    res_q2 = ClinicalCorrectnessAssessor.classify_quadrant("ITEM-2", "Statement 2", 1, 0)
    assert res_q2.quadrant == "Q2_FAITHFUL_BUT_FALSE"

    # Q3: Hallucinated but True (Parametric memory)
    res_q3 = ClinicalCorrectnessAssessor.classify_quadrant("ITEM-3", "Statement 3", 0, 1)
    assert res_q3.quadrant == "Q3_HALLUCINATED_BUT_TRUE"

    # Q4: Hallucinated & False (Critical hallucination)
    res_q4 = ClinicalCorrectnessAssessor.classify_quadrant("ITEM-4", "Statement 4", 0, 0)
    assert res_q4.quadrant == "Q4_HALLUCINATED_AND_FALSE"

def test_clinical_correctness_pending():
    res = ClinicalCorrectnessAssessor.classify_quadrant("ITEM-5", "Statement 5", 1, None)
    assert res.status == "AWAITING_REFERENCE_LABEL"
    assert res.quadrant is None

# ---------------------------------------------------------------------------
# 6. Statistical Methods: Clustered Bootstrap & McNemar Test
# ---------------------------------------------------------------------------
def test_compute_binary_metrics():
    y_true = [1, 1, 1, 0, 0]
    y_pred = [1, 1, 0, 0, 1]
    m = compute_binary_metrics(y_true, y_pred)
    assert m["tp"] == 2
    assert m["tn"] == 1
    assert m["fp"] == 1
    assert m["fn"] == 1
    assert m["overall_agreement"] == 0.6
    assert m["fnr"] == 1/3
    assert m["fpr"] == 1/2

def test_mcnemar_paired_test():
    y_true =  [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    y_ctrl =  [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]  # 0 correct
    y_interv =[1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]  # 12 correct (12 improvements, 0 regressions)
    res = mcnemar_test(y_true, y_ctrl, y_interv)
    assert res["b_regressions"] == 0
    assert res["c_improvements"] == 12
    assert res["p_value"] < 0.01

def test_case_clustered_bootstrap():
    items = [
        {"case_id": "C1", "human_label": 1, "judge_verdict": 1},
        {"case_id": "C1", "human_label": 1, "judge_verdict": 1},
        {"case_id": "C2", "human_label": 0, "judge_verdict": 0},
        {"case_id": "C2", "human_label": 1, "judge_verdict": 0},
        {"case_id": "C3", "human_label": 1, "judge_verdict": 1}
    ]
    res = case_clustered_bootstrap(items, n_bootstraps=500, seed=42)
    assert res["n_cases"] == 3
    assert "overall_agreement" in res["metrics"]
    ci = res["metrics"]["overall_agreement"]
    assert 0.0 <= ci["ci_lower"] <= ci["ci_upper"] <= 1.0

def test_holm_bonferroni_correction():
    p_vals = [0.001, 0.02, 0.04, 0.20]
    corrected = holm_bonferroni_correction(p_vals, alpha=0.05)
    assert len(corrected) == 4
    assert corrected[0]["is_significant"] is True
    assert corrected[3]["is_significant"] is False
