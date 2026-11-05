"""Data models and schemas for MediScanAI Calibrated Evaluator (Revision 2.4)."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AnchorState(str, Enum):
    """Unified 8-state evidence-anchor classification schema."""
    VALID_SUPPORTING_ANCHOR = "VALID_SUPPORTING_ANCHOR"
    VALID_CONTRADICTING_ANCHOR = "VALID_CONTRADICTING_ANCHOR"
    VALID_BUT_IRRELEVANT_ANCHOR = "VALID_BUT_IRRELEVANT_ANCHOR"
    VERIFIED_CONTEXT_ABSENCE = "VERIFIED_CONTEXT_ABSENCE"
    INVALID_CHUNK_ID = "INVALID_CHUNK_ID"
    INVALID_QUOTATION = "INVALID_QUOTATION"
    MISSING_REQUIRED_ANCHOR = "MISSING_REQUIRED_ANCHOR"
    ANCHOR_VALIDATION_ERROR = "ANCHOR_VALIDATION_ERROR"


class RetryEvent(BaseModel):
    """Diagnostic trace of an individual format or reference repair attempt."""
    attempt_index: int
    raw_output: str
    validation_error: str
    retry_prompt: str
    verdict_before_retry: Optional[int] = None
    verdict_after_retry: Optional[int] = None


class EvaluatorExecutionTrace(BaseModel):
    """Comprehensive execution trajectory recording Layer A validation and retries."""
    item_id: str = ""
    initial_raw_output: str = ""
    final_raw_output: str = ""
    initial_verdict: Optional[int] = None
    final_verdict: Optional[int] = None
    verdict_changed_by_retry: bool = False
    retries_used: int = 0
    retry_history: List[RetryEvent] = Field(default_factory=list)
    final_anchor_state: AnchorState = AnchorState.ANCHOR_VALIDATION_ERROR
    is_structural_failure: bool = False
    evaluator_error_code: Optional[str] = None


class RawJudgeStatementVerdict(BaseModel):
    """Strict JSON schema expected from LLM Judge output."""
    verdict: int = Field(..., description="1 if statement is entailed by context, 0 otherwise")
    reason: str = Field(..., description="Concise clinical explanation of grounding determination")
    cited_chunk_id: Optional[str] = Field(None, description="Primary supporting chunk identifier e.g. E1 or disease_chunk_60")
    cited_quote: Optional[str] = Field(None, description="Exact verbatim substring quotation from the cited chunk")
    is_absence_statement: Optional[bool] = Field(False, description="True if statement asserts absence/limitation in context")


class AtomicPropositionVerdict(BaseModel):
    """Individual atomic proposition evaluation."""
    proposition_text: str
    verdict: int
    reason: str
    cited_chunk_id: Optional[str] = None
    cited_quote: Optional[str] = None


class CalibratedStatementResult(BaseModel):
    """Complete evaluation outcome for an individual clinical statement."""
    item_id: str
    case_id: str
    statement: str
    verdict: Optional[int] = None  # None if structural/evaluator failure
    reason: str = ""
    anchor_state: AnchorState = AnchorState.ANCHOR_VALIDATION_ERROR
    cited_chunk_id: Optional[str] = None
    cited_quote: Optional[str] = None
    trace: EvaluatorExecutionTrace
    propositions: List[AtomicPropositionVerdict] = Field(default_factory=list)
    latency_ms: float = 0.0


class CaseEvaluationResult(BaseModel):
    """Aggregated evaluation outcome for a patient clinical case."""
    case_id: str
    statements: List[CalibratedStatementResult] = Field(default_factory=list)
    faithfulness_score: Optional[float] = None
    total_statements: int = 0
    supported_statements: int = 0
    unsupported_statements: int = 0
    invalid_statements: int = 0
