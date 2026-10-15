#!/usr/bin/env python3
"""
MediScanAI — Phase C.3 Ragas Dataset Adapter
Re-exports from phase_c_3.dataset_adapter for root evaluation accessibility.
"""
from evaluation.ragas.phase_c_3.dataset_adapter import (
    RagasEvaluationRecord,
    RagasDatasetAdapter,
)

__all__ = ["RagasEvaluationRecord", "RagasDatasetAdapter"]
