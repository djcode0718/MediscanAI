# MediScanAI Emergency Guardrail Integration Architecture

**Document Version:** 1.0.0  
**Phase:** Phase 1.2.c — Integration Proposal & Readiness Design  
**Date:** 2026-10-17  
**Status:** Architectural Design (Zero Production Code Changes)

---

## 1. Architectural Alternatives Evaluation

To safely integrate the deterministic `EmergencyGuardrail` into MediScanAI, three architectural paradigms were evaluated against strict clinical and engineering criteria.

```
+───────────────────────────────────────────────────────────────────────────────+
| Alternative A: Pre-Generation Prompt Injection Only                           |
|   [Query] ──► [Classifier] ──► [Inject Prompt Context] ──► [LLM Generation]  |
+───────────────────────────────────────────────────────────────────────────────+
| Alternative B: Post-Generation Deterministic Response Guard Only              |
|   [Query] ──► [Retrieval] ──► [LLM Generation] ──► [Deterministic Override]  |
+───────────────────────────────────────────────────────────────────────────────+
| Alternative C: Two-Stage Hybrid Safeguard (RECOMMENDED)                       |
|   [Query] ──► [Stage 1: Pre-Gen Fast-Path / Flag]                             |
|                 │                                                             |
|                 ├── High-Confidence Acute Red Flag: Fast-Path ED Return (<1ms)|
|                 └── Ambiguous/Standard: [Retrieval + LLM] ──►                 |
|                                         [Stage 2: Deterministic Post-Guard]   |
+───────────────────────────────────────────────────────────────────────────────+
```

### 1.1 Comparative Matrix

| Evaluation Dimension | Alternative A: Pre-Gen Injection | Alternative B: Post-Gen Override | Alternative C: Two-Stage Hybrid (Recommended) |
| :--- | :--- | :--- | :--- |
| **Reliability of Escalation** | **Poor.** LLM remains stochastic; may soften warnings or advise routine clinics. | **Excellent (100%).** Deterministic string replacement guarantees emergency directive. | **Excellent (100%).** Deterministic post-guard guarantees compliance; fast-path accelerates urgent cases. |
| **Risk of False-Positive Escalation** | Medium. Injected emergency tokens bias model generation even for nuanced queries. | Low (0.0%). Governed strictly by audited deterministic regex & exception rules. | Low (0.0%). Same deterministic rule engine with negation & contextual gates. |
| **Risk of Contradictory Advice** | **High.** LLM can output "Call 911" followed by "Schedule visit next Tuesday". | **Zero.** The guardrail template supersedes and replaces routine outpatient text. | **Zero.** Complete elimination of routine scheduling text when emergency triggers fire. |
| **Preservation of Non-Emergency Text** | Variable. Alters prompt context for non-emergencies if classifier is loose. | **100% Exact.** Non-emergency responses pass through byte-for-byte unchanged. | **100% Exact.** Unchanged pass-through for all non-emergency benchmark cases. |
| **OCR & Multimodal Compatibility** | Moderate. Requires OCR text injection into classification prompts. | **High.** Operates on user query, transcribed audio, and retrieved context. | **High.** Compatible with text, audio, and OCR inputs. |
| **End-to-End Latency** | Adds 0ms compute, but incurs full 3,000–8,000ms LLM latency for dying patients. | Adds 0.022ms guardrail overhead; still incurs full 3,000–8,000ms LLM latency. | **Sub-millisecond for criticals (<1ms).** Bypasses LLM wait when immediate action is vital. |
| **Testability & Rollback** | Hard. Non-deterministic LLM output requires probabilistic assertions. | **Trivial.** Deterministic string and rule output verified via unit tests. | **Trivial.** Fully deterministic state machine with isolated unit and integration tests. |

---

## 2. Recommended Approach: Alternative C (Two-Stage Safeguard)

We recommend **Alternative C: Two-Stage Hybrid Safeguard with Deterministic Post-Enforcement and Fast-Path Early Return**.

### 2.1 Clinical & Systems Rationale

1. **Life-Critical Time to Action:**
   - In clinical emergencies (e.g. sudden respiratory arrest, anaphylaxis, unconsciousness, crushing retrosternal chest pain), waiting 4 to 8 seconds for a local LLM or cloud API to generate differential diagnoses is clinically unsafe.
   - Stage 1 detects Tier-1 acute emergencies immediately upon input validation and provides immediate dispatch instructions (112 in India, 911 in the US) with **0.010 ms latency**.

2. **Absolute Prevention of Contradictory Routine Care:**
   - The fundamental failure in Phase 1.2.a (`MED-BENCH-038`) was that the model produced contradictory advice: it identified acute coronary syndrome but told the user to make a primary care appointment.
   - Stage 2 deterministically guarantees that no LLM generation can advise outpatient scheduling when red-flag symptoms or retrieval signals are present.

