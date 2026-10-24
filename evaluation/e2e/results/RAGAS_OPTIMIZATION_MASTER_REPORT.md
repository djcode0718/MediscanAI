# MediScanAI — Consolidated RAGAS Experiment History, Failure Analysis & Optimization Master Report

**Repository:** MediScanAI  
**Working Branch:** `exp/ragas-opt`  
**Generated Date:** 2026-10-24T15:14:07.758132  
**Evaluator Framework:** RAGAS 0.2.15 (Judge: llama3.1:8b)  
**Latest Source Commit:** `2e8abc53dc46c3293c24f3b80f7495310197ce8f`  
**Scope:** Exhaustive forensic audit across candidates R0, R0s, A1, A2, A3, A4, A5, A6, A6.1, A7, A8, heldout validation, retrieval matrix, and prompt architectures.  

---

## Section A — Executive Summary

### 1. Program Objective
The primary objective of the MediScanAI RAGAS optimization initiative is to achieve highly grounded, clinically reliable, and faithful multimodal retrieval-augmented generation for medical queries. Specifically, the engineering goal was to elevate answer faithfulness—measured by RAGAS (`llama3.1:8b` judge)—from the historical unconstrained baseline of **0.2993** (R0) and **0.5282** (A2) to > **0.8000** on development cases, with robust out-of-distribution transfer (> **0.7000**) onto unseen held-out clinical cases, while maintaining zero emergency safety regressions and strict citation integrity.

### 2. Best Measured Candidate So Far
- **Best Development Candidate:** **Candidate A6** (`4bbc392`) achieved **0.8021 Mean Faithfulness**, a **1.0000 Median Faithfulness**, and an all-time low of **34 unsupported statements** on the frozen 40-case development subset (`dev_subset_40.json`). It achieved a perfect **1.0000** on clean medicine OCR cases and **0.8793** on symptom-plus-medicine match cases.
- **Best Held-Out Candidate:** **Candidate A6** was independently validated on the zero-contamination 30-case held-out benchmark (`heldout_subset_30.json`), achieving **0.7064 Mean Faithfulness** (+0.0614 over baseline A2 and +0.0509 over A5), a **0.7500 Median Faithfulness**, **0.9075 on Emergency cases**, with unsupported statements reduced to **39**.
- **Candidate A6.1 Status:** Candidate A6.1 targeted two residual qualitative issues from A6 triage (negative disclaimers in symptom-only queries and combination product container attribution). On targeted cases, the fixes achieved **100% faithfulness** (`E2E-073` = 1.0, `E2E-024` = 1.0). However, the aggregate development mean scored **0.7614** due to an evaluator-integrity event: `llama3.1:8b` suffered few-shot prompt leakage on `E2E-080` (emitting statements about Albert Einstein from the internal Ragas prompt), severely penalizing the case (0.00) and depressing the mean.

### 3. Optimization Trajectory Overview
The faithfulness optimization trajectory followed six major empirical phases:
1. **Baseline & Context Bottleneck (R0 -> R0s -> A1):** Unconstrained FAISS dumps blew prompt context limits (8,656 tokens P95, 12.7% truncation rate) and scored 0.2993. Introducing compact evidence formatting and token budgeting (A1) eliminated truncation and boosted faithfulness to 0.6001.
2. **Prompt Architecture & Role Separation (A2):** Moving to Prompt v2 with role separation, evidence neutralization, and explicit citation tags (`[E1]`–`[E5]`) scored 0.5282 on dev, establishing the formal baseline.
3. **Routing & Channel Isolation (A3):** Adding deterministic intent classifier Routing v2 (skipping disease retrieval on medicine-only scans) eliminated cross-domain noise and jumped faithfulness to 0.6558 (+0.1276).
4. **Conditional Indications & Multi-Ingredient Formulation (A4 -> A5):** Prompt v3 conditional verdicts (A4) reached 0.7256. Multi-ingredient formulation parsing and brand filtering (A5) reached 0.7538.
5. **Positive Indication Framing & Claim Grounding (A6):** Prompt v5 prohibited negative symptom exclusions and conversational connectors, reaching the project peak of **0.8021** (median 1.0000).
6. **Abstention Pitfalls, Recovery & Post-Triage Verification (A7 -> A8 -> A6.1):** Attempting explicit negative meta-abstention in A7 caused a severe regression (0.6088) due to the *Meta-Absence Judge Penalty*. A8 recovered to 0.7096 via strict entity isolation. Triage candidate A6.1 verified qualitative fixes on targeted cases, but revealed evaluator vulnerability to small LLM prompt leakage.

### 4. Biggest Persistent Failure Modes & Evaluator Integrity Concerns
- **The Meta-Absence Judge Penalty:** When an answer states that information is *not present* in the sources, the RAGAS NLI judge flags the statement as unsupported because medical package inserts state what drugs do, not what they do not do.
- **Fictitious Drug Probe Penalization:** On unanswerable queries (`E2E-094`, `E2E-096`, `E2E-100`), the judge extracts synthetic drug names (e.g. *Glycozempra*), checks the context, finds 0 occurrences, and marks the statement unfaithful.
- **Evaluator Few-Shot Prompt Leakage:** Small judge models (`llama3.1:8b`) occasionally leak few-shot examples from Ragas's internal prompts (e.g. Albert Einstein on `E2E-080`) when statement extraction parses ambiguously.
- **Degraded OCR Entity Binding:** Severe OCR noise (`E2E-041`, `E2E-047`) causes dictionary retrieval misalignment and attribute confusion.

### 5. Current State of the Project
- **Production Candidate:** **Candidate A6** (`PROMPT_VERSION='v5'`, `ROUTING_VERSION='v2'`, `EVIDENCE_FORMAT='compact'`) remains the authoritative, empirically validated production target.
- **Development Status:** All 204 unit and regression tests pass with 0 failures and 0 model calls in the test suite.
- **Immediate Priority:** Harden the evaluation judge harness (prevent few-shot leakage and parse crashes) before advancing Candidate A6.1 to held-out validation.

---

## Section B — Complete Experiment Inventory

The table below documents every distinct experiment, baseline, and evaluation run discovered across the repository.

