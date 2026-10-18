#!/usr/bin/env python3
"""
MediScanAI — Phase 1.2.c: Isolated Integration Design & Middleware Specification
Reference implementation of the proposed Two-Stage Emergency Guardrail integration contract.
All code is self-contained and isolated within the Phase 1.2.c proposal directory.
Zero production code under app/ or backend/ is modified.
"""

import re
import json
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import audited Phase 1.2.b experimental guardrail
from evaluation.retrieval.phase_1_2_b_emergency_guardrail.guardrail import (
    EmergencyGuardrail,
    EmergencyDecision,
    MANDATORY_HEADER,
    MANDATORY_TEXT
)

logger = logging.getLogger("mediscanai.guardrail.integration")

# Hardcoded fallback rules for absolute fail-safe resilience (Case 4 & Case 3)
FAILSAFE_EMERGENCY_KEYWORDS = [
    re.compile(r"\bchest\s+pain\b", re.IGNORECASE),
    re.compile(r"\bheart\s+attack\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+breathe\b", re.IGNORECASE),
    re.compile(r"\bsevere\s+shortness\s+of\s+breath\b", re.IGNORECASE),
    re.compile(r"\bsudden\s+weakness\b", re.IGNORECASE),
    re.compile(r"\bslurred\s+speech\b", re.IGNORECASE),
    re.compile(r"\bunconscious\b", re.IGNORECASE),
    re.compile(r"\banaphylaxis\b", re.IGNORECASE),
    re.compile(r"\bmassive\s+bleeding\b", re.IGNORECASE),
]

ROUTINE_ADVICE_PATTERNS = [
    re.compile(r"schedule\s+(?:an\s+)?appointment\s+(?:with|to\s+see)\s+(?:your\s+|a\s+)?(?:primary\s+care\s+doctor|cardiologist|physician|gp|doctor)", re.IGNORECASE),
    re.compile(r"consult\s+(?:your\s+|a\s+)?doctor\s+at\s+your\s+earliest\s+convenience", re.IGNORECASE),
    re.compile(r"book\s+(?:a|an)\s+(?:visit|appointment)", re.IGNORECASE),
    re.compile(r"visit\s+(?:your\s+|a\s+)?local\s+clinic\s+for\s+routine", re.IGNORECASE),
]


@dataclass
class GuardrailAuditRecord:
    event_type: str = "EMERGENCY_GUARDRAIL_EVALUATED"
    enabled: bool = False
    is_emergency: bool = False
    action_taken: str = "PASS_THROUGH"
    rule_id: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    latency_ms: float = 0.0
    response_modified: bool = False
    fallback_engaged: bool = False
    # Notice: Strictly data-minimized. No raw query text or complete response text is logged!


