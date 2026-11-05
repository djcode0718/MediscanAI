"""Calibrated Clinical Faithfulness Evaluator Pipeline (Revision 2.4)."""

import os
import json
import time
import hashlib
import urllib.request
from typing import Dict, List, Optional, Tuple, Any

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
from .prompts import (
    B0_LEGACY_SYSTEM,
    EXP01_SYSTEM,
    EXP02_SYSTEM,
    EXP03_SYSTEM,
    EXP04_SYSTEM,
    EXP05_SYSTEM,
    EXP06_SYSTEM,
    EXP07_SYSTEM,
    CALIBRATED_COMBINED_SYSTEM,
    CALIBRATED_COMBINED_V2_SYSTEM
)

class CalibratedFaithfulnessEvaluator:
    """Production Calibrated Faithfulness Evaluator targeting llama3.1:8b via native Ollama API."""

    def __init__(
        self,
        experiment_id: str = "EXP-COMBINED",
        ollama_endpoint: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3.1:8b",
        cache_dir: Optional[str] = None
    ):
        self.experiment_id = experiment_id
        self.ollama_endpoint = ollama_endpoint
        self.model_name = model_name
        self.cache_dir = cache_dir
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)

    def _call_ollama(self, messages: List[Dict[str, str]]) -> Tuple[str, float]:
        """Calls native Ollama /api/chat with strictly enforced options."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "seed": 42,
                "num_ctx": 12288
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.ollama_endpoint,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
        latency_ms = (time.time() - t0) * 1000.0

        content = resp_data.get("message", {}).get("content", "")
        return content, latency_ms

    def _get_cache_key(self, statement: str, context_str: str) -> str:
        h = hashlib.sha256()
        h.update(self.experiment_id.encode("utf-8"))
        h.update(statement.encode("utf-8"))
        h.update(context_str.encode("utf-8"))
        return h.hexdigest()

    def evaluate_statement(
        self,
        item_id: str,
        case_id: str,
        statement: str,
        evidence_blocks: str
    ) -> CalibratedStatementResult:
        """Evaluates a single clinical statement according to the configured experiment mode."""
        cache_key = self._get_cache_key(statement, evidence_blocks)
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                with open(cache_file) as f:
                    cached_data = json.load(f)
                return CalibratedStatementResult.model_validate(cached_data)

        # Parse context chunks into list of dicts using robust multi-format parser
        context_chunks: List[Dict[str, str]] = StructuralValidator.parse_context_chunks(evidence_blocks)

        # Select prompt system based on experiment_id
        if self.experiment_id == "CTRL-B0":
            return self._run_b0_control(item_id, case_id, statement, evidence_blocks, context_chunks)
        elif self.experiment_id == "EXP-01":
            system_prompt = EXP01_SYSTEM
            use_layer_a = True
            use_atom = False
        elif self.experiment_id == "EXP-02":
            system_prompt = EXP02_SYSTEM
            use_layer_a = True
            use_atom = False
        elif self.experiment_id == "EXP-03":
            system_prompt = EXP03_SYSTEM
            use_layer_a = True
            use_atom = False
        elif self.experiment_id == "EXP-04":
            system_prompt = EXP04_SYSTEM
            use_layer_a = True
            use_atom = False
        elif self.experiment_id == "EXP-05":
            system_prompt = EXP05_SYSTEM
            use_layer_a = True
            use_atom = False
        elif self.experiment_id == "EXP-06":
            system_prompt = EXP06_SYSTEM
            use_layer_a = True
            use_atom = True
        elif self.experiment_id == "EXP-07":
            system_prompt = EXP07_SYSTEM
            use_layer_a = True
            use_atom = False
        elif self.experiment_id in ("EXP-COMBINED-V2", "EXP-COMBINED-CORRECTED", "EXP-COMBINED-ISOLATED"):
            system_prompt = CALIBRATED_COMBINED_V2_SYSTEM
            use_layer_a = True
            use_atom = True
        else: # EXP-COMBINED
            system_prompt = CALIBRATED_COMBINED_SYSTEM
            use_layer_a = True
            use_atom = True

        result = self._run_calibrated_pipeline(
            item_id, case_id, statement, evidence_blocks, context_chunks, system_prompt, use_layer_a, use_atom
        )

        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(cache_file, "w") as f:
                f.write(result.model_dump_json(indent=2))

        return result

    def _run_b0_control(
        self,
        item_id: str,
        case_id: str,
        statement: str,
        evidence_blocks: str,
        context_chunks: List[Dict[str, str]]
    ) -> CalibratedStatementResult:
        """Executes frozen uncalibrated legacy B0 evaluation."""
        user_prompt = f"context: {evidence_blocks}\nstatements: [\"{statement}\"]"
        messages = [
            {"role": "system", "content": B0_LEGACY_SYSTEM},
            {"role": "user", "content": user_prompt}
        ]

        raw_out, latency = self._call_ollama(messages)
        trace = EvaluatorExecutionTrace(
            item_id=item_id,
            initial_raw_output=raw_out,
            final_raw_output=raw_out,
            retries_used=0,
            final_anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR
        )

        try:
            parsed = json.loads(raw_out)
            stmts = parsed.get("statements", [])
            if stmts and isinstance(stmts, list):
                s0 = stmts[0]
                verdict = int(s0.get("verdict", 0))
                reason = s0.get("reason", "")
            else:
                verdict = int(parsed.get("verdict", 0))
                reason = parsed.get("reason", "")
        except Exception:
            # Legacy B0 converts parse error to unfaithfulness (verdict = 0)
            verdict = 0
            reason = "Failed to parse legacy JSON output"
            trace.is_structural_failure = True
            trace.evaluator_error_code = "LEGACY_PARSE_FAILURE"

        trace.initial_verdict = verdict
        trace.final_verdict = verdict

        return CalibratedStatementResult(
            item_id=item_id,
            case_id=case_id,
            statement=statement,
            verdict=verdict,
            reason=reason,
            anchor_state=AnchorState.VALID_SUPPORTING_ANCHOR if verdict == 1 else AnchorState.VALID_CONTRADICTING_ANCHOR,
            trace=trace,
            latency_ms=latency
        )

    def _run_calibrated_pipeline(
        self,
        item_id: str,
        case_id: str,
        statement: str,
        evidence_blocks: str,
        context_chunks: List[Dict[str, str]],
        system_prompt: str,
        use_layer_a: bool,
        use_atom: bool
    ) -> CalibratedStatementResult:
        """Executes calibrated pipeline with Layer A validation and optional atomic decomposition."""
        # 1. Pre-scan for scoped absence
        is_scoped_absence = AbsenceScanner.is_scoped_absence_statement(statement)

        # 2. Atomic proposition decomposition
        if use_atom:
            propositions = AtomicPropositionDecomposer.decompose(statement)
        else:
            propositions = [statement]

        prop_results = []
        overall_latency = 0.0

        for p_idx, prop_text in enumerate(propositions):
            user_msg = (
                f"RETRIEVED CONTEXT CHUNKS:\n{evidence_blocks}\n\n"
                f"CLINICAL STATEMENT TO EVALUATE:\n\"{prop_text}\"\n\n"
                f"Evaluate strictly against the chunks. Return JSON."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ]

            raw_out, latency = self._call_ollama(messages)
            overall_latency += latency

            envelope, err = StructuralValidator.validate_raw_json(raw_out)
            retry_history: List[RetryEvent] = []
            retries = 0

            # Layer A retry loop (max 2 retries)
            while err and retries < 2 and use_layer_a:
                retries += 1
                repair_prompt = StructuralValidator.build_format_repair_prompt(raw_out, err)
                retry_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": raw_out},
                    {"role": "user", "content": repair_prompt}
                ]
                retry_out, r_latency = self._call_ollama(retry_messages)
                overall_latency += r_latency

                new_envelope, new_err = StructuralValidator.validate_raw_json(retry_out)
                retry_history.append(RetryEvent(
                    attempt_index=retries,
                    raw_output=retry_out,
                    validation_error=err,
                    retry_prompt=repair_prompt,
                    verdict_before_retry=envelope.verdict if envelope else None,
                    verdict_after_retry=new_envelope.verdict if new_envelope else None
                ))
                raw_out = retry_out
                envelope = new_envelope
                err = new_err

            # Determine final status for this proposition
            if not envelope:
                # Structural failure decoupled: verdict = None, never candidate 0 penalty
                trace = EvaluatorExecutionTrace(
                    item_id=item_id,
                    initial_raw_output=raw_out,
                    final_raw_output=raw_out,
                    initial_verdict=None,
                    final_verdict=None,
                    retries_used=retries,
                    retry_history=retry_history,
                    final_anchor_state=AnchorState.ANCHOR_VALIDATION_ERROR,
                    is_structural_failure=True,
                    evaluator_error_code="PARSE_RETRY_EXHAUSTED"
                )
                return CalibratedStatementResult(
                    item_id=item_id,
                    case_id=case_id,
                    statement=statement,
                    verdict=None,
                    reason=f"Layer A structural failure: {err}",
                    anchor_state=AnchorState.ANCHOR_VALIDATION_ERROR,
                    trace=trace,
                    latency_ms=overall_latency
                )

            # Citation verification
            if use_layer_a:
                anchor_state, cite_err = StructuralValidator.verify_citations(
                    envelope, context_chunks, statement_text=prop_text
                )
                # Enforce citation integrity:
                # If envelope verdict is 1, it MUST have a valid supporting anchor or verified absence
                if envelope.verdict == 1 and anchor_state not in (AnchorState.VALID_SUPPORTING_ANCHOR, AnchorState.VERIFIED_CONTEXT_ABSENCE):
                    if cite_err and ("exception inconsistency" in str(cite_err).lower() or "dropped_exception" in str(cite_err).lower()):
                        # Clinical exception violation: statement overstates evidence; semantic failure verdict = 0
                        prop_verdict = 0
                        is_struct_fail = False
                        err_code = "DROPPED_CLINICAL_EXCEPTION"
                    else:
                        # Positive verdict rejected due to invalid citation anchor
                        prop_verdict = None
                        is_struct_fail = True
                        err_code = f"INVALID_ANCHOR_{anchor_state.value}"
                else:
                    prop_verdict = envelope.verdict
                    is_struct_fail = False
                    err_code = None
            else:
                anchor_state = AnchorState.VALID_SUPPORTING_ANCHOR if envelope.verdict == 1 else AnchorState.VALID_CONTRADICTING_ANCHOR
                prop_verdict = envelope.verdict
                is_struct_fail = False
                err_code = None

            # Scoped absence override if confirmed by context-aware absence verification
            if is_scoped_absence and envelope.verdict == 1 and anchor_state == AnchorState.VERIFIED_CONTEXT_ABSENCE:
                prop_verdict = 1

            prop_results.append((prop_verdict, envelope.reason, envelope.cited_chunk_id, envelope.cited_quote, anchor_state, raw_out, retries, retry_history, is_struct_fail, err_code))

        # Aggregate propositions (conjunction)
        prop_verdicts = [p[0] for p in prop_results]
        final_verdict = AtomicPropositionDecomposer.aggregate_verdicts(prop_verdicts)
        primary_reason = " | ".join([f"P{i+1}: {p[1]}" for i, p in enumerate(prop_results)])
        primary_chunk = prop_results[0][2]
        primary_quote = prop_results[0][3]
        final_anchor = prop_results[0][4]
        has_struct_fail = any(p[8] for p in prop_results)
        primary_err_code = next((p[9] for p in prop_results if p[9]), None)

        # Build execution trace
        trace = EvaluatorExecutionTrace(
            item_id=item_id,
            initial_raw_output=prop_results[0][5],
            final_raw_output=prop_results[0][5],
            initial_verdict=prop_results[0][0],
            final_verdict=final_verdict,
            verdict_changed_by_retry=any(len(p[7]) > 0 for p in prop_results),
            retries_used=sum(p[6] for p in prop_results),
            retry_history=prop_results[0][7],
            final_anchor_state=final_anchor,
            is_structural_failure=has_struct_fail,
            evaluator_error_code=primary_err_code
        )

        return CalibratedStatementResult(
            item_id=item_id,
            case_id=case_id,
            statement=statement,
            verdict=final_verdict,
            reason=primary_reason,
            anchor_state=final_anchor,
            cited_chunk_id=primary_chunk,
            cited_quote=primary_quote,
            trace=trace,
            latency_ms=overall_latency
        )