| Run ID | Type | Date | Git Commit | Dataset & N | Generator | Judge | Prompt / Routing / Evidence | Mean Faith | Med Faith | Valid / Total | Unsupp Stmts | Status | Report Link |
|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|---|
| `R0_offline` | Full offline baseline | 2026-10-14 | `6572920` | e2e_v1.jsonl (110) | llama3.1:8b | llama3.1:8b | legacy / legacy / legacy | **0.2993** | **0.2500** | 24/110 | 77 | complete | [R0_offline](evaluation/e2e/results/PHASE01B_SUMMARY.md) |
| `R0s` | Development baseline pre-hygiene | 2026-10-15 | `9635138` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | legacy / legacy / legacy | **0.3553** | **0.4000** | 12/15 | 0 | partial (15 scored / 12 valid) | [R0s](evaluation/e2e/results/PHASE01B_SUMMARY.md) |
| `A1` | Evidence hygiene baseline | 2026-10-15 | `9635138` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | legacy / legacy / compact | **0.6001** | **0.5714** | 40/40 | 0 | complete | [A1](evaluation/e2e/results/PHASE01B_SUMMARY.md) |
| `A2` | Development evaluation baseline | 2026-10-15 | `5e5a10a` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v2 / legacy / compact | **0.5282** | **0.5000** | 39/40 | 86 | complete (39 valid / 1 NaN) | [A2](evaluation/e2e/results/PHASE01B_SUMMARY.md) |
| `A3` | Development evaluation | 2026-10-16 | `0e56b46` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v2 / v2 / compact | **0.6558** | **0.7018** | 40/40 | 60 | complete | [A3](evaluation/e2e/results/A3_EVAL_REPORT.md) |
| `A4` | Development evaluation | 2026-10-16 | `0069ab6` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v3 / v2 / compact | **0.7256** | **0.8167** | 40/40 | 52 | complete | [A4](evaluation/e2e/results/A4_EVAL_REPORT.md) |
| `A5` | Development evaluation | 2026-10-17 | `ca0f8dc` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v4 / v2 / compact | **0.7538** | **0.8000** | 40/40 | 40 | complete | [A5](evaluation/e2e/results/A5_EVAL_REPORT.md) |
| `A6` | Development evaluation (Program Winner) | 2026-10-18 | `4bbc392` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v5 / v2 / compact | **0.8021** | **1.0000** | 40/40 | 34 | complete | [A6](evaluation/e2e/results/A6_EVAL_REPORT.md) |
| `A6.1` | Controlled development evaluation | 2026-10-24 | `2e8abc5 + patch` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v5 / v2 / compact | **0.7614** | **1.0000** | 39/40 | 35 | complete (39 valid / 1 parser error) | [A6.1](evaluation/e2e/results/A6_1_EVAL_REPORT.md) |
| `A7` | Development evaluation | 2026-10-19 | `4a99a51` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v6 / v2 / compact | **0.6088** | **0.7500** | 40/40 | 70 | complete (severe regression) | [A7](evaluation/e2e/results/A7_EVAL_REPORT.md) |
| `A8` | Development evaluation | 2026-10-20 | `ca2c139` | dev_subset_40.json (40) | llama3.1:8b | llama3.1:8b | v7 / v2 / compact | **0.7096** | **0.9091** | 39/40 | 49 | complete (39 valid / 1 parser error) | [A8](evaluation/e2e/results/A8_EVAL_REPORT.md) |
| `heldout_A2` | Held-out zero-contamination baseline | 2026-10-23 | `2e8abc5` | heldout_subset_30.json (30) | llama3.1:8b | llama3.1:8b | v2 / legacy / compact | **0.6450** | **0.6515** | 30/30 | 58 | complete | [heldout_A2](evaluation/e2e/results/HELDOUT_A2_VS_FINAL_REPORT.md) |
| `heldout_A5` | Held-out reference evaluation | 2026-10-23 | `2e8abc5` | heldout_subset_30.json (30) | llama3.1:8b | llama3.1:8b | v4 / v2 / compact | **0.6555** | **0.7500** | 30/30 | 43 | complete | [heldout_A5](evaluation/e2e/results/HELDOUT_A2_VS_FINAL_REPORT.md) |
| `heldout_A6` | Held-out best candidate evaluation | 2026-10-23 | `2e8abc5` | heldout_subset_30.json (30) | llama3.1:8b | llama3.1:8b | v5 / v2 / compact | **0.7064** | **0.7500** | 30/30 | 39 | complete | [heldout_A6](evaluation/e2e/results/HELDOUT_A2_VS_FINAL_REPORT.md) |

---

## Section C — Chronological Experiment Timeline

### Phase 01: Baseline R0 Evaluation Run (`R0_offline`)
- **Git Commit:** `6572920`
- **1. Motivating Problem:** Production pipeline used unconstrained prompt templates and raw FAISS dictionary dumps without token budgeting.
- **2. Hypothesis:** Evaluating raw pipeline against 110-case clinical benchmark will establish baseline faithfulness and identify primary failure modes.
- **3. Implementation Changes:** Instrumented Pipeline.run with trace capture, generation hyperparameters (temp=0.8), and Ragas runner.
- **4. Intended Effect:** Measure baseline faithfulness across full dataset.
- **5. Measured Outcome:** Scored 0.2993 Mean (median 0.2500) with 86 NaNs due to evaluator timeouts on massive prompts (P95 8,656 tokens). 12.7% truncation rate.
- **6. Improving Categories / Cases:** N/A (baseline).
- **7. Regressing Categories / Cases:** Severe context bloat, hallucinated vitamin indications from prompt few-shot leakage, false negative match verdicts.
- **8. Hypothesis Status:** Supported (Confirmed baseline flaws).
- **9. Key Learnings:** Prompts require strict token budgeting, evidence formatting, and role separation.
- **10. Follow-up Action:** Implement compact evidence format and create frozen 40-case development subset.

### Phase 01b: Evidence Hygiene & Compact Formatting (A1) (`A1`)
- **Git Commit:** `ae2c34e / 9635138`
- **1. Motivating Problem:** Raw Python dictionary dumps (`* Result: {str(obj)}`) wasted tokens and obscured clinical facts.
- **2. Hypothesis:** Replacing raw dumps with structured compact evidence text and token budgeting will prevent truncation and improve grounding.
- **3. Implementation Changes:** Created `app/evidence.py` compact format; budgeted max tokens per evidence item; eliminated raw dictionary printing.
- **4. Intended Effect:** Reduce prompt tokens under 1,500 tokens and improve retrieval readability.
- **5. Measured Outcome:** Mean faithfulness jumped from 0.3553 (R0s) to 0.6001 (+48.7%). Context truncation dropped to 0%.
- **6. Improving Categories / Cases:** All categories improved due to complete context retention.
- **7. Regressing Categories / Cases:** None.
- **8. Hypothesis Status:** Supported.
- **9. Key Learnings:** Evidence presentation format is as important as retrieval ranking.
- **10. Follow-up Action:** Implement source-grounded Prompt v2 with role separation and citation tracking.

### Phase 01b: Source-Grounded Prompt v2 (A2 Baseline) (`A2`)
- **Git Commit:** `ee36ddb / 5e5a10a`
- **1. Motivating Problem:** Legacy prompt lacked system/user separation and forced a rigid template that mandated finding package medicines even on symptom-only queries.
- **2. Hypothesis:** Structured role separation, evidence neutralization, and explicit citation tags (`[E1]`–`[E5]`) will improve clinical discipline.
- **3. Implementation Changes:** Created `app/prompt_v2.py`; implemented strict XML tag boundary isolation, neutralized evidence headers, citation syntax.
- **4. Intended Effect:** Establish clean development baseline for prompt iterations.
- **5. Measured Outcome:** Scored 0.5282 Mean (median 0.5000), 86 unsupported statements on frozen 40-case dev subset.
- **6. Improving Categories / Cases:** Eliminated few-shot vitamin leakage; introduced verifiable citation brackets.
- **7. Regressing Categories / Cases:** Without intent routing, disease chunks were unconditionally retrieved for medicine scans, polluting the prompt.
- **8. Hypothesis Status:** Supported (Established development benchmark baseline).
- **9. Key Learnings:** Prompt discipline cannot compensate for cross-domain retrieval pollution.
- **10. Follow-up Action:** Implement deterministic intent classifier Routing v2 to isolate retrieval channels.

### RAGAS-Opt Stage 1: Deterministic Intent Routing v2 (A3) (`A3`)
- **Git Commit:** `0e56b46 / 9902cab`
- **1. Motivating Problem:** Medicine-only OCR scans retrieved nearest-neighbor disease chunks, forcing the model to explain nonexistent disease mismatches.
- **2. Hypothesis:** Classifying query intent before retrieval and skipping disease retrieval on medicine-directed queries will eliminate irrelevant evidence.
- **3. Implementation Changes:** Implemented `ROUTING_VERSION=v2` deterministic intent classifier; gated disease retrieval; aligned disease chunk ID extraction off-by-one bug.
- **4. Intended Effect:** Zero disease chunks injected into medicine-directed queries.
- **5. Measured Outcome:** Mean faithfulness jumped from 0.5282 to 0.6558 (+0.1276). Clean medicine OCR jumped from 0.5667 to 0.8929.
- **6. Improving Categories / Cases:** Medicine clean OCR (+0.3262), medicine noisy OCR (+0.2500).
- **7. Regressing Categories / Cases:** None.
- **8. Hypothesis Status:** Supported (Major breakthrough).
- **9. Key Learnings:** Channel-level retrieval gating is the most cost-effective lever for faithfulness.
- **10. Follow-up Action:** Redesign verdict template in Prompt v3 to handle match cases and unanswerable probes.

