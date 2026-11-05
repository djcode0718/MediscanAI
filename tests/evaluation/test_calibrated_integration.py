"""Integration tests for end-to-end Calibrated Evaluator Pipeline (Revision 2.4)."""

import pytest
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

def test_end_to_end_grounded_statement():
    chunks = [
        {"chunk_id": "E1", "text": "NP Thyroid consists of levothyroxine (T4) and liothyronine (T3). Rx Only*"},
        {"chunk_id": "disease_chunk_60", "text": "Atrial Fibrillation is an irregular rhythm."}
    ]
    raw_judge_out = '{"verdict": 1, "reason": "Explicitly listed in E1", "cited_chunk_id": "E1", "cited_quote": "NP Thyroid consists of levothyroxine (T4) and liothyronine (T3)", "is_absence_statement": false}'
    
    # 1. Layer A Schema validation
    envelope, err = StructuralValidator.validate_raw_json(raw_judge_out)
    assert err is None
    assert envelope.verdict == 1
    
    # 2. Citation Verification
    anchor_state, cite_err = StructuralValidator.verify_citations(envelope, chunks)
    assert cite_err is None
    assert anchor_state == AnchorState.VALID_SUPPORTING_ANCHOR

def test_end_to_end_scoped_absence():
    chunks = [
        {"chunk_id": "E1", "text": "Adult dose: 10 mg daily. Renal adjustment: 5 mg daily."}
    ]
    stmt = "The available sources do not mention pediatric dosing."
    assert AbsenceScanner.is_scoped_absence_statement(stmt) is True
    assert AbsenceScanner.is_global_denial_statement(stmt) is False
    
    raw_judge_out = '{"verdict": 1, "reason": "Chunks do not mention pediatric dosing", "cited_chunk_id": null, "cited_quote": null, "is_absence_statement": true}'
    envelope, err = StructuralValidator.validate_raw_json(raw_judge_out)
    assert err is None
    assert envelope.verdict == 1
    assert envelope.is_absence_statement is True
    
    anchor_state, cite_err = StructuralValidator.verify_citations(envelope, chunks)
    assert anchor_state == AnchorState.VERIFIED_CONTEXT_ABSENCE

def test_end_to_end_entity_binding_procrit():
    chunks = [
        {"chunk_id": "E5", "text": "Brand: PROCRIT | Active ingredients: EPOETIN | Indications: Treatment of anemia in CKD."}
    ]
    raw_judge_out = '{"verdict": 1, "reason": "PROCRIT actively binds to EPOETIN in E5 header", "cited_chunk_id": "E5", "cited_quote": "Brand: PROCRIT | Active ingredients: EPOETIN", "is_absence_statement": false}'
    envelope, err = StructuralValidator.validate_raw_json(raw_judge_out)
    assert err is None
    
    anchor_state, cite_err = StructuralValidator.verify_citations(envelope, chunks)
    assert anchor_state == AnchorState.VALID_SUPPORTING_ANCHOR

def test_retry_recovery_trajectory():
    chunks = [{"chunk_id": "E1", "text": "Store at 20C to 25C."}]
    
    # Attempt 1 has hallucinated quote
    raw_out_1 = '{"verdict": 1, "reason": "Matches", "cited_chunk_id": "E1", "cited_quote": "Store at absolute zero", "is_absence_statement": false}'
    env_1, _ = StructuralValidator.validate_raw_json(raw_out_1)
    state_1, err_1 = StructuralValidator.verify_citations(env_1, chunks)
    assert state_1 == AnchorState.INVALID_QUOTATION
    
    # Retry prompt
    repair_prompt = StructuralValidator.build_format_repair_prompt(raw_out_1, err_1)
    assert "not found verbatim" in err_1
    
    # Attempt 2 corrects quote
    raw_out_2 = '{"verdict": 1, "reason": "Correct quote", "cited_chunk_id": "E1", "cited_quote": "Store at 20C to 25C.", "is_absence_statement": false}'
    env_2, _ = StructuralValidator.validate_raw_json(raw_out_2)
    state_2, err_2 = StructuralValidator.verify_citations(env_2, chunks)
    assert state_2 == AnchorState.VALID_SUPPORTING_ANCHOR
    
    # Trace records event
    retry_event = RetryEvent(
        attempt_index=1,
        raw_output=raw_out_2,
        validation_error=err_1,
        retry_prompt=repair_prompt,
        verdict_before_retry=1,
        verdict_after_retry=1
    )
    trace = EvaluatorExecutionTrace(
        item_id="ADJ-TEST",
        initial_raw_output=raw_out_1,
        final_raw_output=raw_out_2,
        initial_verdict=1,
        final_verdict=1,
        verdict_changed_by_retry=False,
        retries_used=1,
        retry_history=[retry_event],
        final_anchor_state=state_2,
        is_structural_failure=False
    )
    assert trace.retries_used == 1
    assert trace.is_structural_failure is False

def test_exhausted_retry_decoupling():
    # If all retries fail, verdict is None, NEVER 0 penalty
    trace = EvaluatorExecutionTrace(
        item_id="ADJ-FAIL",
        initial_raw_output="broken",
        final_raw_output="broken",
        initial_verdict=None,
        final_verdict=None,
        retries_used=2,
        final_anchor_state=AnchorState.ANCHOR_VALIDATION_ERROR,
        is_structural_failure=True,
        evaluator_error_code="PARSE_RETRY_EXHAUSTED"
    )
    assert trace.final_verdict is None
    assert trace.is_structural_failure is True
