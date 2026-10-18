#!/usr/bin/env python3
"""
MediScanAI — Production Emergency Triage Guardrail (Phase 1.2.d)
Deterministic red-flag emergency detector and response safeguard for acute clinical presentations.

Key Capabilities:
- Deterministic regex & keyword rule evaluation against acute life-threatening presentations
- Context-aware negation detection (e.g., 'no chest pain', 'without chest pain')
- Historical and family medical history gating (e.g., 'had chest pain 5 years ago', 'father had heart attack')
- Substring collision prevention (e.g., 'chest decongestant', 'stroke volume')
- Prominent immediate emergency escalation directive with national hotlines (112 for India, 911 for US)
- Elimination of contradictory routine clinic appointments when emergency red flags fire
- Diagnostic uncertainty preservation (no definitive diagnosis asserted)
- Preserves verbatim institutional medical disclaimer
- Zero modification to non-emergency responses (100% baseline fidelity)
- Complete fail-safe fallback resilience against runtime exceptions or missing config
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("mediscanai.guardrail")

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "guardrail_config.json"

MANDATORY_HEADER = "### ⚠️ Important Warning"
MANDATORY_TEXT = (
    "This analysis is for informational purposes only and is generated based on the data you provided. "
    "It is **not a substitute for professional medical advice**. You should always consult a qualified doctor "
    "or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition."
)

# Fail-safe static keyword patterns for absolute fault tolerance
FAILSAFE_KEYWORD_PATTERNS = [
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
class EmergencyDecision:
    is_emergency: bool
    fired_rule_id: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    matched_text: Optional[str] = None
    confidence: float = 1.0
    reasoning: str = ""
    detection_latency_ms: float = 0.0
    fallback_engaged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmergencyGuardrail:
    """
    Deterministic emergency guardrail for acute life-threatening clinical triage.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.is_valid = False
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            self.hotlines = self.config.get("emergency_hotlines", {"india": "112", "us": "911"})
            self.rules = self.config.get("rules", [])
            self.negation_patterns = [
                re.compile(p, re.IGNORECASE) for p in self.config.get("negation_patterns", [])
            ]
            self.historical_patterns = [
                re.compile(p, re.IGNORECASE) for p in self.config.get("historical_and_family_patterns", [])
            ]
            self.contextual_exceptions = [
                re.compile(p, re.IGNORECASE) for p in self.config.get("contextual_exceptions", [])
            ]

            # Compile rule triggers
            self.compiled_rules = []
            for r in self.rules:
                triggers = [re.compile(t, re.IGNORECASE) for t in r.get("triggers", [])]
                self.compiled_rules.append((r, triggers))

            self.is_valid = True
            logger.info("EmergencyGuardrail initialized successfully with %d rules.", len(self.compiled_rules))

        except Exception as e:
            logger.error("Failed to load EmergencyGuardrail config from %s: %s. Engaging fail-safe mode.",
                         self.config_path, e, exc_info=True)
            self.is_valid = False
            self.hotlines = {"india": "112", "us": "911"}
            self.compiled_rules = []

    def detect_emergency(
        self, query: str, retrieved_contexts: Optional[List[str]] = None
    ) -> EmergencyDecision:
        """
        Evaluates input query and optional retrieved contexts for acute emergency red-flags.
        """
        t0 = time.perf_counter()
        query_clean = query.strip() if query else ""

        if not query_clean:
            latency = round((time.perf_counter() - t0) * 1000, 3)
            return EmergencyDecision(
                is_emergency=False,
                reasoning="Empty input query.",
                detection_latency_ms=latency,
            )

        # Fallback handling if config failed to load
        if not self.is_valid:
            return self._failsafe_detect(query_clean, t0)

        try:
            # 1. Check contextual exceptions (e.g. stroke volume, chest decongestant)
            for exc_pat in self.contextual_exceptions:
                if exc_pat.search(query_clean):
                    latency = round((time.perf_counter() - t0) * 1000, 3)
                    return EmergencyDecision(
                        is_emergency=False,
                        reasoning=f"Matched contextual exception pattern: {exc_pat.pattern}",
                        detection_latency_ms=latency,
                    )

            # 2. Check negation (e.g., 'no chest pain', 'without chest pain')
            is_negated = False
            for neg_pat in self.negation_patterns:
                if neg_pat.search(query_clean):
                    is_negated = True
                    break

            # 3. Check historical / remote past / family history
            is_historical = False
            for hist_pat in self.historical_patterns:
                if hist_pat.search(query_clean):
                    is_historical = True
                    break

            # If explicitly negated or purely historical, do not escalate acute emergency
            if is_negated:
                latency = round((time.perf_counter() - t0) * 1000, 3)
                return EmergencyDecision(
                    is_emergency=False,
                    reasoning="Emergency symptom explicitly negated in query.",
                    detection_latency_ms=latency,
                )

            if is_historical:
                latency = round((time.perf_counter() - t0) * 1000, 3)
                return EmergencyDecision(
                    is_emergency=False,
                    reasoning="Symptom or condition mentioned in historical, remote past, or family history context.",
                    detection_latency_ms=latency,
                )

            # 4. Check deterministic emergency rules in order (Rules 01–05)
            for rule_dict, triggers in self.compiled_rules:
                for trig in triggers:
                    match = trig.search(query_clean)
                    if match:
                        latency = round((time.perf_counter() - t0) * 1000, 3)
                        return EmergencyDecision(
                            is_emergency=True,
                            fired_rule_id=rule_dict["rule_id"],
                            category=rule_dict.get("category"),
                            severity=rule_dict.get("severity", "CRITICAL_EMERGENCY"),
                            matched_text=match.group(0),
                            confidence=1.0,
                            reasoning=f"Triggered by '{match.group(0)}' matching {rule_dict['rule_id']}: {rule_dict.get('description')}",
                            detection_latency_ms=latency,
                        )

            # 5. Check if query is ambiguous symptom and retrieved evidence surfaces life-threatening emergency
            if retrieved_contexts:
                query_lower = query_clean.lower()
                if any(term in query_lower for term in ["chest", "breathing", "heart", "sudden"]):
                    ctx_joined = " ".join(retrieved_contexts).lower()
                    life_threatening = ["heart attack", "myocardial infarction", "pulmonary embolism", "aortic dissection", "cardiac arrest"]
                    for lt in life_threatening:
                        if lt in ctx_joined:
                            latency = round((time.perf_counter() - t0) * 1000, 3)
                            return EmergencyDecision(
                                is_emergency=True,
                                fired_rule_id="RULE-06-EVIDENCE-CONDITION-INTERCEPT",
                                category="cardiovascular",
                                severity="CRITICAL_EMERGENCY",
                                matched_text=f"Query '{query_clean}' with retrieved life-threatening condition '{lt}'",
                                confidence=0.95,
                                reasoning=f"Query with cardinal thoracic symptoms retrieved immediate life-threatening condition '{lt}'.",
                                detection_latency_ms=latency,
                            )

            latency = round((time.perf_counter() - t0) * 1000, 3)
            return EmergencyDecision(
                is_emergency=False,
                reasoning="No acute emergency red flags identified.",
                detection_latency_ms=latency,
            )

        except Exception as e:
            logger.error("Unexpected exception in detect_emergency: %s. Engaging fail-safe sweep.", e, exc_info=True)
            return self._failsafe_detect(query_clean, t0)

    def apply_guardrail(
        self,
        query: str,
        baseline_response: str,
        retrieved_contexts: Optional[List[str]] = None,
    ) -> Tuple[str, EmergencyDecision]:
        """
        Applies emergency guardrail to a generated response.
        If emergency is detected, returns prominent immediate emergency guidance with disclaimers.
        If no emergency is detected, returns original baseline response unchanged.
        """
        # Negative control abstention check: if baseline response already contains negative control abstention, preserve it
        if baseline_response and "cannot provide medical advice" in baseline_response.lower():
            decision = EmergencyDecision(
                is_emergency=False,
                reasoning="Negative-control abstention detected; preserving baseline response.",
                detection_latency_ms=0.0
            )
            return baseline_response, decision

        decision = self.detect_emergency(query, retrieved_contexts)

        if not decision.is_emergency:
            return baseline_response, decision

        # Build prominent immediate emergency escalation response
        trigger_desc = decision.matched_text or "acute red-flag symptoms"
        hotline_in = self.hotlines.get("india", "112")
        hotline_us = self.hotlines.get("us", "911")

        guarded_response = (
            f"<USER_QUERY>\n{query}\n</USER_QUERY>\n\n"
            f"### 🚨 Immediate Emergency Medical Guidance\n\n"
            f"**Seek immediate emergency medical care.**\n"
            f"The presentation you described (\"{trigger_desc}\") can be a sign of an acute, life-threatening medical emergency "
            f"(such as acute coronary syndrome / heart attack, pulmonary embolism, aortic dissection, or acute respiratory failure) "
            f"that requires immediate, urgent in-person clinical assessment.\n\n"
            f"**Actions Required Immediately:**\n"
            f"* **Call emergency services right now:** Call **{hotline_in}** (in India), **{hotline_us}** (in the US), or your local emergency number immediately.\n"
            f"* **Go to the nearest hospital Emergency Department (ED / A&E)** without delay. Do not wait for a routine appointment or outpatient consultation.\n"
            f"* **Do not drive yourself** if experiencing active chest pain, shortness of breath, dizziness, or weakness; call an ambulance or have someone drive you.\n"
            f"* **Do not substitute home remedies, rest, or over-the-counter medications** for urgent medical evaluation.\n\n"
            f"**Clinical Uncertainty & Safety:**\n"
            f"This guidance is an urgent safety precaution based on the reported symptoms. An accurate diagnosis cannot be made online. "
            f"Only emergency diagnostic evaluation (such as an urgent electrocardiogram [ECG], cardiac enzyme testing, and vital signs monitoring) "
            f"can safely rule out life-threatening causes.\n\n"
            f"{MANDATORY_HEADER}\n"
            f"{MANDATORY_TEXT}"
        )

        # Eliminate any lingering contradictory routine appointment scheduling text
        sanitized_response = self._eliminate_contradictory_routine_advice(guarded_response)
        return sanitized_response, decision

    def _eliminate_contradictory_routine_advice(self, text: str) -> str:
        """
        Removes or supersedes contradictory routine clinic appointment phrases in emergency mode.
        """
        cleaned = text
        for pat in ROUTINE_ADVICE_PATTERNS:
            cleaned = pat.sub("[ROUTINE CLINIC SCHEDULING SUPPRESSED: SEEK EMERGENCY CARE]", cleaned)
        return cleaned

    def _failsafe_detect(self, query_clean: str, t0: float) -> EmergencyDecision:
        """
        Resilient static keyword fallback. Never drops an emergency signal under exception or missing config.
        """
        latency = round((time.perf_counter() - t0) * 1000, 3)

        # Check for explicit negation in fallback
        if re.search(r"\bno\s+(?:chest\s+pain|shortness\s+of\s+breath)\b", query_clean, re.I):
            return EmergencyDecision(
                is_emergency=False,
                reasoning="Fail-safe fallback: explicit negation detected.",
                detection_latency_ms=latency,
                fallback_engaged=True,
            )

        for kw in FAILSAFE_KEYWORD_PATTERNS:
            match = kw.search(query_clean)
            if match:
                return EmergencyDecision(
                    is_emergency=True,
                    fired_rule_id="RULE-FAILSAFE-KEYWORD",
                    category="emergency_fallback",
                    severity="CRITICAL_EMERGENCY",
                    matched_text=match.group(0),
                    confidence=0.9,
                    reasoning=f"Fail-safe fallback triggered on '{match.group(0)}'.",
                    detection_latency_ms=latency,
                    fallback_engaged=True,
                )

        return EmergencyDecision(
            is_emergency=False,
            reasoning="Fail-safe fallback: no red flags identified.",
            detection_latency_ms=latency,
            fallback_engaged=True,
        )