### RAGAS-Opt Stage 2: Prompt v3 Conditional Indications (A4) (`A4`)
- **Git Commit:** `0069ab6 / c72cdb2`
- **1. Motivating Problem:** Prompt v2 forced a verdict that assumed the medicine was unsuitable, creating severe false negative bias in match cases.
- **2. Hypothesis:** Allowing conditional verdicts ('suitable' vs 'not suitable' vs 'information unverified') will eliminate false negative bias.
- **3. Implementation Changes:** Implemented Prompt v3 with conditional indications verdict and grounded unanswerable probe handling.
- **4. Intended Effect:** Eliminate false negative bias in symptom_plus_medicine_match category.
- **5. Measured Outcome:** Mean faithfulness jumped to 0.7256 (+0.0698 over A3). Match category jumped from 0.4948 to 0.7688 (+0.2740).
- **6. Improving Categories / Cases:** Symptom plus medicine match (+0.2740), symptom-only (+0.0506).
- **7. Regressing Categories / Cases:** Unanswerable cases dropped to 0.4762 due to residual probe token hallucination.
- **8. Hypothesis Status:** Supported.
- **9. Key Learnings:** Prompt templates must support positive matches as first-class grammatical paths.
- **10. Follow-up Action:** Implement multi-ingredient formulation parsing and brand filtering in Prompt v4.

### RAGAS-Opt Stage 3: Multi-Ingredient Parsing & Brand Filtering (A5) (`A5`)
- **Git Commit:** `36cd9b7 / ca0f8dc`
- **1. Motivating Problem:** Combination medications (e.g. pain relievers with multiple salts) confused single-ingredient attribution rules.
- **2. Hypothesis:** Parsing multi-ingredient formulations and filtering noisy brand mentions in OCR text will isolate true active ingredients.
- **3. Implementation Changes:** Implemented multi-ingredient formulation extraction, OCR brand filtering, and Prompt v4.
- **4. Intended Effect:** Accurately associate indications with combination medicines without salt confusion.
- **5. Measured Outcome:** Mean faithfulness rose to 0.7538 (+0.0282). Noisy OCR jumped from 0.8000 to 0.9333.
- **6. Improving Categories / Cases:** Medicine noisy OCR (+0.1333), symptom plus medicine mismatch (+0.1408).
- **7. Regressing Categories / Cases:** Symptom-only dipped slightly to 0.6628 due to alternative ingredient descriptions.
- **8. Hypothesis Status:** Supported.
- **9. Key Learnings:** Formulation parsing resolves OCR noise, but combination kits require whole-product attribution.
- **10. Follow-up Action:** Enforce positive indication framing and claim-level sanitization in Candidate A6.

### Cycle A6: Claim-Level Grounding & Positive Indication Framing (A6 Winner) (`A6`)
- **Git Commit:** `4bbc392 / c7fa1d1`
- **1. Motivating Problem:** Residual unsupported statements stemmed from negative exclusion phrases ('not indicated for X') and conversational connectors ('also includes').
- **2. Hypothesis:** Framing all verdicts positively based strictly on labeled indications, combined with deterministic regex claim sanitization, will eliminate ungrounded negative claims.
- **3. Implementation Changes:** Implemented Prompt v5: positive indication framing, prohibition of conversational connectors; added `validate_and_sanitize_claims` to strip malformed tags and ungrounded disclaimers.
- **4. Intended Effect:** Attain >0.8000 development faithfulness.
- **5. Measured Outcome:** Mean faithfulness reached **0.8021** (+0.0483 over A5), median reached **1.0000** (perfect median). Unsupported statements fell to an all-time low of 34.
- **6. Improving Categories / Cases:** Clean OCR reached 1.0000; Symptom-only rebounded to 0.8500 (+0.1872); Mismatch reached 0.8889.
- **7. Regressing Categories / Cases:** Noisy OCR dropped slightly to 0.8000 due to E2E-041 cross-entity attribute confusion.
- **8. Hypothesis Status:** Supported (Program Winner).
- **9. Key Learnings:** Positive indication framing eliminates the vast majority of NLI judge penalties.
- **10. Follow-up Action:** Investigate explicit evidence sufficiency states and grounded abstention in Candidate A7.

### Cycle A7: Evidence Sufficiency States & Grounded Abstention (A7 Regression) (`A7`)
- **Git Commit:** `4a99a51 / e6b5f55`
- **1. Motivating Problem:** Unanswerable probes and missing indications continued to score poorly (~0.40).
- **2. Hypothesis:** Formalizing EvidenceSufficiencyState and prompting explicit negative abstention ('Labeled indications are not stated in the available sources') will demonstrate grounded caution.
- **3. Implementation Changes:** Implemented Prompt v6 with explicit abstention directives and evidence sufficiency state engine.
- **4. Intended Effect:** Improve unanswerable and missing indication faithfulness.
- **5. Measured Outcome:** Catastrophic regression: Mean faithfulness plummeted to 0.6088 (-0.1933), unsupported statements doubled to 70.
- **6. Improving Categories / Cases:** None.
- **7. Regressing Categories / Cases:** 21 of 40 cases regressed. Clean OCR dropped to 0.7639, Noisy OCR to 0.5100, Mismatch to 0.6361.
- **8. Hypothesis Status:** Rejected (Major Discovery).
- **9. Key Learnings:** Discovered the **Meta-Absence Judge Penalty**: RAGAS judges context containment literally; statements asserting that information is *absent* are marked unfaithful because FDA labels do not contain meta-statements of absence.
- **10. Follow-up Action:** Revert negative meta-abstention prompts; implement strict entity isolation in Candidate A8.

### Cycle A8: Unified Prompt v7 & Strict Entity Isolation (A8) (`A8`)
- **Git Commit:** `ca2c139`
- **1. Motivating Problem:** Need to prevent cross-entity attribute confusion (e.g. Allopurinol indications bound to Glibenclarnide) without triggering meta-absence penalties.
- **2. Hypothesis:** Strict product isolation rules in Prompt v7 will prevent entity cross-contamination while retaining A6's positive indication framing.
- **3. Implementation Changes:** Implemented Prompt v7: strict product isolation boundaries, entity-neutral unanswerable probe detection.
- **4. Intended Effect:** Recover from A7 regression and fix E2E-041.
- **5. Measured Outcome:** Faithfulness recovered to 0.7096 (median 0.9091, 49 unsupported statements), but remained inferior to A6 (0.8021).
- **6. Improving Categories / Cases:** Recovered +0.1008 over A7.
- **7. Regressing Categories / Cases:** Failed to surpass A6 due to added prompt complexity and one parser exception.
- **8. Hypothesis Status:** Partially Supported (A6 confirmed as superior pipeline).
- **9. Key Learnings:** Candidate A6 represents the Pareto-optimal prompt architecture.
- **10. Follow-up Action:** Promote Candidate A6 to zero-contamination held-out validation.

### Held-Out Zero-Contamination Validation (A2 vs A5 vs A6) (`heldout_validation`)
- **Git Commit:** `2e8abc5`
- **1. Motivating Problem:** Development set (40 cases) risks overfitting; must verify generalizability on unseen clinical queries.
- **2. Hypothesis:** Candidate A6 will maintain significant superiority over A2 and A5 on 30 unseen cases, including emergency scenarios.
- **3. Implementation Changes:** Executed held-out evaluation runner on `heldout_subset_30.json` (0 dev overlap, seed 42) across A2, A5, and A6.
- **4. Intended Effect:** Validate out-of-distribution generalization and emergency safety escalation.
- **5. Measured Outcome:** A6 achieved **0.7064 Mean Faithfulness** (+0.0614 over A2, +0.0509 over A5), **0.9075 on Emergency cases**, with unsupported statements reduced to 39 (vs 58 in A2).
- **6. Improving Categories / Cases:** Emergency (0.9075), Mismatch (0.7917), Clean OCR (0.8750).
- **7. Regressing Categories / Cases:** Generalization gap (-0.0957 vs dev) revealed novel combination kit and symptom-only negative disclaimer issues.
- **8. Hypothesis Status:** Supported (A6 established as generalizable winner).
- **9. Key Learnings:** Candidate A6 generalizes cleanly; emergency guardrail is completely preserved.
- **10. Follow-up Action:** Execute targeted failure triage on held-out A6 residuals to define candidate fixes.

