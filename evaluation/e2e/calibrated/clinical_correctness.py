"""Layer C: Independent Clinical Correctness Assessor (Revision 2.4)."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class ClinicalReferenceStandard(BaseModel):
    """Specification of authoritative clinical reference source."""
    source_tier: int = Field(..., description="Tier 1 (FDA SPL), Tier 2 (USP-NF), Tier 3 (AHA/ACC etc), Tier 4 (Compendia)")
    source_title: str
    revision_date: str
    section: str
    jurisdiction: str = "US"
    target_population: str = "General"
    curator_credentials: Optional[str] = None


class OrthogonalEvaluationResult(BaseModel):
    """Orthogonal 2x2 Faithfulness x Clinical Correctness classification."""
    item_id: str
    statement: str
    faithfulness_verdict: Optional[int] = None
    clinical_correctness_verdict: Optional[int] = None
    quadrant: Optional[str] = Field(None, description="Q1: Faithful & True, Q2: Faithful & False, Q3: Hallucinated & True, Q4: Hallucinated & False")
    risk_classification: Optional[str] = None
    status: str = "COMPLETED"


class ClinicalCorrectnessAssessor:
    """Evaluates clinical correctness independently from retrieved context."""

    QUADRANT_DEFINITIONS = {
        (1, 1): ("Q1_FAITHFUL_AND_TRUE", "Ideal RAG Execution (Clinically Safe)"),
        (1, 0): ("Q2_FAITHFUL_BUT_FALSE", "Retrieval Index Corruption Defect (High Risk)"),
        (0, 1): ("Q3_HALLUCINATED_BUT_TRUE", "Parametric Memory Fallback (Moderate Risk)"),
        (0, 0): ("Q4_HALLUCINATED_AND_FALSE", "Critical Model Hallucination (Severe Hazard)")
    }

    @classmethod
    def classify_quadrant(
        cls,
        item_id: str,
        statement: str,
        faithfulness_verdict: Optional[int],
        clinical_correctness_label: Optional[int]
    ) -> OrthogonalEvaluationResult:
        """Assigns the 2x2 quadrant if both verdicts exist, or returns pending."""
        if faithfulness_verdict is None or clinical_correctness_label is None:
            return OrthogonalEvaluationResult(
                item_id=item_id,
                statement=statement,
                faithfulness_verdict=faithfulness_verdict,
                clinical_correctness_verdict=clinical_correctness_label,
                quadrant=None,
                risk_classification="PENDING_HUMAN_CLINICAL_GROUND_TRUTH",
                status="AWAITING_REFERENCE_LABEL"
            )

        quadrant_key = (faithfulness_verdict, clinical_correctness_label)
        q_code, q_desc = cls.QUADRANT_DEFINITIONS.get(quadrant_key, ("UNKNOWN", "Undefined Quadrant"))

        return OrthogonalEvaluationResult(
            item_id=item_id,
            statement=statement,
            faithfulness_verdict=faithfulness_verdict,
            clinical_correctness_verdict=clinical_correctness_label,
            quadrant=q_code,
            risk_classification=q_desc,
            status="COMPLETED"
        )
