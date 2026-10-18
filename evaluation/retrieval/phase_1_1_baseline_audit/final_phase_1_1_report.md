# MediScanAI Phase 1.1 — Master Baseline & Evaluation Audit Report

**Evaluation Phase:** MediScanAI Phase 1.1  
**Date:** October 17, 2026  
**Auditor:** Autonomous Systems Baseline & Evaluation Specialist  
**Authoritative Final Verdict:**

$$\mathbf{BASELINE\_ESTABLISHED\_WITH\_WARNINGS}$$

---

## 1. Executive Summary & Authorizing Decision

Phase 1.1 was conducted as an exhaustive, read-only audit to establish a trustworthy, evidence-backed baseline for the MediScanAI architecture prior to initiating optimization work.

### Summary of Core Audit Findings:
1. **Provenance & Production Disconnect:**  
   The selected Phase D.2.c retrieval architecture (`CFG-04-D2C-ADAPTIVE-FINAL`, config hash `f3937376cd191ee7`) remains **an isolated experiment** in `evaluation/retrieval/phase_d_2_c/`. The production code in [`app/retriever.py`](file:///Users/sj/Documents/mediscanai/app/retriever.py) is the legacy uncalibrated baseline and contains zero Phase D routing or thresholding logic.
2. **Phase C.5 vs. C.5.1 Reconciliation:**  
   The historical metric conflict was fully resolved. The original Phase C.5 numbers (Faithfulness: **0.5835**, Answer Relevancy: **0.7532**, Context Precision: **0.8932**, Context Recall: **0.6186**) are the **true, mathematically recomputed values**. The conflicting numbers in the text of `audit_report.md` Section 3.1 (`0.817651`, etc.) are an **unreproduced clerical transcription error** within that markdown document, contradicted by the audit's own machine-readable JSON data.
3. **Retrieval Baseline Established:**  
   The retrieval baseline for `CFG-04-D2C-ADAPTIVE-FINAL` is established and reproducible:
   - **Strict Record Recall@5:** Dev: **0.4444** | Val: **0.4444** | Held-Out: **0.5556**
   - **Canonical-Entity Recall@5:** Dev: **0.6296** | Val: **0.6667** | Held-Out: **0.7778**
   - **Negative Control Rejection Accuracy:** **1.0000 (100.0%)** across all splits.
   - **Safety Suite Pass Rate:** **100.0%** (12/12 common subset; 14/14 extended suite).
4. **Generation Baseline Explicitly Not Established:**  
   Zero generation runs have been conducted using evidence from the Phase D.2.c retrieval pipeline. Existing generation artifacts (Phase C.4) were conditioned on legacy un-routed retrieval. Presenting historical Phase C.5 values as the D.2.c baseline is scientifically impermissible. The generation baseline is formally recorded as **`BASELINE_NOT_ESTABLISHED`**.
5. **Latency Baseline Documented:**  
   Retrieval latency median is **1,407 ms** (p95: 1,791 ms), dominated by cross-encoder reranking. End-to-end latency median is **~19.1 seconds**, dominated by local autoregressive decoding on Ollama `llama3.1:8b` (~8.9 tokens/sec).

Because the retrieval baseline is verified, historical discrepancies are reconciled, and generation limitations are explicitly bounded, the phase gate decision is **`BASELINE_ESTABLISHED_WITH_WARNINGS`**.

---

## 2. What Is Actually Working (Verified Strengths)

1. **Negative Control & Fictional Drug Rejection:**
   - The Upstream Lexical Verification Gate achieves **100% clean abstention (rejection accuracy 1.0)** across all negative controls and fictional entities (`Zephastin`, `Virokine`, `Pulmoflux`, `Zorvaxil`, `Cardioprex`).
   - Zero distractor adoption observed in generation.
2. **Emergency Triage Escalation:**
   - 100% of red-flag emergency presentations (acute chest pain, anaphylaxis, stroke symptoms) trigger immediate escalation directives (`TRIAGE_ESCALATE`).
3. **Canonical Active Substance Recovery:**
   - Canonical-Entity Recall@5 reaches **0.6296 (dev)**, **0.6667 (val)**, and **0.7778 (held-out)**, demonstrating that when a specific commercial package chunk is missed, the correct therapeutic active substance is still surfaced $>63-78\%$ of the time.
4. **OCR Degradation Recovery:**
   - OCR regression pass rate is **100.0%**; packaging noise and crop artifacts are handled via normalized lexical lookups.
5. **Format & Disclaimer Compliance:**
   - **100.0% compliance** on mandatory warning headers (`### ⚠️ Important Warning`) and verbatim statutory legal disclaimers.

---

## 3. What Is Demonstrably Failing and Why (Verified Defects)

1. **Production Code Architecture Lag:**
   - Production [`app/retriever.py`](file:///Users/sj/Documents/mediscanai/app/retriever.py) has not incorporated Phase D advances. In production, unanswerable queries still return false positive documents because no score threshold is applied.
2. **Lay-Phrased Multi-Symptom Threshold Pruning (`MED-BENCH-035`):**
   - The fixed cross-encoder threshold $\tau = -0.5$ eliminated false positives on negative controls (`MED-BENCH-045`), but pruned valid disease evidence for query `MED-BENCH-035` (`"missed periods, trouble getting pregnant, and weight gain"`), where cross-encoder scores fell between $-0.55$ and $-2.82$.
3. **Relationship Query Misrouting:**
   - Queries seeking brand-generic or ingredient pairings (`MED-BENCH-017`, `018`, `019`, `046`, `048`) are misclassified as `general_medical_query` (`BALANCED_MULTI_RETRIEVAL`), where broad text search fails to surface the specific entity relationship in the top-5.
4. **Carried-Forward Intent-Router Defects:**
   - **`DEFECT-ORAL-ROUTE-COLLISION`:** The word `"oral"` in symptom phrases causes generic liquid formulations (*Metformin oral solution*, *Amoxicillin oral suspension*) to route to disease diagnosis, suppressing the drug catalog.
   - **`DEFECT-SPACE-SEPARATED-STRENGTH`:** Space-separated dosages (`"500 mg"`) fail contiguous regex, leaving `"500"` unstripped and falling back to broad multi-retrieval.
   - **`DEFECT-SUBSTRING-COLLISION`:** Substring match in lexical gate allows `"met"` to pass gate rather than cleanly abstaining.
5. **Emergency Guidance Dilution Under Context Expansion (`MED-BENCH-038`):**
   - In Phase C.4 generation, appending supplemental context caused `llama3.1:8b` to suggest consulting a *pharmacist* for acute chest pain instead of strictly calling 911/ER.

---

## 4. What Remains Unknown

1. **Current Generation Quality on D.2.c Contexts:**  
   The exact Faithfulness, Context Precision, and Context Recall of answers generated from `CFG-04-D2C-ADAPTIVE-FINAL` evidence remain unknown until a fresh generation run is executed.
2. **Downstream Effect of Threshold Pruning:**  
   How the local generator behaves when the retriever returns 0 items due to threshold pruning (e.g. `MED-BENCH-035`) vs. when it returns low-scoring candidates.
3. **Cross-Encoder Concurrency Scaling:**  
   Retrieval latency under concurrent multi-user load has not been tested; cross-encoder model evaluation is currently executed sequentially on CPU/MPS.
4. **Cloud LLM Judge Calibration:**  
   Agreement rates between cloud judges (e.g., Claude 3.5 Sonnet, GPT-4o) and clinical references on MediScanAI answer formats remain unmeasured.

---

## 5. Expected Impact Analysis

| Architecture Area | Identified Issue | Expected Impact on Faithfulness | Expected Impact on Context Recall | Expected Impact on Context Precision | Expected Impact on Latency |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Relationship Routing** | Misrouting brand/generic queries | High (model confabulates pairs) | **Critical** (target pair missing) | Medium (diluted by broad text) | Low |
| **Score Thresholding** | Fixed $\tau = -0.5$ on lay symptoms | High (forces clean abstention) | **Critical** (prunes lay gold chunks) | Positive (eliminates noise) | Low |
| **Candidate Pool Size** | Pool size 30 in cross-encoder | Minimal | Positive (broad safety net) | Neutral | **Critical** (drives 95% of latency) |
| **Route Token Collision** | Word "oral" misrouting to disease | High (absent drug info) | **Critical** (0 drug chunks returned)| High (wrong channel) | Low |
| **Context Assembly** | Appending excessive triples | **Critical** (causes multi-hop drift)| Neutral | Negative (dilutes precision) | Medium (+11.5% gen latency) |

---

## 6. Ranked Evidence-Based Proposal for Phase 1.2

Based on verified empirical evidence, the engineering roadmap for Phase 1.2 is prioritized as follows:

1. **Priority 1: Execute Dedicated Generation Baseline on Phase D.2.c (`CFG-04`)**
   - Condition generation on verified Phase D.2.c retrieval evidence across the 50 canonical benchmark cases using Ollama `llama3.1:8b`.
   - Score using the formalized Phase 1.1 metric contract to establish the official Generation Baseline.
2. **Priority 2: Remediate the Three Bounded Intent-Router Defects**
   - *Fix 1:* Filter administration route terms (`"oral"`, `"topical"`, `"otic"`) out of `self.symptom_phrases`.
   - *Fix 2:* Support space-separated dosage token normalization (`r"^\d+\s*(?:mg|mcg|g|ml)$"`).
   - *Fix 3:* Require exact word-boundary token matching in the upstream lexical gate.
3. **Priority 3: Implement Adaptive Margin-Based Thresholding for Lay Phrasing**
   - Replace the uniform text threshold $\tau = -0.5$ with an adaptive or query-type-specific threshold that preserves negative control rejection ($1.0$) while recovering lay-symptom queries like `MED-BENCH-035`.
4. **Priority 4: Optimize Cross-Encoder Candidate Pool for Latency Reduction**
   - Reduce the cross-encoder candidate pool from 30 to 15 for single-entity queries, cutting retrieval latency from ~1,400 ms to $< 800\text{ ms}$ without sacrificing Hit Rate@5.
5. **Priority 5: Production Code Integration (`app/retriever.py`)**
   - Once Phase 1.2 validates the generation baseline and routing fixes, promote the experimental D.2.c architecture into production [`app/retriever.py`](file:///Users/sj/Documents/mediscanai/app/retriever.py).