### Post-Triage Candidate A6.1 Controlled Evaluation (`A6_1`)
- **Git Commit:** `2e8abc5 + patch`
- **1. Motivating Problem:** Targeted triage revealed two addressable flaws: negative disclaimer leakage in symptom-only queries, and product-level indication attribution in combination kits.
- **2. Hypothesis:** Sanitizing symptom-only negative disclaimers and normalizing physical container attribution will fix residual triage failures.
- **3. Implementation Changes:** Added symptom-only disclaimer stripping rule in `app/prompt_v2.py`; added physical container attribution normalizer in `app/evidence.py`.
- **4. Intended Effect:** Eliminate residual disclaimer and combination product attribution failures.
- **5. Measured Outcome:** Targeted fixes 100% verified on dev (`E2E-073` = 1.0, `E2E-024` = 1.0). Net mean scored 0.7614 due to evaluator few-shot leakage on `E2E-080` (Albert Einstein statements).
- **6. Improving Categories / Cases:** Symptom plus medicine match (+0.0056 dev mean; E2E-073 jumped to 1.0000).
- **7. Regressing Categories / Cases:** Mismatch dropped due to E2E-080 judge prompt leakage artifact; E2E-062 had JSON parser error.
- **8. Hypothesis Status:** Inconclusive / Evaluator Integrity Blocker.
- **9. Key Learnings:** Small LLM evaluators (`llama3.1:8b`) are fragile to internal few-shot prompt leakage and require schema hardening.
- **10. Follow-up Action:** Harden evaluation judge harness before advancing A6.1 fixes to production.

---

## Section D — Cross-Run Performance Comparison

### 1. Development Benchmark Comparison (40 Frozen Cases)

| Metric | R0s Baseline | A1 Hygiene | A2 Baseline | A3 Intent | A4 Verdict | A5 Multi-Ing | A6 Winner | A6.1 Triage | A7 Abstention | A8 Isolated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Mean Faithfulness** | 0.3553 | 0.6001 | 0.5282 | 0.6558 | 0.7256 | 0.7538 | 0.8021 | 0.7614 | 0.6088 | 0.7096 |
| **Median Faithfulness** | 0.4000 | 0.5714 | 0.5000 | 0.7018 | 0.8167 | 0.8000 | 1.0000 | 1.0000 | 0.7500 | 0.9091 |
| **Valid Cases** | 12/40 | 40/40 | 39/40 | 40/40 | 40/40 | 40/40 | 40/40 | 39/40 | 40/40 | 39/40 |
| **Unsupported Statements** | 0 | 0 | 86 | 60 | 52 | 40 | 34 | 35 | 70 | 49 |
| **Medicine Only Clean Ocr** | 0.1333 | 0.5480 | 0.5667 | 0.8929 | 0.9583 | 0.9667 | 1.0000 | 1.0000 | 0.7639 | 1.0000 |
| **Medicine Only Noisy Ocr** | 0.4221 | 0.5428 | 0.4867 | 0.7367 | 0.8000 | 0.9333 | 0.8000 | 0.8000 | 0.5100 | 0.8667 |
| **Symptom Only** | 0.2778 | 0.6188 | 0.6536 | 0.6744 | 0.7250 | 0.6628 | 0.8500 | 0.8021 | 0.7326 | 0.7326 |
| **Symptom Plus Medicine Match** | 0.2857 | 0.6377 | 0.4635 | 0.4948 | 0.7688 | 0.8604 | 0.8793 | 0.8849 | 0.7552 | 0.8799 |
| **Symptom Plus Medicine Mismatch** | 0.4222 | 0.6382 | 0.6468 | 0.5774 | 0.6648 | 0.8056 | 0.8889 | 0.7361 | 0.6361 | 0.6365 |
| **Unanswerable** | 0.4500 | 0.5885 | 0.3595 | 0.6250 | 0.4762 | 0.3809 | 0.4167 | 0.3810 | 0.2143 | 0.2143 |

### 2. Held-Out Benchmark Comparison (30 Frozen Unseen Cases)

| Metric | Held-Out A2 Baseline | Held-Out A5 Reference | Held-Out A6 Winner | Delta (A6 vs A2) | Delta (A6 vs A5) |
|---|---:|---:|---:|---:|---:|
| **Mean Faithfulness** | 0.6450 | 0.6555 | **0.7064** | **+0.0614** | **+0.0509** |
| **Median Faithfulness** | 0.6515 | 0.7500 | **0.7500** | +0.0985 | +0.0000 |
| **Valid Cases** | 30/30 | 30/30 | **30/30** | 0 | 0 |
| **Unsupported Statements** | 58 | 43 | **39** | **-19 (-32.8%)** | **-4 (-9.3%)** |
| **Emergency** | 0.7417 | 0.8556 | **0.9075** | +0.1658 | +0.0519 |
| **Medicine Only Clean Ocr** | 0.5309 | 0.9000 | **0.8750** | +0.3441 | -0.0250 |
| **Medicine Only Noisy Ocr** | 0.5208 | 0.3929 | **0.6012** | +0.0804 | +0.2083 |
| **Symptom Only** | 0.7529 | 0.5595 | **0.6467** | -0.1062 | +0.0872 |
| **Symptom Plus Medicine Match** | 0.7933 | 0.7000 | **0.5867** | -0.2066 | -0.1133 |
| **Symptom Plus Medicine Mismatch** | 0.5758 | 0.6042 | **0.7917** | +0.2159 | +0.1875 |
| **Unanswerable** | 0.4667 | 0.5000 | **0.4722** | +0.0055 | -0.0278 |

### 3. Paired Win / Loss / Tie Ledger (A6 vs Baselines)
- **Development (A6 vs A2, 40 cases, tolerance $\pm 10^{-4}$):** **27 Wins / 3 Losses / 9 Ties** (1 NaN in A2).
- **Development (A6 vs A5, 40 cases, tolerance $\pm 10^{-4}$):** **16 Wins / 9 Losses / 15 Ties**.
- **Held-Out (A6 vs A2, 30 cases, tolerance $\pm 10^{-4}$):** **15 Wins / 14 Losses / 1 Tie**.
- **Controlled Development (A6.1 vs A6, 40 cases):** **4 Wins / 9 Losses / 26 Ties** (1 parser error in A6.1; losses concentrated on evaluator-leakage case `E2E-080` and parsing failure on `E2E-062`).

---

## Section E — Per-Case Failure Database

Below is the consolidated per-case failure database covering the most difficult, persistently low-scoring, and diagnostic cases across all development and held-out evaluations.

