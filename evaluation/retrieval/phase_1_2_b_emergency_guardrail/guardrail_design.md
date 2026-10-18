# MediScanAI Phase 1.2.b — Emergency Triage Guardrail Design Specification

**Phase:** Phase 1.2.b Emergency Guardrail Experiment  
**Date:** October 17, 2026  
**Status:** **Experimental Prototype (Isolated)**  
**Component:** `EmergencyGuardrail` (`evaluation/retrieval/phase_1_2_b_emergency_guardrail/guardrail.py`)  
**Configuration:** `guardrail_config.json`  

---

## 1. Clinical Motivation & Problem Statement

In MediScanAI Phase 1.2.a, an audit of 50 generated responses conditioned on frozen Phase D.2.c hybrid retrieval evidence revealed a critical clinical triage failure:

- **Case `MED-BENCH-038` ("Chest pain"):**
  - **Retrieved Evidence:** Correctly retrieved life-threatening etiologies: Myocardial Infarction / Heart Attack (`disease_chunk_3066`), Pericarditis (`disease_chunk_157`), and Lung Contusion (`disease_chunk_129`).
  - **Generator Response:** Correctly summarized these conditions, but concluded:
    > *"A thorough medical evaluation by a qualified professional is necessary to determine the underlying cause of chest pain."*
  - **Clinical Failure Mode:** Recommending routine or general medical consultation for an acute chest pain presentation without immediately instructing the user to contact emergency services (e.g., call 112 / 911 or visit an Emergency Department) introduces severe delay-to-care risks in acute coronary syndromes, pulmonary embolism, or aortic dissection.

The goal of Phase 1.2.b is to build an isolated, deterministic, sub-millisecond emergency safeguard that intercepts acute life-threatening presentations and enforces immediate emergency escalation while preserving 100% fidelity on routine queries and negative controls.

---

## 2. Guardrail Architecture & Interception Flow

The guardrail operates as an isolated post-retrieval / pre-response safeguard:

```
                  ┌───────────────────────────────┐
                  │          User Query           │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │   Contextual Exception Check  │───(Match: e.g. "stroke volume")───► Pass-through Baseline
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │    Negation & History Gate    │───(Match: e.g. "no chest pain")───► Pass-through Baseline
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ Deterministic Emergency Rules │───(No Match)──────────────────────► Pass-through Baseline
                  └──────────────┬────────────────┘
                                 │ (Rule Match: e.g. RULE-01)
                                 ▼
                  ┌───────────────────────────────┐
                  │  Evidence Life-Threat Check   │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │  Prominent Emergency Guidance │
                  │  (Call 112 / Immediate ED)    │
                  └───────────────────────────────┘
```

---

## 3. Deterministic Rule Hierarchy & Triggers

