"""Dedicated Synthetic Regression Suite for MediScanAI Calibrated Evaluator (Revision 2.4)."""

import os
import json
import time
from typing import Dict, List, Any
from pydantic import BaseModel, Field

from .models import AnchorState, RawJudgeStatementVerdict
from .structural_validator import StructuralValidator
from .absence_scanner import AbsenceScanner
from .atomic_decomposer import AtomicPropositionDecomposer
from .calibrated_faithfulness import CalibratedFaithfulnessEvaluator

class SyntheticTestCase(BaseModel):
    test_id: str
    category: str
    is_positive_case: bool
    description: str
    context_chunks: List[Dict[str, str]]
    statement: str
    expected_verdict: int
    expected_anchor_state: AnchorState
    expected_failure_reason: str = ""

def get_synthetic_test_suite() -> List[SyntheticTestCase]:
    """Returns the authoritative 20-case minimal pair synthetic regression suite."""
    suite = [
        # 1. Direct Entailment
        SyntheticTestCase(
            test_id="SYNTH-ENTAIL-POS",
            category="Direct Entailment",
            is_positive_case=True,
            description="Evidence directly states indication",
            context_chunks=[{"chunk_id": "E1", "text": "Amlodipine is indicated for the treatment of hypertension to lower blood pressure."}],
            statement="Amlodipine is used to treat high blood pressure.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-ENTAIL-NEG",
            category="Direct Entailment",
            is_positive_case=False,
            description="Evidence does not support unsupported indication",
            context_chunks=[{"chunk_id": "E1", "text": "Amlodipine is indicated for the treatment of hypertension to lower blood pressure."}],
            statement="Amlodipine is indicated for acute gastrointestinal hemorrhage.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 2. Scoped Abstention
        SyntheticTestCase(
            test_id="SYNTH-ABST-POS",
            category="Scoped Abstention",
            is_positive_case=True,
            description="Correctly qualified evidence-scoped absence statement",
            context_chunks=[{"chunk_id": "E1", "text": "Adult dosage: 50 mg daily. Renal adjustment: 25 mg daily."}],
            statement="The available sources do not provide pediatric dosing recommendations.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VERIFIED_CONTEXT_ABSENCE
        ),
        SyntheticTestCase(
            test_id="SYNTH-ABST-NEG",
            category="Scoped Abstention",
            is_positive_case=False,
            description="Improper global ontological nonexistence claim",
            context_chunks=[{"chunk_id": "E1", "text": "Adult dosage: 50 mg daily."}],
            statement="Pediatric dosing for this medication does not exist in medical science.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 3. Entity Attribution Binding (EPOETIN/PROCRIT mandatory regression)
        SyntheticTestCase(
            test_id="SYNTH-ENTITY-POS",
            category="Entity Attribution Binding",
            is_positive_case=True,
            description="Mandatory EPOETIN/PROCRIT field binding scenario",
            context_chunks=[{"chunk_id": "E1", "text": "Brand: PROCRIT | Active ingredients: EPOETIN | Form: sterile solution"}],
            statement="PROCRIT lists EPOETIN as an active ingredient.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-ENTITY-NEG",
            category="Entity Attribution Binding",
            is_positive_case=False,
            description="Cross-entity symptom and attribute transference",
            context_chunks=[
                {"chunk_id": "E1", "text": "Condition: Atrial Fibrillation | Symptoms: palpitations, dyspnea."},
                {"chunk_id": "E2", "text": "Condition: Epilepsy | Symptoms: recurrent seizures, myoclonic jerks."}
            ],
            statement="Atrial Fibrillation causes recurrent seizures.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 4. Clinical & Statutory Synonymy
        SyntheticTestCase(
            test_id="SYNTH-SYNONYM-POS",
            category="Clinical Synonymy",
            is_positive_case=True,
            description="Standard statutory equivalent Rx Only* to prescription required",
            context_chunks=[{"chunk_id": "E1", "text": "Lipitor (atorvastatin calcium) tablets. Rx Only*. Store at 20-25C."}],
            statement="Lipitor is a prescription-only medication.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-SYNONYM-NEG",
            category="Clinical Synonymy",
            is_positive_case=False,
            description="Prohibited regulatory level swap: OTC to prescription-only",
            context_chunks=[{"chunk_id": "E1", "text": "Cetirizine hydrochloride 10mg tablets. Over-The-Counter (OTC)."}],
            statement="Cetirizine requires a doctor prescription to purchase.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 5. Compound Claims
        SyntheticTestCase(
            test_id="SYNTH-COMPOUND-POS",
            category="Compound Claims",
            is_positive_case=True,
            description="All material propositions supported by context",
            context_chunks=[
                {"chunk_id": "E1", "text": "Metformin reduces hepatic glucose production and improves insulin sensitivity."}
            ],
            statement="Metformin reduces hepatic glucose production and improves insulin sensitivity.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-COMPOUND-NEG",
            category="Compound Claims",
            is_positive_case=False,
            description="One material proposition supported but second proposition fabricated",
            context_chunks=[
                {"chunk_id": "E1", "text": "Metformin reduces hepatic glucose production."}
            ],
            statement="Metformin reduces hepatic glucose production and completely cures Type 2 diabetes permanently.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 6. Cross-Chunk Synthesis
        SyntheticTestCase(
            test_id="SYNTH-CROSSCHUNK-POS",
            category="Cross-Chunk Synthesis",
            is_positive_case=True,
            description="Multiple chunks jointly establish clinical adjustment",
            context_chunks=[
                {"chunk_id": "E1", "text": "Patient has severe renal impairment with CrCl = 25 mL/min."},
                {"chunk_id": "E2", "text": "Standard normal maintenance dose is 50 mg once daily."},
                {"chunk_id": "E3", "text": "For patients with CrCl < 30 mL/min, reduce normal dose by 50%."}
            ],
            statement="The renal-adjusted maintenance dose for this patient is 25 mg once daily.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-CROSSCHUNK-NEG",
            category="Cross-Chunk Synthesis",
            is_positive_case=False,
            description="Evidence does not jointly support incorrectly calculated dosage",
            context_chunks=[
                {"chunk_id": "E1", "text": "Patient has severe renal impairment with CrCl = 25 mL/min."},
                {"chunk_id": "E2", "text": "Standard normal maintenance dose is 50 mg once daily."},
                {"chunk_id": "E3", "text": "For patients with CrCl < 30 mL/min, reduce normal dose by 50%."}
            ],
            statement="The renal-adjusted maintenance dose for this patient is 100 mg once daily.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 7. Direct Contradiction
        SyntheticTestCase(
            test_id="SYNTH-CONTRADICT-POS",
            category="Direct Contradiction",
            is_positive_case=True,
            description="Claim aligns with documented administration instructions",
            context_chunks=[{"chunk_id": "E1", "text": "Administer orally with or without food. Do not crush or chew."}],
            statement="Take orally and swallow whole without crushing.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-CONTRADICT-NEG",
            category="Direct Contradiction",
            is_positive_case=False,
            description="Claim directly contradicts explicit contraindication",
            context_chunks=[{"chunk_id": "E1", "text": "Administer orally with or without food. Do not crush or chew."}],
            statement="Crush thoroughly and dissolve in liquid before ingestion.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 8. Structural Validation
        SyntheticTestCase(
            test_id="SYNTH-STRUCT-POS",
            category="Structural Validation",
            is_positive_case=True,
            description="Valid citation and exact verbatim quotation substring",
            context_chunks=[{"chunk_id": "E1", "text": "Store at 20°C to 25°C (68°F to 77°F); excursions permitted between 15°C and 30°C."}],
            statement="Permitted storage excursions are between 15°C and 30°C.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-STRUCT-NEG",
            category="Structural Validation",
            is_positive_case=False,
            description="Quotation not present in context chunks",
            context_chunks=[{"chunk_id": "E1", "text": "Store at 20°C to 25°C."}],
            statement="Must be stored at cryogenic sub-zero temperatures.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 9. Format Retry & Trajectory
        SyntheticTestCase(
            test_id="SYNTH-RETRY-POS",
            category="Retry Behavior",
            is_positive_case=True,
            description="Successfully parsed and structured output",
            context_chunks=[{"chunk_id": "E1", "text": "Indicated as an adjunct to diet and exercise in adults with type 2 diabetes."}],
            statement="Indicated for adults with type 2 diabetes mellitus alongside diet and exercise.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-RETRY-NEG",
            category="Retry Behavior",
            is_positive_case=False,
            description="Exhausted structural parsing failure decoupled from candidate verdict",
            context_chunks=[{"chunk_id": "E1", "text": "Some text."}],
            statement="Some unrelated statement.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),

        # 10. Redundancy Decoupling
        SyntheticTestCase(
            test_id="SYNTH-REDUND-POS",
            category="Redundancy Decoupling",
            is_positive_case=True,
            description="First occurrence of grounded clinical fact",
            context_chunks=[{"chunk_id": "E1", "text": "Common adverse reactions include nausea, diarrhea, and headache."}],
            statement="Headache is a common adverse reaction.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),
        SyntheticTestCase(
            test_id="SYNTH-REDUND-REPEAT",
            category="Redundancy Decoupling",
            is_positive_case=True,
            description="Repeated occurrence of grounded fact receives zero penalty",
            context_chunks=[{"chunk_id": "E1", "text": "Common adverse reactions include nausea, diarrhea, and headache."}],
            statement="Headache is a documented adverse effect.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        ),

        # 11. Targeted Abstention Boundary (Revision 2.4 - Option B)
        # 11.1 Evidence-scoped missing dosage (Positive)
        SyntheticTestCase(
            test_id="SYNTH-ABST-MISSING-DOSAGE-POS",
            category="Targeted Abstention Boundary",
            is_positive_case=True,
            description="Evidence-scoped missing dosage statement correctly reports absence in sources",
            context_chunks=[{"chunk_id": "E1", "text": "Amlodipine is indicated for hypertension in adult patients. Dosage: 5-10 mg daily."}],
            statement="Available sources do not provide pediatric dosing recommendations for amlodipine.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VERIFIED_CONTEXT_ABSENCE
        ),
        # 11.2 Fabricated treatment with affirmative dosage assertion (Negative)
        SyntheticTestCase(
            test_id="SYNTH-ABST-FABRICATED-DOSAGE-NEG",
            category="Targeted Abstention Boundary",
            is_positive_case=False,
            description="Fabricated dosage recommendation without evidence support",
            context_chunks=[{"chunk_id": "E1", "text": "Amlodipine is indicated for hypertension in adult patients. Dosage: 5-10 mg daily."}],
            statement="Administer 100 mg of amlodipine intravenously every 2 hours for acute hypertension.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),
        # 11.3 Evidence-scoped missing indication (Positive)
        SyntheticTestCase(
            test_id="SYNTH-ABST-MISSING-INDICATION-POS",
            category="Targeted Abstention Boundary",
            is_positive_case=True,
            description="Evidence-scoped missing indication statement accurately reports absence in evidence",
            context_chunks=[{"chunk_id": "E1", "text": "Metformin is indicated as an adjunct to diet and exercise in adults with type 2 diabetes."}],
            statement="Retrieved evidence does not state whether metformin is indicated for acute migraine headaches.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VERIFIED_CONTEXT_ABSENCE
        ),
        # 11.4 Entity mentioned in another context but not supported for claimed indication (Negative)
        SyntheticTestCase(
            test_id="SYNTH-ABST-UNSUPPORTED-INDICATION-NEG",
            category="Targeted Abstention Boundary",
            is_positive_case=False,
            description="Entity present in context but affirmative indication claim is unsupported",
            context_chunks=[{"chunk_id": "E1", "text": "Metformin is indicated as an adjunct to diet and exercise in adults with type 2 diabetes."}],
            statement="Metformin is indicated for treating acute migraine headaches.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),
        # 11.5 Fabricated entity in a treatment recommendation / ADJ-0128 minimal pair (Negative)
        SyntheticTestCase(
            test_id="SYNTH-ABST-ADJ0128-CHOCOLATE-NEG",
            category="Targeted Abstention Boundary",
            is_positive_case=False,
            description="Mandatory ADJ-0128 regression: ungrounded affirmative clinical recommendation disguised with negative phrasing",
            context_chunks=[
                {"chunk_id": "E1", "text": "Clemastine Fumarate Syrup is indicated for allergic rhinitis."},
                {"chunk_id": "E2", "text": "Ranitidine Syrup is indicated for active duodenal ulcer."}
            ],
            statement="The clinical dosage of chocolate syrup is not recommended for treating acute appendicitis.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),
        # 11.6 Genuine supported medical limitation statement on ungrounded entity (Positive minimal pair with 11.5)
        SyntheticTestCase(
            test_id="SYNTH-ABST-UNGROUNDED-LIMITATION-POS",
            category="Targeted Abstention Boundary",
            is_positive_case=True,
            description="Genuine evidence-scoped limitation accurately reporting that ungrounded entity is omitted from sources",
            context_chunks=[
                {"chunk_id": "E1", "text": "Clemastine Fumarate Syrup is indicated for allergic rhinitis."},
                {"chunk_id": "E2", "text": "Ranitidine Syrup is indicated for active duodenal ulcer."}
            ],
            statement="Available sources do not contain information regarding chocolate syrup for appendicitis.",
            expected_verdict=1,
            expected_anchor_state=AnchorState.VERIFIED_CONTEXT_ABSENCE
        ),
        # 11.7 Global nonexistence claim (Negative)
        SyntheticTestCase(
            test_id="SYNTH-ABST-GLOBAL-NONEXIST-NEG",
            category="Targeted Abstention Boundary",
            is_positive_case=False,
            description="Universal nonexistence assertion exceeding retrieved context scope",
            context_chunks=[{"chunk_id": "E1", "text": "Atorvastatin is indicated for reduction of LDL-C and prevention of cardiovascular disease."}],
            statement="There is no scientific evidence anywhere in medical literature that statins lower cholesterol.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        ),
        # 11.8 Unsupported safety assertion (Negative)
        SyntheticTestCase(
            test_id="SYNTH-ABST-UNSUPPORTED-SAFETY-NEG",
            category="Targeted Abstention Boundary",
            is_positive_case=False,
            description="Unsupported affirmative clinical safety claim without context documentation",
            context_chunks=[{"chunk_id": "E1", "text": "Lisinopril is indicated for hypertension. Common adverse reactions include dizziness, headache, and cough."}],
            statement="Lisinopril is completely harmless and has no contraindications or adverse effects.",
            expected_verdict=0,
            expected_anchor_state=AnchorState.VALID_CONTRADICTING_ANCHOR
        )
    ]
    return suite