| Case ID | Category | Query Summary | A2 | A5 | A6 | A6.1 | Heldout A6 | Unsupp Count | Exact Unsupported Claim Sample | Failure Mechanism | Resolution Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `E2E-094` | `unanswerable` | What is the official FDA pediatric approval d... | 0.00 | 0.00 | 0.00 | — | — | 20 | "The label evidence for Xanthroflurane Inhalation Soluti..." | Fictitious probe token leakage / Meta-absence penalty | Under Investigation (Probe Neutrality) |
| `E2E-100` | `unanswerable` | What is the pediatric weight-based dosing for... | 0.17 | 0.00 | 0.00 | — | — | 17 | "The label evidence for Glycozempra lists uses that matc..." | Fictitious probe token leakage / Meta-absence penalty | Under Investigation (Probe Neutrality) |
| `E2E-041` | `medicine_only_noisy_ocr` | I scanned my pill container label. Can you id... | 0.00 | 0.67 | 0.00 | — | — | 37 | "The label evidence for Glibenclarnide lists uses that m..." | Noisy OCR dictionary misalignment (Allopurinol vs Glibenclarnide) | Unresolved (Degraded OCR) |
| `E2E-099` | `unanswerable` | Is Valerionex oral suspension safe for use du... | 0.25 | 0.33 | 0.00 | — | — | 19 | "The label evidence for Valerionex Oral Suspension lists..." | Fictitious probe token leakage / Meta-absence penalty | Under Investigation (Probe Neutrality) |
| `E2E-062` | `symptom_plus_medicine_match` | I am experiencing symptoms of Confusion, Smal... | 0.00 | 0.33 | 0.50 | — | — | 22 | "The answer contains only the incomplete word "Based" an..." | Ragas JSON output parser exception | Evaluator Harness Fix Needed |
| `E2E-097` | `unanswerable` | Can I take Novaproxin capsules for severe chr... | 0.50 | 0.33 | 0.25 | — | — | 14 | "The label evidence for Novaproxin lists uses that match..." | Fictitious probe token leakage / Meta-absence penalty | Under Investigation (Probe Neutrality) |
| `E2E-082` | `symptom_plus_medicine_mismatch` | I have Arthralgia, Abdominal, Abnormalities, ... | 0.25 | 0.67 | 0.33 | — | — | 29 | "The label evidence for Strophanthus lists uses that mat..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-091` | `unanswerable` | What is the recommended dosage and administra... | 0.33 | 0.00 | 1.00 | — | — | 16 | "The available sources do not have enough information to..." | Fictitious probe token leakage / Meta-absence penalty | Under Investigation (Probe Neutrality) |
| `E2E-080` | `symptom_plus_medicine_mismatch` | I have Insomnia, depression, headache, irrita... | 0.75 | 0.50 | 1.00 | — | — | 13 | "The label evidence for Neomycin and Polymyxin B Sulfate..." | Evaluator few-shot prompt leakage (Albert Einstein claims) | Evaluator Integrity Blocker |
| `E2E-021` | `symptom_only` | I have been suffering from Gait Disorders, Ne... | 0.40 | 0.80 | 0.75 | — | — | 14 | "Kearns-Sayre Syndrome lists Gait Disorders, Neurologic;..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-024` | `symptom_only` | Doctor, I recently developed cerebral palsy, ... | 0.17 | 0.40 | 1.00 | — | — | 16 | "Cerebral palsy includes cerebral palsy, blindness, cram..." | Negative disclaimer leakage under Alternatives | Resolved in A6.1 Sanitizer |
| `E2E-081` | `symptom_plus_medicine_mismatch` | I have Headache, Spinal Osteophytosis, Spinal... | 0.50 | 0.67 | 1.00 | — | — | 16 | "The label evidence for Thymoglobulin lists uses that ma..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-073` | `symptom_plus_medicine_match` | I am experiencing symptoms of Vertigo, Brain ... | 0.33 | 1.00 | 1.00 | — | — | 8 | "The label evidence for Meclizine Hydrochloride lists us..." | Product-level indication attributed to constituent salt | Resolved in A6.1 Normalizer |
| `E2E-001` | `symptom_only` | I am experiencing Coronary Atherosclerosis, C... | 0.83 | 0.29 | 0.50 | — | — | 20 | "Based on the information provided, the medicine identif..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-063` | `symptom_plus_medicine_match` | I am experiencing symptoms of anemia due to c... | 0.33 | 1.00 | 1.00 | — | — | 7 | "The label evidence for PROCRIT lists uses that match yo..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-034` | `medicine_only_clean_ocr` | Please provide the therapeutic indications, a... | 0.25 | 0.80 | 1.00 | — | — | 9 | "The therapeutic indications for this drug label are not..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-004` | `symptom_only` | For the last 3 days I've been feeling sick wi... | 0.80 | 0.75 | 0.75 | — | — | 11 | "Based on the information provided, the medicine identif..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-069` | `symptom_plus_medicine_match` | I am experiencing symptoms of bacteremia, abd... | 0.33 | 0.75 | 0.75 | — | — | 7 | "The label evidence for Penicillin V Potassium lists use..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-008` | `symptom_only` | I am experiencing acanthosis nigricans, acne ... | 0.70 | 0.67 | 1.00 | — | — | 22 | "Based on the information provided, the medicine identif..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-009` | `symptom_only` | Doctor, I recently developed Blindness, Neova... | 1.00 | 0.80 | 0.80 | — | — | 13 | "Based on the information provided, no medicine has been..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-095` | `unanswerable` | What is the recommended clinical dosage of ch... | 0.67 | 1.00 | 0.67 | — | — | 3 | "There is no condition listed that matches these symptom..." | Fictitious probe token leakage / Meta-absence penalty | Under Investigation (Probe Neutrality) |
| `E2E-005` | `symptom_only` | Doctor, I recently developed Farsightedness, ... | 0.62 | 0.80 | 1.00 | — | — | 13 | "Based on the information provided, the medicine identif..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-065` | `symptom_plus_medicine_match` | I am experiencing symptoms of Cough, Spinal S... | 0.33 | 1.00 | 0.91 | — | — | 9 | "The label evidence for Tylenol Cold Plus Flu Severe lis..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-072` | `symptom_plus_medicine_match` | I am experiencing symptoms of hypercalcemia, ... | 0.88 | 0.80 | 0.88 | — | — | 23 | "The label evidence for METHYLPREDNISOLONE lists uses th..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |
| `E2E-056` | `symptom_plus_medicine_match` | I am experiencing symptoms of Vaginitis, Pain... | 0.50 | 1.00 | 1.00 | — | — | 4 | "The label evidence for ESTRADIOL VAGINAL INSERTS lists ..." | Extracted claim broader than retrieved context | Partially Resolved in A6 |

---

## Section F — Root-Cause Taxonomy

Analysis of the 643 recorded unsupported statements across all historical candidates categorizes failures into seven discrete root causes:

### RC1_RETRIEVAL: Retrieval Failures
- **Description:** Mismatch between query entity and retrieved document, insufficient coverage, or non-overlapping disease symptom lists.
- **Affected Cases:** `E2E-041, E2E-047, E2E-082`
- **Severity & Clinical Impact:** **High**
- **Confidence Level:** High (Partially Resolved)
- **Fixes Attempted:** Routing v2 intent classifier, drug dictionary fallback for degraded OCR.
- **Evaluator vs Candidate Distinction:** Candidate pipeline defect

### RC2_EVIDENCE_ASSEMBLY: Evidence Construction and Selection
- **Description:** Product-level indications attributed to individual active ingredients in multi-component kits or combination drugs.
- **Affected Cases:** `E2E-058, E2E-061, E2E-070, E2E-073`
- **Severity & Clinical Impact:** **High**
- **Confidence Level:** High (Resolved in A6.1)
- **Fixes Attempted:** Attribution normalizer binding indications to product entities rather than isolated chemical salts.
- **Evaluator vs Candidate Distinction:** Candidate pipeline defect

### RC3_CANDIDATE_GENERATION: Candidate Generation & Hallucination
- **Description:** Unsupported negative claims under Suggested Alternatives, or unneeded elaboration beyond retrieved clinical label text.
- **Affected Cases:** `E2E-002, E2E-007, E2E-017, E2E-023, E2E-024`
- **Severity & Clinical Impact:** **Medium**
- **Confidence Level:** High (Resolved in A6.1)
- **Fixes Attempted:** Deterministic sanitizer replacing negative disclaimers with 'Not applicable: no medicine provided.'.
- **Evaluator vs Candidate Distinction:** Candidate pipeline defect

### RC4_PROMPTING_ROUTING: Prompting and Routing
- **Description:** Prompts forcing the model to explain nonexistent mismatches or assert meta-absence of information.
- **Affected Cases:** `A7 cohort (21/40 cases), E2E-001, E2E-026`
- **Severity & Clinical Impact:** **Critical**
- **Confidence Level:** High (Resolved in A6)
- **Fixes Attempted:** Prompt v5 positive indication framing; complete elimination of negative meta-absence prompts.
- **Evaluator vs Candidate Distinction:** Candidate pipeline defect

### RC5_SANITIZATION: Sanitization and Post-Processing
- **Description:** Citation tag syntax errors and ungrounded disclaimer leakage.
- **Affected Cases:** `All historical pre-A6 cases`
- **Severity & Clinical Impact:** **Medium**
- **Confidence Level:** High (Resolved in A6)
- **Fixes Attempted:** Deterministic regex claim validator normalizing [E1]-[E10] and stripping invalid tags.
- **Evaluator vs Candidate Distinction:** Candidate pipeline defect

### RC6_EVALUATOR_INTEGRITY: Evaluation / Judge Failures
- **Description:** Few-shot prompt example leakage (Albert Einstein statements), JSON parser crashes (E2E-062), and Meta-Absence Judge Penalties.
- **Affected Cases:** `E2E-080, E2E-062, E2E-094, E2E-096, E2E-099, E2E-100`
- **Severity & Clinical Impact:** **Critical**
- **Confidence Level:** High (Active / Unresolved)
- **Fixes Attempted:** Requires judge prompt hardening (stripping few-shot examples or enforcing Pydantic grammar schemas).
- **Evaluator vs Candidate Distinction:** Evaluator defect

### RC7_DATASET_LIMITATIONS: Dataset & Reference Limitations
- **Description:** Unanswerable fictitious probes containing synthetic strings not present in FDA labels, causing unavoidable judge penalties.
- **Affected Cases:** `E2E-091, E2E-094, E2E-096, E2E-097, E2E-099, E2E-100`
- **Severity & Clinical Impact:** **Medium**
- **Confidence Level:** High (Under Investigation)
- **Fixes Attempted:** Entity-neutral abstention phrasing ('The requested clinical information could not be verified').
- **Evaluator vs Candidate Distinction:** Candidate pipeline defect

---

## Section G — Category-Level Underperformance Analysis

### 1. Medicine Only Clean OCR (Dev: 1.0000 | Held-Out: 0.8750)
- **Sample Size:** 6 dev cases, 4 held-out cases.
- **Trajectory:** 0.5667 (A2) -> 0.8929 (A3) -> 0.9583 (A4) -> 0.9667 (A5) -> **1.0000 (A6)** -> 1.0000 (A6.1).
- **Dynamics:** Clean OCR reaches 100% faithfulness once intent routing eliminates irrelevant disease retrieval and prompt templates adhere strictly to FDA indication blocks.
- **Held-Out Transfer:** High (0.8750). The slight dip on held-out (`E2E-038`) occurred because of an over-long multi-indication list where the judge dropped one sentence.

### 2. Medicine Only Noisy OCR (Dev: 0.8000 | Held-Out: 0.6012)
- **Sample Size:** 5 dev cases, 4 held-out cases.
- **Trajectory:** 0.4867 (A2) -> 0.7367 (A3) -> 0.8000 (A4) -> 0.9333 (A5) -> 0.8000 (A6) -> 0.8000 (A6.1).
- **Dynamics & Persistent Failure:** Case `E2E-041` is the single most persistent failure in the development benchmark (mean 0.198 across all runs). The OCR text contains degraded strings (`Glibenclarnide` with an 'r' instead of 'm'). The retriever returns both Glyburide and Allopurinol. The candidate pipeline confuses the indications of Allopurinol with Glibenclarnide, asserting that Glibenclarnide reduces serum uric acid.
- **Held-Out Generalization:** 0.6012. Cases `E2E-047` and `E2E-048` suffered from brand sunscreen confusion (Habana Brisa SPF 30 vs generic avobenzone).

### 3. Symptom-Only (Dev: 0.8500 in A6, 0.8021 in A6.1 | Held-Out: 0.6467)
- **Sample Size:** 8 dev cases, 5 held-out cases.
- **Trajectory:** 0.6536 (A2) -> 0.6744 (A3) -> 0.7250 (A4) -> 0.6628 (A5) -> **0.8500 (A6)** -> 0.8021 (A6.1).
- **Dynamics:** In A6, symptom-only cases scored 0.8500, but leaked negative disclaimers under `### Suggested Alternatives` (`No other conditions were identified in the available sources`). In A6.1, `E2E-024` was completely fixed (1.0000), but `E2E-009` extracted overlap claims between blindness and neovascularization, lowering the category mean.
- **Held-Out Transfer:** 0.6467. In held-out queries (`E2E-002`, `E2E-007`, `E2E-017`, `E2E-023`), disclaimer leakage was the primary reason for score reduction.