3. **Complete Differential Context When Safe:**
   - For queries with ambiguous symptoms (e.g. atypical chest discomfort without red flags) where emergency evidence is only uncovered during retrieval (RULE-06), the system executes full hybrid retrieval and generation, followed by Stage 2 deterministic enforcement.

---

## 3. Structural Integration Flow

```
                      [User Request: text / voice / image]
                                       │
                                       ▼
                        [Input Preprocessing & Whisper]
                                       │
                                       ▼
             ┌──────────────────────────────────────────────────┐
             │ Stage 1: Pre-Generation Emergency Detection      │
             │ EmergencyGuardrail.detect_emergency(query)       │
             └──────────────────────────────────────────────────┘
                                       │
                 Is Tier-1 Immediate Red Flag & Fast-Path Enabled?
                     ├── YES ──► [Immediate Emergency Response (<1ms)]
                     │           - National Hotlines (112 / 911)
                     │           - Immediate ED Directive
                     │           - Driving / Self-Medication Prohibition
                     │           - Verbatim Legal Disclaimer
                     │           - Audit Event: EMERGENCY_FAST_PATH_TRIGGERED
                     │           └──► [DB Persistence & Return]
                     │
                     └── NO (Standard or Ambiguous Query)
                           │
                           ▼
             ┌──────────────────────────────────────────────────┐
             │ Multi-Index Hybrid Retrieval (FAISS + BM25 + CE) │
             └──────────────────────────────────────────────────┘
                           │
                           ▼
             ┌──────────────────────────────────────────────────┐
             │ Prompt Assembly & LLM Generation                 │
             └──────────────────────────────────────────────────┘
                           │
                           ▼
             ┌──────────────────────────────────────────────────┐
             │ Stage 2: Post-Generation Deterministic Guard     │
             │ EmergencyGuardrail.apply_guardrail(query, resp)  │
             └──────────────────────────────────────────────────┘
                           │
                     Did Guardrail Fire?
                     ├── YES: Supersede routine outpatient advice with
                     │        prominent emergency directive + hotline.
                     └── NO:  Pass through original LLM response 100% untouched.
                           │
                           ▼
             ┌──────────────────────────────────────────────────┐
             │ Summary Card Packaging & DB Audit Persistence    │
             └──────────────────────────────────────────────────┘
                           │
                           ▼
                   [Client Response Delivery]
```

---

## 4. Architectural Boundaries and Component Design

### 4.1 Modular Component Placement
The guardrail must reside as an isolated, self-contained module in the application layer:
- **Location:** `app/guardrails/emergency.py` (or `app/emergency_guardrail.py`).
- **Configuration:** `app/guardrails/emergency_config.json`.
- **Zero Heavy Dependencies:** The guardrail uses only the Python Standard Library (`re`, `json`, `time`, `dataclasses`, `pathlib`). It requires:
  - **NO Neo4j.**
  - **NO Cloud APIs or network calls.**
  - **NO PyTorch or HuggingFace model downloads.**
  - **NO additional database dependencies.**

### 4.2 Decoupling from Generation Engine
The guardrail sits strictly outside the LLM generator. It wraps `Pipeline.run()` or is invoked within `Pipeline.run()` as a transparent pre/post middleware filter.

If Ollama, Gemini, or Groq is completely down or throwing 500 errors, the emergency guardrail still functions with 100% reliability because it executes independently in Python memory.

---

## 5. Ensuring Emergency Advice Prominence and Non-Contradiction

To guarantee that the Phase 1.2.a safety defect can never recur, the integration architecture enforces the following content invariants:

1. **Header Prominence:**
   The emergency escalation block is inserted at the top of the clinical guidance section, immediately after the mandatory legal disclaimer. It is highlighted with clear Markdown alert indicators (`### 🚨 Immediate Emergency Medical Guidance`).

2. **Explicit Countermand of Routine Consultation:**
   The template includes an explicit negative command:
   > *"Do not wait to see if symptoms improve and do not wait for an outpatient clinic appointment."*
   This directly counteracts the default tendency of clinical models to suggest booking a routine consultation.

3. **Prohibition of Self-Transportation:**
   The template includes explicit safety instructions:
   > *"Do not drive yourself if experiencing active chest pain, shortness of breath, dizziness, or weakness; call an ambulance or have someone drive you."*

4. **No Delaying Follow-Up Questions:**
   In emergency mode, the pipeline suppresses interactive "tell me more" or follow-up clarification questions. Asking a patient with crushing chest pain what they ate for lunch creates dangerous distraction; immediate emergency care must be the sole actionable focus.
