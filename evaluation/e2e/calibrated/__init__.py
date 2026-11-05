"""MediScanAI Calibrated Evaluator Package (Revision 2.4)."""

from .models import (
    AnchorState,
    RetryEvent,
    EvaluatorExecutionTrace,
    RawJudgeStatementVerdict,
    CalibratedStatementResult,
    CaseEvaluationResult
)
from .structural_validator import StructuralValidator
from .absence_scanner import AbsenceScanner
from .atomic_decomposer import AtomicPropositionDecomposer
from .clinical_correctness import ClinicalCorrectnessAssessor, OrthogonalEvaluationResult
from .clustered_bootstrap import (
    compute_binary_metrics,
    mcnemar_test,
    case_clustered_bootstrap,
    holm_bonferroni_correction
)
from .calibrated_faithfulness import CalibratedFaithfulnessEvaluator

__all__ = [
    "AnchorState",
    "RetryEvent",
    "EvaluatorExecutionTrace",
    "RawJudgeStatementVerdict",
    "CalibratedStatementResult",
    "CaseEvaluationResult",
    "StructuralValidator",
    "AbsenceScanner",
    "AtomicPropositionDecomposer",
    "ClinicalCorrectnessAssessor",
    "OrthogonalEvaluationResult",
    "compute_binary_metrics",
    "mcnemar_test",
    "case_clustered_bootstrap",
    "holm_bonferroni_correction",
    "CalibratedFaithfulnessEvaluator"
]