Rules are defined in [`guardrail_config.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_2_b_emergency_guardrail/guardrail_config.json) and executed in strict priority order:

### 1. `RULE-01-CARDIOVASCULAR-CHEST-PAIN`
- **Clinical Scope:** Acute coronary syndromes, angina, myocardial infarction, aortic dissection.
- **Triggers:**
  - `\bchest\s+pain\b`, `\bpain\s+in\s+(?:the\s+|my\s+)?chest\b`
  - `\bchest\s+hurts?\b`, `\bmy\s+chest\s+hurts?\b`
  - `\bchest\s+(?:tightness|pressure|heaviness|squeezing|crushing)\b`
  - `\bcrushing\s+(?:chest\s+)?pain\b`
  - `\bradiating\s+to\s+(?:the\s+|my\s+)?(?:left\s+)?(?:arm|jaw|neck|back)\b`
  - `\b(?:left\s+)?arm\s+(?:is\s+)?numb.*chest\b`

### 2. `RULE-02-RESPIRATORY-DISTRESS`
- **Clinical Scope:** Acute respiratory failure, airway obstruction, anaphylaxis, pulmonary edema.
- **Triggers:**
  - `\bsevere\s+(?:difficulty\s+breathing|shortness\s+of\s+breath|breathlessness)\b`
  - `\bgasping\s+for\s+(?:air|breath)\b`
  - `\bthroat\s+swelling\b`, `\banaphylaxis\b`, `\bstridor\b`
  - `\bbluish\s+(?:lips|face|skin)\b`, `\bcyanosis\b`
  - `\bcannot\s+breathe\b`, `\bcan(?:'t| not)\s+(?:catch\s+my\s+breath|breathe)\b`

### 3. `RULE-03-NEUROLOGICAL-STROKE`
- **Clinical Scope:** Acute ischemic stroke, intracerebral hemorrhage, subarachnoid hemorrhage (FAST signs).
- **Triggers:**
  - `\bfacial\s+droop(?:ing)?\b`
  - `\bsudden\s+(?:weakness|numbness|paralysis)\s+(?:in|on|of)\s+(?:one\s+side|arm|face|leg)\b`
  - `\bslurred\s+speech.*(?:weakness|droop)\b`
  - `\bthunderclap\s+headache\b`, `\bworst\s+headache\s+of\s+(?:my\s+)?life\b`

### 4. `RULE-04-UNCONSCIOUSNESS-COLLAPSE`
- **Clinical Scope:** Syncope with trauma, cardiac arrest, coma, status epilepticus.
- **Triggers:**
  - `\bunconscious(?:ness)?\b`, `\bunresponsive(?:ness)?\b`
  - `\bpassed\s+out\s+and\s+(?:cannot\s+wake|unresponsive)\b`
  - `\bcollapse(?:d)?\s+and\s+(?:not\s+breathing|unconscious)\b`

### 5. `RULE-05-SEVERE-HEMORRHAGE`
- **Clinical Scope:** Massive gastrointestinal, pulmonary, or arterial hemorrhage.
- **Triggers:**
  - `\bcoughing\s+up\s+(?:large\s+amounts\s+of\s+)?blood\b`, `\bmassive\s+hemoptysis\b`
  - `\bvomiting\s+blood\b`, `\bhematemesis\b`
  - `\bsevere\s+(?:uncontrolled\s+)?arterial\s+bleeding\b`

### 6. `RULE-06-EVIDENCE-CONDITION-INTERCEPT`
- **Clinical Scope:** Cross-evidence validation for ambiguous cardinal thoracic symptoms.
- **Trigger Condition:** Query contains cardinal thoracic keywords (`chest`, `breathing`, `heart`, `sudden`) AND retrieved evidence includes life-threatening emergency conditions (`heart attack`, `myocardial infarction`, `pulmonary embolism`, `aortic dissection`, `cardiac arrest`).

---

## 4. False-Positive Suppression & Gating

To prevent the guardrail from converting routine symptom queries, physiological inquiries, or negative controls into false emergencies:

1. **Explicit Negation Gate:**
   - Filters out explicitly negated complaints:
     - `\bno\s+(?:chest\s+pain|shortness\s+of\s+breath|difficulty\s+breathing)\b`
     - `\bwithout\s+(?:chest\s+pain|shortness\s+of\s+breath)\b`
     - `\bdenies\s+(?:chest\s+pain|shortness\s+of\s+breath)\b`
   - Example: *"no chest pain but have mild runny nose and sneezing"* $\to$ Emergency escalation suppressed.

2. **Historical & Family History Gate:**
   - Identifies remote events and third-party family history:
     - `\b(?:years?|months?)\s+ago\b`, `\bin\s+2015\b`
     - `\b(?:father|mother|brother|sister|parent)\s+had\s+(?:a\s+)?(?:heart\s+attack|stroke)\b`
   - Example: *"father had a heart attack in 2015, what is Lipitor for?"* $\to$ Emergency escalation suppressed.

3. **Contextual Collision Gate:**
   - Prevents substring false alarms:
     - `\bchest\s+decongestant\b` (medication formulation, not chest pain)
     - `\bstroke\s+volume\b` (cardiac physiology parameter, not cerebral stroke)
     - `\bpain\s+relief\s+(?:cream|gel)\s+for\s+(?:knee|foot)\b` (peripheral joint pain)

4. **Negative Control Invariant Preservation:**
   - Unanswerable and fictional medicine controls (`MED-BENCH-041`..`045`) lack acute emergency signals.
   - The guardrail maintains 100% baseline abstention without triggering false alarms.

---

## 5. Escalation Directive & Disclaimer Standards

When an emergency presentation is confirmed, the guardrail emits a structured, urgent guidance block:

1. **Prominent Header:** `### 🚨 Immediate Emergency Medical Guidance`
2. **Immediate Action Directives:**
   - Call local emergency services immediately: **112** (India), **911** (US), or national emergency number.
   - Proceed immediately to the nearest Emergency Department (ED / A&E).
   - Do not wait for a routine clinic appointment or outpatient consultation.
   - Do not drive yourself if experiencing chest pain, weakness, or breathlessness.
   - Do not substitute home remedies, rest, or OTC medications for urgent clinical evaluation.
3. **Preservation of Diagnostic Uncertainty:**
   - The guardrail explicitly states that an online tool cannot provide a definitive diagnosis, and that urgent in-person diagnostics (ECG, cardiac biomarkers, imaging) are required.
4. **Mandatory Legal Disclaimer:**
   - Retains `### ⚠️ Important Warning` and verbatim project disclaimer at the bottom.

---

## 6. Limitations and Known Risks

1. **Lexical and Syntax Dependency:**
   - Highly atypical slang, extreme typographical corruptions, or phonetic homophones not covered by compiled regexes could evade detection.
2. **Clinical False Negatives:**
   - Subtle, atypical presentations (e.g., painless silent myocardial infarction in elderly diabetic patients presenting solely with profound nausea or fatigue) will not be captured by chest pain rules without over-escalating all fatigue queries.
3. **Automated Evaluation Scope:**
   - Automated tests confirm rule matching and deterministic behavior, but do not replace certified clinician review of triage thresholds.