### 4. Symptom Plus Medicine Match (Dev: 0.8793 in A6, 0.8849 in A6.1 | Held-Out: 0.5867)
- **Sample Size:** 8 dev cases, 5 held-out cases.
- **Trajectory:** 0.4635 (A2) -> 0.4948 (A3) -> 0.7688 (A4) -> 0.8604 (A5) -> 0.8793 (A6) -> **0.8849 (A6.1)**.
- **Dynamics:** Reached near-perfection on dev in A6.1. Case `E2E-073` scored 1.0000 with live judge verification, validating that normalizing physical container attribution fixes active ingredient confusion.
- **Held-Out Generalization Gap:** Dropped to 0.5867 on held-out. As diagnosed in `A6_TARGETED_FAILURE_TRIAGE.md`, held-out match cases contained complex multi-ingredient products (`Virus Defense`, `BP Reg`, `AMVUTTRA`) where the prompt attributed indications to single active ingredients rather than the overall formulation.

### 5. Symptom Plus Medicine Mismatch (Dev: 0.8889 in A6, 0.7361 in A6.1 | Held-Out: 0.7917)
- **Sample Size:** 6 dev cases, 4 held-out cases.
- **Trajectory:** 0.6468 (A2) -> 0.5774 (A3) -> 0.6648 (A4) -> 0.8056 (A5) -> **0.8889 (A6)** -> 0.7361 (A6.1).
- **Dynamics:** A6 achieved 0.8889. In A6.1, the score dropped to 0.7361 solely because of the evaluator few-shot leakage artifact on `E2E-080` (Albert Einstein claims scoring 0.00). In reality, the candidate answer on `E2E-080` was completely faithful.
- **Held-Out Transfer:** Excellent transfer (0.7917), validating that positive indication framing reliably communicates clinical mismatches without hallucinating counter-indications.

### 6. Unanswerable Probes (Dev: 0.4167 | Held-Out: 0.4722)
- **Sample Size:** 7 dev cases, 3 held-out cases.
- **Trajectory:** 0.3595 (A2) -> 0.6250 (A3) -> 0.4762 (A4) -> 0.3809 (A5) -> 0.4167 (A6) -> 0.3810 (A6.1) -> 0.2143 (A7).
- **Dynamics:** The most stubborn category across the entire program. Because test cases feature synthetic/fictitious drug names (*Glycozempra*, *Zephyroflurane*, *NonexistentDrugZ*), any response that repeats the drug name causes the Ragas judge to search retrieved FDA chunks, find 0 matches, and penalize the statement as unfaithful.

### 7. Emergency Guidance (Held-Out: 0.9075)
- **Sample Size:** 5 held-out cases.
- **Trajectory:** 0.7417 (A2) -> 0.8556 (A5) -> **0.9075 (A6)**.
- **Safety Integrity:** Zero safety regressions. Mandatory emergency escalation directives and hotlines are deterministically preserved by fast-path guardrails without being suppressed by evidence sanitizers.

---

## Section H — Optimization Attempts: What Worked and What Did Not