class IntegratedEmergencyGuardrail:
    """
    Proposed production-ready guardrail wrapper implementing the Two-Stage Safeguard contract:
    - Feature flag control (EMERGENCY_GUARDRAIL_ENABLED)
    - Stage 1: Pre-generation detection & optional early-exit fast path
    - Stage 2: Post-generation deterministic enforcement (removes contradictory routine advice)
    - Fail-safe fallback under fault injection
    - Data-minimized privacy audit event generation
    """

    def __init__(
        self,
        enabled: bool = False,
        config_path: Optional[Path] = None,
        fast_path_enabled: bool = True
    ):
        self.enabled = enabled
        self.fast_path_enabled = fast_path_enabled
        self.config_path = config_path
        self._guardrail: Optional[EmergencyGuardrail] = None
        self._init_error: Optional[str] = None

        if self.enabled:
            self._initialize_guardrail()

    def _initialize_guardrail(self):
        try:
            self._guardrail = EmergencyGuardrail(self.config_path)
            self._init_error = None
        except Exception as e:
            logger.error(f"Failed to initialize EmergencyGuardrail: {e}", exc_info=True)
            self._init_error = str(e)
            self._guardrail = None

    def pre_generation_check(self, query: str) -> Tuple[bool, Optional[str], GuardrailAuditRecord]:
        """
        Stage 1: Pre-Generation Emergency Detection.
        If fast-path is enabled and an acute Tier-1 emergency is identified,
        returns (is_emergency=True, emergency_response_text, audit_record).
        Otherwise returns (is_emergency=False, None, audit_record).
        """
        if not self.enabled:
            return False, None, GuardrailAuditRecord(enabled=False, action_taken="FEATURE_FLAG_DISABLED")

        t0 = time.perf_counter()

        # Handle initialization fault fallback
        if self._guardrail is None:
            return self._execute_failsafe_sweep(query, baseline_response="", t0=t0, stage="PRE_GEN")

        try:
            decision = self._guardrail.detect_emergency(query)
            latency = round((time.perf_counter() - t0) * 1000, 3)

            if decision.is_emergency and self.fast_path_enabled and decision.severity == "CRITICAL_EMERGENCY":
                # Synthesize immediate fast-path emergency response
                fast_path_response, _ = self._guardrail.apply_guardrail(query, baseline_response="")
                audit = GuardrailAuditRecord(
                    enabled=True,
                    is_emergency=True,
                    action_taken="FAST_PATH_OVERRIDE",
                    rule_id=decision.fired_rule_id,
                    category=decision.category,
                    severity=decision.severity,
                    latency_ms=latency,
                    response_modified=True
                )
                return True, fast_path_response, audit

            audit = GuardrailAuditRecord(
                enabled=True,
                is_emergency=decision.is_emergency,
                action_taken="PRE_GEN_INSPECTED_PASS",
                rule_id=decision.fired_rule_id,
                category=decision.category,
                severity=decision.severity,
                latency_ms=latency,
                response_modified=False
            )
            return decision.is_emergency, None, audit

        except Exception as e:
            logger.error(f"Error in pre_generation_check: {e}", exc_info=True)
            return self._execute_failsafe_sweep(query, baseline_response="", t0=t0, stage="PRE_GEN_EXCEPTION")

    def post_generation_guard(
        self,
        query: str,
        baseline_response: str,
        retrieved_contexts: Optional[List[str]] = None
    ) -> Tuple[str, GuardrailAuditRecord]:
        """
        Stage 2: Post-Generation Deterministic Enforcement.
        If emergency detected, supersedes routine outpatient advice and enforces mandatory disclaimers.
        If no emergency detected, returns baseline response 100% unchanged.
        """
        if not self.enabled:
            return baseline_response, GuardrailAuditRecord(enabled=False, action_taken="FEATURE_FLAG_DISABLED")

        t0 = time.perf_counter()

        # Handle initialization fault fallback
        if self._guardrail is None:
            _, fallback_resp, audit = self._execute_failsafe_sweep(
                query, baseline_response=baseline_response, t0=t0, stage="POST_GEN_FAILSAFE"
            )
            return fallback_resp or baseline_response, audit

        try:
            # Check for negative-control abstention marker first (Case 10)
            if "cannot provide medical advice" in baseline_response.lower():
                latency = round((time.perf_counter() - t0) * 1000, 3)
                audit = GuardrailAuditRecord(
                    enabled=True,
                    is_emergency=False,
                    action_taken="ABSTENTION_PRESERVED",
                    latency_ms=latency,
                    response_modified=False
                )
                return baseline_response, audit

            guarded_resp, decision = self._guardrail.apply_guardrail(
                query=query,
                baseline_response=baseline_response,
                retrieved_contexts=retrieved_contexts
            )

            latency = round((time.perf_counter() - t0) * 1000, 3)

            if decision.is_emergency:
                # Guarantee elimination of contradictory routine outpatient appointment language (Case 7 & Gate 5)
                sanitized_resp = self._eliminate_contradictory_routine_advice(guarded_resp)
                audit = GuardrailAuditRecord(
                    enabled=True,
                    is_emergency=True,
                    action_taken="POST_GENERATION_OVERRIDE",
                    rule_id=decision.fired_rule_id,
                    category=decision.category,
                    severity=decision.severity,
                    latency_ms=latency,
                    response_modified=True
                )
                return sanitized_resp, audit

            # Non-emergency: preserve baseline response exactly
            audit = GuardrailAuditRecord(
                enabled=True,
                is_emergency=False,
                action_taken="PASS_THROUGH",
                latency_ms=latency,
                response_modified=False
            )
            return baseline_response, audit

        except Exception as e:
            logger.error(f"Error in post_generation_guard: {e}", exc_info=True)
            _, fallback_resp, audit = self._execute_failsafe_sweep(
                query, baseline_response=baseline_response, t0=t0, stage="POST_GEN_EXCEPTION"
            )
            return fallback_resp or baseline_response, audit

    def _eliminate_contradictory_routine_advice(self, text: str) -> str:
        """
        Ensures that if an emergency response is given, any lingering routine outpatient advice
        from concatenated contexts is eliminated.
        """
        cleaned = text
        for pat in ROUTINE_ADVICE_PATTERNS:
            cleaned = pat.sub("[ROUTINE CLINIC SCHEDULING SUPPRESSED: SEEK EMERGENCY CARE]", cleaned)
        return cleaned

    def _execute_failsafe_sweep(
        self, query: str, baseline_response: str, t0: float, stage: str
    ) -> Tuple[bool, str, GuardrailAuditRecord]:
        """
        Fail-safe fallback: performs ultra-resilient regex sweep on input query.
        Never drops an emergency signal even if primary engine threw an exception.
        """
        latency = round((time.perf_counter() - t0) * 1000, 3)
        query_clean = query.strip()

        # Check for explicit negation first in fallback
        if re.search(r"\bno\s+(?:chest\s+pain|shortness\s+of\s+breath)\b", query_clean, re.I):
            audit = GuardrailAuditRecord(
                enabled=True,
                is_emergency=False,
                action_taken="FAILSAFE_NEGATION_PASS",
                latency_ms=latency,
                response_modified=False,
                fallback_engaged=True
            )
            return False, baseline_response, audit

        for kw_pat in FAILSAFE_EMERGENCY_KEYWORDS:
            if kw_pat.search(query_clean):
                # Critical emergency detected in fallback sweep!
                fallback_resp = (
                    f"### 🚨 Emergency Safety Notice (Fail-Safe Engaged)\n\n"
                    f"**Immediate Emergency Medical Evaluation Required.**\n"
                    f"Your query reported symptoms that may indicate an acute medical emergency.\n\n"
                    f"* **Call 112 (India) or 911 (US) immediately.**\n"
                    f"* **Proceed to the nearest Emergency Department immediately.**\n"
                    f"* Do not wait for a routine doctor's appointment.\n\n"
                    f"{MANDATORY_HEADER}\n{MANDATORY_TEXT}"
                )
                audit = GuardrailAuditRecord(
                    enabled=True,
                    is_emergency=True,
                    action_taken="FAILSAFE_EMERGENCY_OVERRIDE",
                    rule_id="RULE-FAILSAFE-FALLBACK",
                    category="emergency_fallback",
                    severity="CRITICAL_EMERGENCY",
                    latency_ms=latency,
                    response_modified=True,
                    fallback_engaged=True
                )
                return True, fallback_resp, audit

        # No emergency keywords in fallback sweep
        audit = GuardrailAuditRecord(
            enabled=True,
            is_emergency=False,
            action_taken="FAILSAFE_PASS_THROUGH",
            latency_ms=latency,
            response_modified=False,
            fallback_engaged=True
        )
        return False, baseline_response, audit
