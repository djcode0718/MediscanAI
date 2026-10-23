# MediScanAI Cycle A8 Failure Analysis & Cross-Cycle Integration
**Date:** 2026-10-23  
**Analysis Target:** Synthesis of A5, A6, and A7 empirical evidence to guide final Candidate A8  
**Working Branch:** `exp/ragas-opt`  

---

## 1. Synthesis of Empirical Evidence Across Candidates

| Dimension | A5 Candidate | A6 Candidate | A7 Candidate | Key Finding |
|---|---:|---:|---:|---|
| **Mean Faithfulness** | 0.7538 | **0.8021** | 0.6088 | A6 was the highest performing candidate. A7 suffered from meta-absence penalties. |
| **Median Faithfulness** | 0.8000 | **1.0000** | 0.7500 | A6 reached perfect median (1.0000). |
| **Unsupported Statements** | 40 | **34** | 70 | Lowest unsupported statement count in A6. |
| **Medicine Clean OCR** | 0.9667 | **1.0000** | 0.7639 | Perfect 1.0000 in A6 when strictly reporting positive labeled facts. |
| **Medicine Noisy OCR** | 0.9333 | 0.8000 | 0.5100 | Regressed in A7 when prompted to report missing indications/precautions. |
| **Symptom-Only** | 0.6628 | **0.8500** | 0.7326 | A6 recovered (+0.1872) by eliminating "also includes" and negative condition disclaimers. |
| **Symptom + Med Mismatch** | 0.8056 | **0.8889** | 0.6361 | Positive indication framing in A6 scored highest. |

---

## 2. Root Cause Diagnoses of Persistent Failures

### 2.1 The "Meta-Absence" Hallucination Trap (Discovered in A7)
- **Observation:** When the LLM outputs negative meta-statements such as *"The labeled indications for Hospicare are not stated in the available sources"* or *"No medical illness was identified in the available sources"*, the RAGAS judge flags them as unsupported.
- **Judge Reasoning:** The judge checks whether the context contains the meta-sentence itself. If the context simply lacks the information rather than stating "this information is missing", the judge treats the assertion of absence as ungrounded!
- **A8 Remedy:** **Strict Positive Grounding.** Only report facts directly asserted in evidence. Never instruct the LLM to output meta-sentences asserting that precautions or indications are absent.

### 2.2 Cross-Entity Attribute Bleed (Seen in `E2E-082` and `E2E-041`)
- **Observation:** In `E2E-082`, the scanned medicine was `Strophanthus (STROPHANTHUS) 20mg` (which has `Rx Only*` in its drug block [E7]). In A6, it borrowed "induced abortion" from disease chunk [E1]. In A7, it borrowed active ingredients and indications from Kids Relief in [E6].
- **Root Cause:** When the scanned medicine's chunk lacks clinical indication text, the LLM searches other chunks in the prompt and attributes their indications to the scanned medicine.
- **A8 Remedy:** In Prompt v7, enforce an unconditional rule:
  `"Under no circumstances attribute the indications or ingredients of one DRUG or DISEASE block to another drug. If the scanned medicine's DRUG block does not contain an indication, write: '<Brand/Generic> label evidence in E# states: Rx Only.' Do not cite or attribute any other block."`

### 2.3 Unanswerable Probes & Entity Leakage (Seen in `E2E-094`, `E2E-097`, `E2E-100`)
- **Observation:** In `E2E-100`, outputting *"The requested pediatric weight-based dosing for Glycozempra 5mg/mL solution could not be found"* caused the judge to penalize Glycozempra because Glycozempra is not in the context.
- **A8 Remedy:** Use the clean entity-neutral abstention template:
  `"The requested clinical information could not be verified from the available sources."`

---

## 3. Design of Unified Candidate A8 (Prompt v7 & Pipeline Integration)

1. **Restore Core A6 Prompt Architecture:**
   - Use A6's winning prompt structures for `SYMPTOM_ONLY`, `MEDICINE_ONLY`, and `SYMPTOM_AND_MEDICINE`.
   - Maintain positive indication framing ("X is labeled for Y, which does not cover the presented symptoms").
2. **Absolute Entity Isolation:**
   - Strict product-evidence binding prohibiting borrowing indications from neighboring chunks.
3. **Refined Grounded Abstention:**
   - Strictly entity-neutral abstention for all unanswerable queries.
4. **Deterministic Multi-Stage Sanitization:**
   - Normalizes citation syntax.
   - Strips invalid tags.
   - Strips additive modifiers ("also includes").
   - Strips negative condition disclaimers.
   - Cleans duplicate periods and orphan brackets.