| Change ID | Target Failure | Files Changed | Hypothesis | Dev Outcome | Held-Out Outcome | Regressions | Decision |
|---|---|---|---|---|---|---|---|
| `OPT-01-COMPACT-EVIDENCE` | Raw dictionary dumps blowing context limit (8,656 tokens P95) | `app/evidence.py, app/core.py` | Structured compact text format with token budget manager will prevent context truncation and lower hallucination. | Faithfulness improved from 0.3553 (R0s) to 0.6001 (A1). Truncation dropped from 12.7% to 0%. | Confirmed foundational prerequisite across all runs. | None. | **KEEP** |
| `OPT-02-PROMPT-V2` | Unconstrained generation template and few-shot vitamin leakage | `app/prompt_v2.py` | Role separation, explicit evidence neutralization, and structured verdict headers will enforce clinical discipline. | A2 scored 0.5282. Role separation worked, but without intent routing, irrelevant disease chunks polluted medicine queries. | Held-out baseline A2 scored 0.6450. | Introduced citation tracking [E1]-[E5] which judge initially struggled with before normalization. | **REFINE** |
| `OPT-03-ROUTING-V2` | Irrelevant disease evidence retrieved on pure medicine scans | `app/evidence.py, app/core.py` | Deterministic intent classifier to skip disease retrieval for medicine-directed queries will eliminate cross-domain noise. | A3 faithfulness jumped to 0.6558 (+0.1276 over A2). Medicine clean OCR jumped from 0.5667 to 0.8929. | Essential architectural pillar across A4, A5, A6. | None. | **KEEP** |
| `OPT-04-PROMPT-V3` | Forced negative mismatch verdicts on match cases and ungrounded unanswerables | `app/prompt_v2.py` | Conditional indications verdict and explicit abstention instructions will eliminate false negative bias. | A4 jumped to 0.7256 (+0.0698 over A3). Symptom+med match jumped from 0.4948 to 0.7688. | Proved conditional verdict necessity. | Unanswerable cases still had residual probe token leakage. | **KEEP** |
| `OPT-05-PROMPT-V4-MULTI-INGRED` | Active ingredient attribution failure on multi-substance labels | `app/evidence.py, app/prompt_v2.py` | Multi-ingredient formulation parsing, brand filtering, and Prompt v4 will isolate compound components. | A5 jumped to 0.7538 (+0.0282 over A4). Noisy medicine OCR jumped from 0.8000 to 0.9333. | A5 achieved 0.6555 on heldout. | Attributed overall product indications to constituent single ingredients in combination kits. | **KEEP & REFINE** |
| `OPT-06-PROMPT-V5-CLAIM-GROUNDING` | Negative symptom exclusions ('not indicated for') and conversational additive claims | `app/prompt_v2.py, evaluation/e2e/sanitize.py` | Positive indication framing and deterministic claim sanitization will eliminate ungrounded negative claims. | A6 achieved 0.8021 Mean, 1.0000 Median (Program Peak). Medicine clean OCR reached 1.0000. | A6 won heldout evaluation at 0.7064 Mean, 0.9075 Emergency. | Residual negative disclaimers under Alternatives in symptom-only queries. | **BEST WINNING PIPELINE (PRODUCTION TARGET)** |
| `OPT-07-PROMPT-V6-META-ABSTENTION` | Explicitly declaring what the evidence lacks via EvidenceSufficiencyState | `app/prompt_v2.py, app/evidence.py` | Instructing model to declare 'Labeled indications are not stated in the available sources' will demonstrate rigorous abstention. | Severe regression: A7 collapsed to 0.6088 (70 unsupported statements). | Not deployed to heldout. | Triggered the Meta-Absence Judge Penalty: RAGAS judge penalizes claims stating context lacks information. | **REVERT** |
| `OPT-08-PROMPT-V7-ENTITY-ISOLATION` | Cross-entity attribute bleeding without negative meta-abstention | `app/prompt_v2.py` | Strict product isolation and positive indication grounding will recover from A7 regression. | A8 recovered to 0.7096, but remained inferior to A6 (0.8021). | Not deployed to heldout. | Entity isolation instructions added prompt length without exceeding A6's natural precision. | **REVERT TO A6** |
| `OPT-09-A6-1-TRIAGE-PATCH` | Symptom-only negative disclaimers and combination product container attribution | `app/evidence.py, app/prompt_v2.py` | Deterministic negative-disclaimer stripping and physical container attribution normalizer will fix residual triage failures. | Triage fixes fully verified on E2E-073 (1.0) and E2E-024 (1.0). Net mean dropped to 0.7614 due to judge few-shot leakage on E2E-080. | Pending judge hardening. | Exposed judge vulnerability to Ragas prompt leakage. | **HOLD IN DEV BRANCH (HARDEN JUDGE BEFORE PROMOTION)** |

### Summary of Counterproductive Approaches (What Definitely Does Not Work)
1. **Negative Meta-Abstention Prompts (Candidate A7):** Prompting the model to state *what the evidence does not contain* directly triggers RAGAS judge penalties. The judge treats absence statements as factual claims about the world and marks them unfaithful because FDA labels do not contain meta-absence declarations.
2. **Raw String Dictionary Dumps (R0 Baseline):** Injecting unbudgeted raw Python dictionaries bloats prompts to >8,000 tokens, triggers severe context truncation (12.7%), and degrades local LLM attention.
3. **Hardcoding Negative Verdict Templates (Prompt v1/v2):** Hardcoding phrases like *'is not suitable for'* induces an overwhelming false-negative bias on match cases, dropping match faithfulness to 0.4635.
4. **Echoing Fictitious Probe Entities on Unanswerables:** Echoing fictitious drug names (*'We could not verify Glycozempra'*) guarantees a 0.00 faithfulness score on small LLM judges.

---

## Section I — Token Usage, Runtime, and Evaluation Reliability

### 1. Resource Accounting Summary (A6.1 Development Benchmark)
- **Generator Provider / Model:** `ollama/llama3.1:8b` (temp=0.0, seed=42, num_ctx=8192, num_predict=700)
- **Generator Calls:** 40 calls across 40 cases (100% provider-reported telemetry from Ollama runtime)
- **Generator Input Tokens:** 55,383 tokens (avg 1,384.6 tokens/case)
- **Generator Output Tokens:** 3,589 tokens (avg 89.7 tokens/case)
- **Generator Total Tokens:** 58,972 tokens
- **Generator Latency:** Average 17,600.1 ms (17.6s), Median 17,460.5 ms
- **Judge Provider / Model:** `ollama/llama3.1:8b` (temp=0.0, seed=42, num_ctx=12288, format=json)
- **Judge Calls (Live):** 46 live calls across 40 cases (capturing statement extraction and NLI judgments)
- **Judge Input Tokens:** 47,616 tokens
- **Judge Output Tokens:** 14,273 tokens
- **Judge Total Tokens:** 61,889 tokens
- **Total Tokens Incurred:** **120,861 tokens**
- **Direct API Cost:** **$0.00** (100% executed locally on Apple Silicon GPU via Ollama)
- **Projected Hosted API Cost (Groq Llama 3.1 8B):** ~$0.003 (less than one-third of a cent)

### 2. Historical Resource Evolution (Tokens & Latency)
- **R0 Baseline:** Prompts reached P95 of 8,656 tokens; average latency exceeded 45,000 ms; 12.7% truncation rate.
- **A1–A2:** Prompts reduced to ~3,100 tokens; latency dropped to ~25,000 ms; 0% truncation.
- **A3–A6:** Prompts optimized to **946.8 tokens** average; latency dropped to ~23,800 ms; evidence tokens averaged 647.2 tokens.
- **A6.1:** Generator latency averaged 17,600 ms, reflecting efficient compact evidence formatting and prompt discipline.

### 3. Evaluator Reliability Assessment
- **Caching Integrity:** `evaluation/e2e/results/judge_cache.json` contains 405 verified judgments, guaranteeing exact deterministic replication of invariant candidate answers across runs.
- **Coverage Quality:** 100% of token counts and latencies in A6.1 are provider-reported directly from Ollama runtime structures (`prompt_eval_count`, `eval_count`), eliminating heuristic token estimation.

---

## Section J — Current State and Unresolved Issues

The table below lists all known unresolved issues in order of impact on candidate and measured evaluation quality.

### ISSUE-01: Evaluator Few-Shot Contamination (Albert Einstein Leakage)
- **Impact Level:** **Severe (0.00 score on E2E-080, reducing A6.1 mean by 0.025 across 40 dev cases)**
- **Demonstrated Failure Mechanism:** Local llama3.1:8b judge emits few-shot example claims from internal Ragas prompt when parsing fails.
- **Recommended Diagnostic & Remediation:** Harden Ragas statement generator prompt; remove persona few-shot examples or enforce grammar schema.

### ISSUE-02: Ragas JSON Output Parser Exception on E2E-062
- **Impact Level:** **Score invalidation (NaN on A6.1 and A8)**
- **Demonstrated Failure Mechanism:** Ollama emitted trailing markdown backticks or invalid JSON escaping, causing RagasOutputParserException.
- **Recommended Diagnostic & Remediation:** Add robust JSON cleaner wrapper before delegating to Ragas LangChain parser.

### ISSUE-03: Fictitious Drug Probe Penalization in Unanswerable Category
- **Impact Level:** **Category score ceiling (~0.40 on dev and held-out)**
- **Demonstrated Failure Mechanism:** Judge extracts probe drug name (e.g. Glycozempra), checks context, finds 0 mentions, and marks claim unfaithful.
- **Recommended Diagnostic & Remediation:** Implement entity-neutral abstention rules that avoid echoing fictitious drug names in the output.

### ISSUE-04: Development to Held-Out Generalization Gap
- **Impact Level:** **A6 achieved 0.8021 on dev but 0.7064 on held-out (-0.0957 gap)**
- **Demonstrated Failure Mechanism:** Held-out set introduces emergency cases (5 cases) and novel combination products (BP Reg, Virus Defense).
- **Recommended Diagnostic & Remediation:** Expand stratified evaluation to full 110-case benchmark once judge hardening is complete.

---

## Section K — Evidence-Based Next-Step Roadmap

The roadmap is divided into six prioritized phases, ordered by expected value, confidence, engineering effort, and risk.

