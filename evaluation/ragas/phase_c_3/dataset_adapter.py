#!/usr/bin/env python3
"""
MediScanAI — Phase C.3 Ragas Dataset Adapter
Converts MediScanAI evaluation records (retrievals, model responses, reference answers)
into the exact format required by Ragas 0.2.15 (HuggingFace Dataset and EvaluationDataset).
Preserves case IDs, track distinctions (baseline vs graph), provenance, and model metadata.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datasets import Dataset
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset


@dataclass
class RagasEvaluationRecord:
    case_id: str
    query: str
    retrieved_contexts: List[str]
    response: str
    reference: Optional[str] = None
    track: str = "baseline"  # "baseline" or "graph"
    retrieved_source_ids: Optional[List[str]] = None
    model: str = "llama3.1:8b"
    prompt_version: str = "phase_c_2_v1"
    reference_provenance: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> List[str]:
        """Validates that the record contains all required fields for Ragas evaluation."""
        errors = []
        if not self.case_id or not self.case_id.strip():
            errors.append("case_id cannot be empty")
        if not self.query or not self.query.strip():
            errors.append("query cannot be empty")
        if not isinstance(self.retrieved_contexts, list) or len(self.retrieved_contexts) == 0:
            errors.append("retrieved_contexts must be a non-empty list of strings")
        if not self.response or not self.response.strip():
            errors.append("response cannot be empty")
        if self.track not in ("baseline", "graph", "synthetic_test"):
            errors.append(f"track must be 'baseline', 'graph', or 'synthetic_test', got '{self.track}'")
        return errors

    def to_ragas_dict(self) -> Dict[str, Any]:
        """Converts to dictionary formatted for HuggingFace Dataset consumption by Ragas 0.2.x."""
        return {
            "user_input": self.query,
            "response": self.response,
            "retrieved_contexts": self.retrieved_contexts,
            "reference": self.reference if self.reference is not None else "",
            # Metadata columns preserved for auditability
            "case_id": self.case_id,
            "track": self.track,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "retrieved_source_ids": self.retrieved_source_ids or []
        }

    def to_single_turn_sample(self) -> SingleTurnSample:
        """Converts to Ragas SingleTurnSample object."""
        kwargs: Dict[str, Any] = {
            "user_input": self.query,
            "response": self.response,
            "retrieved_contexts": self.retrieved_contexts,
        }
        if self.reference:
            kwargs["reference"] = self.reference
        return SingleTurnSample(**kwargs)


class RagasDatasetAdapter:
    """Standalone adapter converting MediScanAI benchmark records to Ragas datasets."""

    @staticmethod
    def create_hf_dataset(records: List[RagasEvaluationRecord]) -> Dataset:
        """
        Converts a list of RagasEvaluationRecord objects into a HuggingFace Dataset
        with the schema expected by Ragas evaluate().
        """
        if not records:
            raise ValueError("Cannot create dataset from empty record list")

        for r in records:
            errs = r.validate()
            if errs:
                raise ValueError(f"Validation failure for case {r.case_id}: {'; '.join(errs)}")

        data = {
            "user_input": [r.query for r in records],
            "response": [r.response for r in records],
            "retrieved_contexts": [r.retrieved_contexts for r in records],
            "reference": [r.reference if r.reference else "" for r in records],
            "case_id": [r.case_id for r in records],
            "track": [r.track for r in records],
            "model": [r.model for r in records],
            "prompt_version": [r.prompt_version for r in records],
            "retrieved_source_ids": [r.retrieved_source_ids or [] for r in records],
        }
        return Dataset.from_dict(data)

    @staticmethod
    def create_evaluation_dataset(records: List[RagasEvaluationRecord]) -> EvaluationDataset:
        """Converts records into a Ragas EvaluationDataset containing SingleTurnSample objects."""
        samples = [r.to_single_turn_sample() for r in records]
        return EvaluationDataset(samples=samples)

    @staticmethod
    def filter_by_track(records: List[RagasEvaluationRecord], track: str) -> List[RagasEvaluationRecord]:
        """Separates records by track ('baseline' vs 'graph') to enforce isolated comparison."""
        return [r for r in records if r.track == track]
