"""
MediScanAI — Phase D.2.b: Cross-Encoder Threshold Calibrator

Evaluates score distributions, false acceptances, and false rejections
across calibrated thresholds on Development data only.
Outputs calibration statistics to threshold_calibration.json.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np


class ThresholdCalibrator:
    """
    Calibrates cross-encoder score cutoffs on Development queries.
    """

    def __init__(self, thresholds: Optional[List[float]] = None):
        if thresholds is None:
            self.thresholds = [None, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0]
        else:
            self.thresholds = thresholds

    def analyze_thresholds(
        self,
        scored_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Computes TP, FP, TN, FN, False Acceptance, and False Rejection across thresholds.
        Each item in scored_cases:
        {
            "case_id": str,
            "is_answerable": bool,
            "candidates": List[{"eid": str, "score": float, "is_relevant": bool}]
        }
        """
        results_by_thresh = {}

        for tau in self.thresholds:
            t_label = "no_threshold" if tau is None else f"tau_{tau:+.1f}"

            total_gold_relevant = 0
            true_positives = 0
            false_rejections = 0  # Gold relevant rejected by threshold
            false_acceptances = 0 # Irrelevant or negative control accepted above threshold
            true_negatives = 0

            neg_control_total = 0
            neg_control_clean_abstentions = 0

            for c in scored_cases:
                is_ans = c["is_answerable"]
                cands = c["candidates"]

                if not is_ans:
                    neg_control_total += 1
                    # In negative control, any candidate above threshold is a false acceptance
                    accepted = [cand for cand in cands if (tau is None or cand["score"] >= tau)]
                    if len(accepted) == 0:
                        neg_control_clean_abstentions += 1
                    else:
                        false_acceptances += len(accepted)
                else:
                    for cand in cands:
                        is_rel = cand["is_relevant"]
                        sc = cand["score"]
                        is_above = (tau is None or sc >= tau)

                        if is_rel:
                            total_gold_relevant += 1
                            if is_above:
                                true_positives += 1
                            else:
                                false_rejections += 1
                        else:
                            if is_above:
                                false_acceptances += 1
                            else:
                                true_negatives += 1

            recall = true_positives / float(total_gold_relevant) if total_gold_relevant > 0 else 0.0
            precision = true_positives / float(true_positives + false_acceptances) if (true_positives + false_acceptances) > 0 else 0.0
            rejection_acc = neg_control_clean_abstentions / float(neg_control_total) if neg_control_total > 0 else 0.0

            results_by_thresh[t_label] = {
                "threshold_value": tau,
                "true_positives": true_positives,
                "false_rejections": false_rejections,
                "false_acceptances": false_acceptances,
                "true_negatives": true_negatives,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0,
                "negative_control_rejection_acc": round(rejection_acc, 4),
            }

        return results_by_thresh