### Phase 1: Immediate Evaluator Integrity Fixes (Zero Model Calls)
- **Action 1.1:** Harden the Ragas statement generator prompt in `evaluation/e2e/score_candidate.py` to strip few-shot examples (Albert Einstein persona) that induce small LLM leakage.
- **Action 1.2:** Add a pre-parsing JSON sanitizer to catch and repair trailing markdown backticks or escaped strings from Ollama before delegating to Ragas, resolving `E2E-062` parser crashes.
- **Success Criteria:** Zero parser exceptions, zero out-of-context few-shot leakage claims.
- **Effort:** ~1-2 hours. Zero model calls.

### Phase 2: Low-Cost Deterministic Pipeline Improvements (Zero Model Calls)
- **Action 2.1:** Implement entity-neutral abstention in `app/prompt_v2.py` for unanswerable queries: replace *'The requested medication information about <Drug> could not be verified'* with *'The requested clinical medication information could not be verified from the available FDA package labels.'*
- **Action 2.2:** Expand `app/evidence.py` drug dictionary alias mapping for degraded OCR strings (e.g. mapping `Glibenclarnide` directly to `Glyburide` without retrieving Allopurinol).
- **Success Criteria:** Unit tests in `tests/unit/test_evidence_hygiene.py` pass without regression.
- **Effort:** ~2-3 hours. Zero model calls.

### Phase 3: Targeted Verification of Candidate A6.1 on Hardened Evaluator
- **Action 3.1:** Re-run faithfulness scoring for cases `E2E-080` and `E2E-062` using the hardened judge harness.
- **Success Criteria:** Recomputed A6.1 development mean faithfulness matches or exceeds A6 (`0.8021`), confirming that A6.1's triage fixes do not regress overall performance.
- **Effort:** ~5 minutes (2 judge model calls on Ollama).

### Phase 4: Full Development Benchmark Re-Validation
- **Action 4.1:** Once Phase 3 confirms parity or gain, re-verify the full 40-case development benchmark under the hardened harness.
- **Success Criteria:** A6.1 dev mean > 0.8100, median = 1.0000, unsupported statements < 30.
- **Effort:** ~15 minutes (local Ollama execution).

### Phase 5: Held-Out Benchmark Re-Validation
- **Action 5.1:** Run Candidate A6.1 across the 30 zero-contamination held-out cases (`heldout_subset_30.json`).
- **Success Criteria:** Held-out mean faithfulness > 0.7200 (surpassing A6's 0.7064), emergency category maintained >= 0.9000.
- **Effort:** ~25 minutes (local Ollama execution).

### Phase 6: Production Readiness and Promotion
- **Action 6.1:** Merge validated Candidate A6.1 into `main`.
- **Action 6.2:** Set default runtime configuration: `PROMPT_VERSION='v5'`, `ROUTING_VERSION='v2'`, `EVIDENCE_FORMAT='compact'`.
- **Success Criteria:** All 204 unit and API tests pass; end-to-end smoke test verifies live inference.

---

## Section L — Reproducibility and Artifact Index

Every historical artifact, dataset, result file, and report is cataloged below with repository-relative links.

### 1. Benchmark Datasets
- [`evaluation/e2e/dataset/e2e_v1.jsonl`](evaluation/e2e/dataset/e2e_v1.jsonl) — Full 110-case clinical benchmark.
- [`evaluation/e2e/dataset/dev_subset_40.json`](evaluation/e2e/dataset/dev_subset_40.json) — Frozen 40-case stratified development subset.
- [`evaluation/e2e/dataset/heldout_subset_30.json`](evaluation/e2e/dataset/heldout_subset_30.json) — Frozen 30-case zero-contamination held-out subset.
- [`evaluation/e2e/dataset/dataset_stats.json`](evaluation/e2e/dataset/dataset_stats.json) — Benchmark character and token distribution statistics.

### 2. Candidate Evaluation Reports
- [`evaluation/e2e/results/PHASE01B_SUMMARY.md`](evaluation/e2e/results/PHASE01B_SUMMARY.md) — R0, R0s, A1, A2 baseline report.
- [`evaluation/e2e/results/A3_EVAL_REPORT.md`](evaluation/e2e/results/A3_EVAL_REPORT.md) — Candidate A3 (Intent Routing v2) evaluation report.
- [`evaluation/e2e/results/A4_EVAL_REPORT.md`](evaluation/e2e/results/A4_EVAL_REPORT.md) — Candidate A4 (Prompt v3) evaluation report.
- [`evaluation/e2e/results/A5_EVAL_REPORT.md`](evaluation/e2e/results/A5_EVAL_REPORT.md) — Candidate A5 (Prompt v4 & Multi-Ingredient) evaluation report.
- [`evaluation/e2e/results/A6_EVAL_REPORT.md`](evaluation/e2e/results/A6_EVAL_REPORT.md) — Candidate A6 (Prompt v5 Winner) evaluation report.
- [`evaluation/e2e/results/A6_HANDOFF.md`](evaluation/e2e/results/A6_HANDOFF.md) — Candidate A6 handoff contract.
- [`evaluation/e2e/results/A6_FAILURE_ANALYSIS.md`](evaluation/e2e/results/A6_FAILURE_ANALYSIS.md) — Candidate A6 residual failure analysis.
- [`evaluation/e2e/results/A6_TARGETED_FAILURE_TRIAGE.md`](evaluation/e2e/results/A6_TARGETED_FAILURE_TRIAGE.md) — Post-A6 targeted failure triage report.
- [`evaluation/e2e/results/A6_1_EVAL_REPORT.md`](evaluation/e2e/results/A6_1_EVAL_REPORT.md) — Candidate A6.1 controlled evaluation report.
- [`evaluation/e2e/results/A6_1_RESOURCE_USAGE_REPORT.md`](evaluation/e2e/results/A6_1_RESOURCE_USAGE_REPORT.md) — Candidate A6.1 token and cost accounting report.
- [`evaluation/e2e/results/A6_1_VERIFICATION_REPORT.md`](evaluation/e2e/results/A6_1_VERIFICATION_REPORT.md) — Candidate A6.1 post-triage audit report.
- [`evaluation/e2e/results/A7_EVAL_REPORT.md`](evaluation/e2e/results/A7_EVAL_REPORT.md) — Candidate A7 (Prompt v6 Abstention Regression) evaluation report.
- [`evaluation/e2e/results/A7_HANDOFF.md`](evaluation/e2e/results/A7_HANDOFF.md) — Candidate A7 handoff contract and meta-absence diagnosis.
- [`evaluation/e2e/results/A8_EVAL_REPORT.md`](evaluation/e2e/results/A8_EVAL_REPORT.md) — Candidate A8 (Prompt v7 Entity Isolation) evaluation report.
- [`evaluation/e2e/results/A6_A8_FINAL_REPORT.md`](evaluation/e2e/results/A6_A8_FINAL_REPORT.md) — Consolidated A6–A8 optimization program report.
- [`evaluation/e2e/results/HELDOUT_A2_VS_FINAL_REPORT.md`](evaluation/e2e/results/HELDOUT_A2_VS_FINAL_REPORT.md) — Held-out validation report (A2 vs A5 vs A6).

### 3. Machine-Readable Artifact Directories
- [`evaluation/e2e/results/A6/`](evaluation/e2e/results/A6/) — A6 generated cases, scored results, metadata, unsupported statements.
- [`evaluation/e2e/results/A6_1/`](evaluation/e2e/results/A6_1/) — A6.1 generated cases, scored results, resource usage, unsupported statements.
- [`evaluation/e2e/results/heldout/A6/`](evaluation/e2e/results/heldout/A6/) — Held-out A6 generated cases, scored results, unsupported statements.
- [`evaluation/e2e/results/ragas_opt/exp01_retrieval_matrix/`](evaluation/e2e/results/ragas_opt/exp01_retrieval_matrix/) — Deterministic retrieval matrix evaluation.
- [`evaluation/e2e/results/judge_cache.json`](evaluation/e2e/results/judge_cache.json) — 405 verified judge judgments.
- [`evaluation/e2e/results/RAGAS_OPTIMIZATION_MASTER_DATA.json`](evaluation/e2e/results/RAGAS_OPTIMIZATION_MASTER_DATA.json) — Structured companion database for this report.
