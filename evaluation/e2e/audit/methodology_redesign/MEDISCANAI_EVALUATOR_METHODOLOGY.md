# MediScanAI Evaluator Calibration & Validation Methodology
**Document:** `evaluation/e2e/audit/methodology_redesign/MEDISCANAI_EVALUATOR_METHODOLOGY.md`  
**Status:** PROPOSED METHODOLOGY / AWAITING HUMAN AUTHORIZATION  
**Author:** Principal ML Evaluation Engineer, Clinical AI Evaluation Researcher, Statistical Evaluation Specialist, Software Quality Architect  
**Date:** 2026-11-01  
**Target System:** MediScanAI Automated Faithfulness Evaluator  
**Authorized Judge Model:** `llama3.1:8b` via Ollama native `/api/chat` (`temp=0.0`, `seed=42`, `format="json"`, `num_ctx=12288`)  

---

## 1. Executive Summary & Purpose

The MediScanAI automated faithfulness evaluator measures whether medical AI generation is strictly grounded in retrieved clinical evidence. In Phase 3B, blinded human clinical adjudication of 136 statement pairs across 39 evaluation cases against the authoritative `llama3.1:8b` judge exposed critical structural and statistical deficiencies:
* **Overall Agreement:** **75.59%** (Target: $\ge 85.0\%$) — **FAIL**
* **Judge-Negative Precision:** **38.64%** (Target: $\ge 80.0\%$) — **FAIL**
* **Judge False-Negative Rate:** **25.47%** (27/106 supported statements falsely rejected)
* **Judge False-Positive Rate:** **19.05%** (4/21 unsupported statements falsely accepted)
* **Baseline B0 Status:** **PROVISIONAL** (Gated per Prompt 3 governance contract)

With a negative precision of 38.64%, **over 61% of the judge's unfaithfulness flags were false alarms** against clinically valid, evidence-grounded statements. The evaluator penalized models that properly abstained on missing context, rejected recognized statutory synonyms (e.g. `Rx Only` vs. "requires prescription"), and missed cross-chunk symptom misattributions.

Previous design revisions (up to Revision 2.3) improved failure taxonomies and accounting, but left fundamental methodological limitations unaddressed:
1. They conflated structural citation integrity with semantic entailment.
2. They lacked separation between retrieval faithfulness and real-world clinical correctness.
3. They treated an inspected 25-case partition as if it were a blind, untouched validation set.
4. They relied on single-annotator human adjudication without measuring inter-rater reliability.
5. They used statement counts without modeling intra-case correlation or addressing extreme class sparsity ($N=17$ held-out negative statements).

This document establishes a redesigned, scientifically defensible, statistically sound, and production-oriented evaluation framework. Its primary objective is to prove whether the authorized judge can reliably measure MediScanAI faithfulness before any engineering or clinical deployment decisions are made.

---

## 2. Forensic Critical Assessment of Previous Methodology

An inspection of historical B0 adjudication artifacts (`adjudication_sheet.csv`, `adjudication_stats.json`, `adjudication_failure_analysis.md`) and Revision 2.3 documents reveals five fundamental limitations in the prior methodology:

### 2.1 Conflation of Deterministic Formatting with Semantic Entailment
In the original evaluator, if an LLM judge produced an invalid chunk ID, hallucinated a quote, or omitted citation brackets, the evaluation pipeline either crashed, converted the parsing failure into an unfaithfulness verdict (`verdict = 0`), or failed silently. This conflated candidate unfaithfulness with evaluator structural incompetence. Conversely, in Revision 2.2/2.3, verifying that a quotation appeared verbatim in a chunk was treated as proof of support, ignoring whether the quoted text actually entailed the specific clinical proposition asserted by the candidate.

### 2.2 Conflation of Retrieval Faithfulness with Clinical Correctness
The legacy evaluation system operated under a dangerous implicit assumption: that an automated faithfulness evaluator acts as a clinical ground-truth authority. In reality:
* A statement can be **100% faithful to retrieved context, but medically false or hazardous** (e.g. if the retrieved chunk contains an outdated, corrupted, or erroneous drug monograph).
* A statement can be **100% medically true according to global pharmacology, but completely unfaithful to retrieved context** (e.g. stating that Metformin causes lactic acidosis when the retrieved chunks discuss only dosage forms).
Failing to isolate these dimensions makes it impossible to distinguish between retrieval failures, generator hallucinations, and evaluator reasoning defects.

### 2.3 Validation Set Contamination (The 25-Case "Held-Out" Illusion)
In Revision 2.0–2.3, the 39 adjudicated cases were partitioned into 13 calibration cases and 25 "held-out" cases. However, during the Phase 3B and Phase 3C investigations, **all 31 disagreements across all 39 cases were forensically audited, cataloged, and discussed in detail in `adjudication_failure_analysis.md`**. Every error in the 25 "held-out" cases (e.g. `ADJ-0009` in `E2E-004`, `ADJ-0020` in `E2E-009`, `ADJ-0074` in `E2E-062`, `ADJ-0080` in `E2E-063`) was known to the engineering team. Treating these 25 cases as an independent, blind validation benchmark violates fundamental machine learning validation hygiene.

### 2.4 Single-Annotator Subjectivity and Unmeasured Inter-Rater Reliability
The 136 human labels were generated by a single clinician. Two statements were labeled `unclear` (`ADJ-0011` and `ADJ-0050`), and several meta-statements (e.g. "No other conditions were identified in available sources") were labeled `supported` despite ambiguous evidence boundaries. Without double-blind annotation and formal inter-rater reliability statistics (Cohen's $\kappa$ or Gwet's $AC_1$), human annotation noise cannot be disentangled from evaluator errors.

### 2.5 Inadequate Sample Size and Clustered Variance Underreporting
The held-out partition contains 77 clean decisive statements across 25 cases. Crucially, **only 17 statements belong to the negative (unsupported) class**. When resampling cases with replacement in a clustered bootstrap, individual cases contribute between 1 and 14 statements. A single case (`E2E-065`) contains 10 statements. Intra-case correlation ($ICC$) inflates the variance of aggregate metrics by a cluster design effect ($DEFF$) of 1.6 to 2.2. With only 17 negative instances, the 95% confidence interval for Negative Precision is $[25.7\%, 53.4\%]$—far too wide to reliably detect whether the evaluator satisfies the $\ge 80.0\%$ production gate.

---

## 3. Redesigned Three-Layer Evaluation Architecture

To resolve the conflation of responsibilities, the evaluation framework is decomposed into three strictly separated, decoupled layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MediScanAI Evaluator Input                        │
│   (Candidate Answer, Retrieved Chunks [E1]..[En], Clinical Query Metadata)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LAYER A: Deterministic Structural Validator                 │
│  - Validates JSON schema adherence (Pydantic model)                         │
│  - Verifies cited chunk IDs exist in context input                          │
│  - Verifies cited quotes match context chunks via exact verbatim substring   │
│  - Programmatic token scanner: flags false absence if entity is in context  │
│  * Output: VALID_STRUCTURAL_ENVELOPE or RETRY_STRUCTURAL_REPAIR (max 2x)   │
│  * Invariant: Evaluator formatting failure NEVER yields candidate penalty  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LAYER B: Semantic Faithfulness Evaluator                    │
│                 (Authoritative Judge: llama3.1:8b)                          │
│  - Atomic proposition decomposition of candidate claims                     │
│  - Semantic entailment verification against Layer A validated anchors       │
│  - Scope classification: Evidence-scoped limitation vs. Ontological claim   │
│  - Entity-attribute binding: Prevents cross-chunk symptom misattribution    │
│  - Multi-chunk synthesis & clinical synonym normalization                   │
│  * Output: Statement Verdict (1 = Faithful, 0 = Unfaithful, null = ParseErr)│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             LAYER C: Independent Clinical Correctness Assessor              │
│                 (Decoupled Clinical Reference Engine)                       │
│  - Evaluates real-world pharmacological accuracy against clinical reference │
│  - Completely decoupled from retrieval context contents                     │
│  - Generates 2x2 Orthogonal Evaluation Matrix:                              │
│    (Faithful + Correct, Faithful + Incorrect, Hallucinated + Correct, etc.) │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Layer A: Deterministic Structural Validation
Layer A executes programmatically prior to and following LLM judge generation. It contains zero LLM reasoning and guarantees technical integrity:
1. **JSON Schema Enforcement:** Enforces Pydantic typing for all evaluator outputs.
2. **Chunk ID Existence:** Verifies that every cited chunk identifier (e.g. `[E3]`) exists in the input context payload.
3. **Quotation Authenticity:** Checks that every cited quotation matches the referenced chunk text as an exact substring.
4. **Decoupled Failure Semantics:** If the LLM judge hallucinates a chunk ID or quote, Layer A intercepts the response and triggers a targeted format repair prompt (max 2 retries). If repair fails, the statement is recorded as `evaluator_invalid_parse` with `score = null`. It is **never converted into candidate unfaithfulness (`verdict = 0`)**.
5. **Token Absence Scanning:** Scans context chunks for normalized entity names (e.g. "Erythropoietin", "Procrit"). If a candidate asserts an entity is absent, but Layer A finds the entity token in context, Layer A flags the statement as a potential false absence.

### 3.2 Layer B: Semantic Faithfulness Evaluation
Layer B is executed by the authorized `llama3.1:8b` judge using a strictly calibrated structured prompt (`ClinicalNLIStatementPrompt`):
1. **Atomic Proposition Decomposition:** Deconstructs complex candidate sentences into single testable clinical assertions.
2. **Semantic Entailment:** Determines whether the verified anchor text semantically entails the atomic claim.
3. **Abstention Scope Discrimination:** Differentiates between:
   * *Evidence-Scoped Limitation (Category A/B):* "Available sources do not mention pediatric dosing" $\rightarrow$ **Faithful (`verdict = 1`)** if chunk lacks pediatric dosing.
   * *Global Ontological Assertion (Category C/D):* "This drug has no pediatric dosing" or "This drug is unsafe for children" $\rightarrow$ **Unfaithful (`verdict = 0`)** if context merely omits the topic.
4. **Entity-Attribute Binding:** Explicitly tests whether the subject entity in chunk `[Ei]` is the actual recipient of the attribute in chunk `[Ej]`, preventing cross-chunk symptom blending (e.g. assigning myoclonus insomnia to epilepsy).
5. **Statutory and Clinical Synonymy:** Authorizes standard regulatory equivalents (`Rx Only` $\equiv$ "prescription required"; `tablets USP` $\equiv$ "standard oral tablet") while rejecting false equivalences (e.g. OTC $\ne$ Rx).

### 3.3 Layer C: Independent Clinical Correctness Assessment
Layer C resolves the conflation between context faithfulness and real-world medical safety. It reports clinical correctness on a separate axis, producing a $2 \times 2$ Orthogonal Evaluation Grid:

| Quadrant | Retrieval Faithfulness (Layer B) | Medical Correctness (Layer C) | Diagnostic Classification | Clinical Risk Profile |
|---|:---:|:---:|---|---|
| **Q1: Grounded & True** | **Faithful (1)** | **Correct (1)** | Ideal RAG performance. | Safe for clinical decision support. |
| **Q2: Grounded but False** | **Faithful (1)** | **Incorrect (0)** | **Corrupted Retrieval Defect.** Model reproduced an erroneous context chunk. | High risk: RAG system regurgitates erroneous medical literature. |
| **Q3: Hallucinated but True** | **Unfaithful (0)** | **Correct (1)** | **Parametric Memory Fallback.** Model stated a true fact not found in context. | Moderate risk: Factually correct, but violates audit trail and provenance. |
| **Q4: Hallucinated & False** | **Unfaithful (0)** | **Incorrect (0)** | **Total Generation Defect.** Pure hallucination with medical falsehood. | Severe risk: Fabricated clinical misinformation. |

---

## 4. Dataset Governance and Tripartite Segregation

To establish valid, reproducible calibration and validation, evaluation data is strictly segregated into three distinct datasets:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Evaluation Data Segregation                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
[Dataset 1: Historical Diagnostic] [Dataset 2: Calibration]   [Dataset 3: Independent Validation]
 - 136 Statements (39 Cases)        - 13 Cases (50 Statements) - Unseen Cases (60 to 100 Cases)
 - Preserved Immutable Historical   - Permitted tuning dataset - Fully Blind, Untouched Benchmark
 - Role: Failure mode analysis,     - Role: Prompt formatting, - Role: Generalization measurement,
   root-cause tracing, regression     demonstration selection    final certification gate
```

### 4.1 Dataset 1: Historical Diagnostic Dataset ($N=136$ Statements, 39 Cases)
* **Composition:** The complete set of 136 statement records evaluated during Phase 3B (109 supported, 25 unsupported, 2 unclear; 7 contaminated).
* **Role:** Read-only historical benchmark and diagnostic failure catalog.
* **Governance Rule:** Never used for prompt tuning or validation claims. Preserved permanently in `evaluation/e2e/results/B0/adjudication_sheet.csv`.

### 4.2 Dataset 2: Calibration Tuning Dataset ($M=13$ Cases, $N=50$ Statements)
* **Composition:** 13 carefully selected cases representing 15 historical disagreements and 35 agreements (including 16 designated primary regression controls).
* **Role:** The only data permitted to be used for prompt engineering, demonstration tuning, and absence trigger calibration.
* **Governance Rule:** Tuning is strictly confined to these 13 cases. Zero statements from outside this partition may be consulted during prompt calibration.

### 4.3 Dataset 3: Independent Validation Dataset (Unseen Cases)
* **Composition:** A newly sampled, previously uninspected cohort of clinical queries and generated answers.
* **Exclusion Invariant:** Must NOT reuse the 25 "held-out" cases from `dev_subset_40` that were audited during Phase 3B/3C triage.
* **Stratified Clinical Sampling:**
  * Clean indication and dosage queries (positive controls).
  * Unanswerable / evidence-absent queries requiring qualified abstention (negative controls).
  * Statutory synonym cases (`Rx Only`, generic/brand naming).
  * Multi-entity distractors (combination medicines, cross-chunk indications).
  * Noisy OCR and ambiguous compound claims.
* **Sample Size Requirement:** Statistically derived in Section 7 to guarantee adequate power for cluster-adjusted metrics.

---

## 5. Human Clinical Annotation Protocol & Inter-Rater Reliability

To eliminate single-annotator subjectivity, Dataset 3 must be adjudicated under a rigorous double-blind clinical protocol:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Double-Blind Annotation Workflow                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
[Reviewer 1: Independent Clinician]           [Reviewer 2: Independent Clinician]
 - Blind to model identity                     - Blind to model identity
 - Blind to automated judge verdict            - Blind to automated judge verdict
 - Reviews statement + context chunks          - Reviews statement + context chunks
 - Labels: Supported / Unsupported / Unclear   - Labels: Supported / Unsupported / Unclear
        │                                                             │
        └──────────────────────────────┬──────────────────────────────┘
                                       ▼
                       [Consensus & Reliability Engine]
                        - Computes Percentage Agreement
                        - Computes Cohen's Kappa & Gwet's AC1
                        - Concordant labels -> Certified Ground Truth
                        - Discrepant labels -> Routed to Arbiter (Reviewer 3)
```

### 5.1 Adjudication Standards and Decision Rules
1. **Blinding:** Clinicians receive statements stripped of candidate model name, generation metadata, and LLM judge verdict. They inspect only the `query`, `candidate_statement`, and `retrieved_evidence_chunks`.
2. **Standardized Decision Rules:**
   * `SUPPORTED`: The statement's clinical meaning is directly entailed by the cited evidence chunks without requiring unstated assumptions.
   * `UNSUPPORTED`: The statement introduces facts, dosages, symptoms, or contraindications not stated in context, or asserts global nonexistence when context merely omits evidence.
   * `UNCLEAR`: The statement is syntactically vacuous, internally contradictory, or evidence chunks present unresolved contradictions.
3. **Inter-Rater Reliability Thresholds:**
   * Inter-rater agreement must achieve **Cohen's $\kappa \ge 0.75$** and **Gwet's $AC_1 \ge 0.80$** across the double-annotated set.
   * If inter-rater agreement falls below $\kappa = 0.70$, annotation guidelines must be revised and annotators recalibrated before proceeding.

---

## 6. Controlled Calibration Experiments & Ablation Matrix

Prompt engineering must not proceed via ad-hoc trial and error. We define eight formal hypotheses tested through a sequence of controlled ablation experiments:

### 6.1 Formal Hypotheses
* **H1 (Abstention Semantics):** Explicit demonstration of evidence-scoped abstention reduces false rejections of valid limitation statements by $\ge 80\%$ without increasing false acceptances of global nonexistence claims.
* **H2 (Atomic Proposition Decomposition):** Pre-decomposing compound statements into single assertions reduces partial-truth classification errors by $\ge 50\%$.
* **H3 (Exact Evidence Anchoring):** Requiring verbatim substring quotations for positive verdicts eliminates hallucinated evidence attribution.
* **H4 (Entity-Attribute Binding):** Forcing explicit pairwise binding between entity names and clinical attributes eliminates cross-chunk symptom misattributions.
* **H5 (Clinical Synonym Normalization):** Incorporating a closed-world regulatory synonym glossary eliminates false negatives on statutory terms (`Rx Only`) without increasing false positives on non-equivalent terms.
* **H6 (Multi-Chunk Attention Structuring):** Deduplicating chunks and prefixing chunks with entity headers eliminates "lost-in-the-middle" attention dropout in long contexts ($>6$ chunks).
* **H7 (Decoupled Structural Failure):** Separating formatting retries from candidate scoring reduces the invalid evaluation rate to $<1\%$ while preventing false unfaithfulness penalties.
* **H8 (Dual-Layer Absence Scanner):** Combining programmatic entity token scanning with model semantic boundary evaluation outperforms prompt-only absence evaluation in both agreement ($\ge 90\%$) and repeatability ($\text{MAD} = 0.00$).

### 6.2 Controlled Ablation Sequence
Each experiment isolates exactly one variable while holding the judge model (`llama3.1:8b`), runtime options (`temp=0`, `seed=42`, `num_ctx=12288`), and calibration dataset ($M=13$) strictly fixed. Every experiment logs to an isolated cache namespace (`evaluation/e2e/cache_v2_exp_*`) and records cryptographic input hashes in a run manifest.

---

## 7. Metrics, Statistical Uncertainty & Sample Size Methodology

### 7.1 Core Classification Metric Suite
All evaluations are computed on clean, decisive statements (excluding parse failures, unclear labels, and quarantined items):
* **Overall Agreement:** $\text{Acc} = \frac{A + D}{A + B + C + D}$
* **Supported Precision:** $\text{Prec}_{\text{sup}} = \frac{A}{A + B}$
* **Judge-Negative Precision:** $\text{Prec}_{\text{unsup}} = \frac{D}{C + D}$
* **Supported Recall:** $\text{Rec}_{\text{sup}} = \frac{A}{A + C}$
* **Negative Recall:** $\text{Rec}_{\text{unsup}} = \frac{D}{B + D}$
* **False-Negative Rate (FNR):** $\text{FNR} = \frac{C}{A + C}$
* **False-Positive Rate (FPR):** $\text{FPR} = \frac{B}{B + D}$
* **Balanced Accuracy:** $\text{BalAcc} = \frac{1}{2}(\text{Rec}_{\text{sup}} + \text{Rec}_{\text{unsup}})$
* **Macro-F1:** $\text{MacroF1} = \frac{F1_{\text{sup}} + F1_{\text{unsup}}}{2}$

### 7.2 Clustered Statistical Uncertainty
Because statements generated within the same case share context chunks and generator style, statement-level observations violate the independent identically distributed (i.i.d.) assumption.
* **Primary Uncertainty Estimator:** **Case-Clustered Bootstrap** ($B = 10,000$ iterations). Entire cases (including all their decisive statements) are resampled with replacement. Empirical percentile bounds $[\theta^*_{0.025}, \theta^*_{0.975}]$ directly reflect intra-case clustering.
* **Supplementary Descriptive Estimator:** Wilson 95% score intervals are reported for individual binomial proportions as descriptive statement-level bounds, but are explicitly documented as *unadjusted for clustering*.
* **Sparse Class Policy:** In bootstrap resampling, if $>5\%$ of replicates lack instances of a sparse class ($B^* + D^* = 0$), the clustered estimator is formally flagged as `unstable_sparse_class` rather than silently replaced.

### 7.3 Mathematical Sample Size Derivation
To achieve a target confidence interval half-width $w$ at confidence level $1 - \alpha = 0.95$, the effective sample size is:
$$n_{eff} = \frac{z_{1-\alpha/2}^2 \cdot p(1-p)}{w^2}$$
Accounting for intra-case statement correlation ($ICC \approx 0.25$) and average statements per case ($\bar{m} \approx 3.5$), the cluster design effect is:
$$DEFF = 1 + (\bar{m} - 1) \cdot ICC = 1 + (2.5 \cdot 0.25) = 1.625$$
Total required statements $N = n_{eff} \cdot DEFF$:
* For Overall Agreement ($p = 0.85$, $w = \pm 0.05$): $n_{eff} = 196 \implies N = 318$ statements across **$\approx 90$ cases**.
* For Negative Precision ($p = 0.80$, $w = \pm 0.08$, negative class prevalence $\pi = 0.25$): $N_{neg} \ge 96 \implies N_{total} \ge 384$ statements across **$\approx 110$ cases**.

We define two validation tiers:
1. **Minimum Viable Validation Design:** 60 cases ($\sim 210$ statements). Agreement CI half-width $\approx \pm 6.5\%$; Negative Precision CI half-width $\approx \pm 11.5\%$.
2. **Preferred High-Quality Validation Design:** 100 cases ($\sim 350$ statements). Agreement CI half-width $\approx \pm 5.0\%$; Negative Precision CI half-width $\approx \pm 8.5\%$.

---

## 8. Redesigned Multi-Tier Acceptance Gates

Acceptance gates are restructured into five distinct, specialized tiers to prevent masking subgroup failures behind aggregate agreement numbers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MediScanAI Five-Tier Acceptance Gates                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        ▼              ▼               ▼               ▼              ▼
    [Tier 1]       [Tier 2]        [Tier 3]        [Tier 4]       [Tier 5]
  Engineering     Calibration     Independent      Clinical      Production
   Integrity      Stability       Validation        Safety       Readiness
```

### Tier 1: Engineering Integrity Gates (Pre-requisites)
1. **Authorized Judge Model:** Strictly `llama3.1:8b` via native Ollama `/api/chat`.
2. **Runtime Options Probe:** Verification of `temperature=0.0`, `seed=42`, `format="json"`, `num_ctx=12288`.
3. **Deterministic Verification Pass:** 100% of positive verdicts possess verified verbatim anchors.
4. **Cache & Manifest Isolation:** Zero writes to historical caches; cryptographic manifest generated.

### Tier 2: Calibration Stability Gates (13 Calibration Cases / 50 Statements)
1. **Calibration Agreement:** Point estimate $\ge 90.0\%$ (45/50).
2. **Calibration Negative Precision:** Point estimate $\ge 85.0\%$.
3. **Adversarial Unit Test Suite:** 100% pass rate (24/24) on `tests/evaluation/test_calibrated_evaluator_adversarial.py`.

### Tier 3: Independent Validation Gates (Unseen Dataset 3)
1. **Overall Agreement:** Point estimate $\ge 85.0\%$, with Case-Clustered Bootstrap 95% lower bound $\ge 75.0\%$.
2. **Judge-Negative Precision:** Point estimate $\ge 80.0\%$, with descriptive Wilson lower bound $\ge 60.0\%$.
3. **False-Negative Rate (FNR):** $\le 12.0\%$ (prevents evaluator skepticism/conservatism).
4. **False-Positive Rate (FPR):** $\le 12.0\%$ (prevents evaluator leniency and hallucination blindness).
5. **Balanced Accuracy:** Clustered Bootstrap point estimate $\ge 85.0\%$.
6. **Repeatability:** Test-retest statement agreement $\ge 98.0\%$ (MAD $\le 0.02$) across two identical no-cache runs.
7. **Invalid Rate:** Parse or runtime failures $\le 3.0\%$.

### Tier 4: Clinical Safety & Subgroup Gates (Dataset 3 Subgroups)
1. **Abstention Subgroup Accuracy:** Agreement $\ge 90.0\%$ on evidence-scoped absence statements.
2. **Entity Attribution Subgroup Precision:** Negative precision $\ge 85.0\%$ on cross-entity distractor statements.
3. **Statutory Synonym Subgroup Recall:** Recall $\ge 95.0\%$ on regulatory equivalence assertions (`Rx Only`).

### Tier 5: Production Readiness Certification
1. **Consensus Certification:** Pass all Tiers 1–4.
2. **Executive Sign-Off:** Independent clinical lead and principal ML evaluation engineer sign-off.
3. **Baseline Transition:** Baseline B0 promoted from `PROVISIONAL` to `ESTABLISHED`.

---

## 9. Failure Analysis and Regression Management Taxonomy

Every discrepancy discovered between automated judge verdicts and human ground truth must be logged into a structured failure catalog. We define nine mutually exclusive defect categories:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Evaluator Failure Taxonomy                            │
└─────────────────────────────────────────────────────────────────────────────┘
  1. CANDIDATE_GENERATION_DEFECT      Candidate produced unfaithful medical claim
  2. RETRIEVAL_CORRUPTION_DEFECT      Retrieved evidence contains corrupted/erroneous facts
  3. EVIDENCE_EXTRACTION_DEFECT       Judge failed to locate verbatim text in long context
  4. ENTITY_ATTRIBUTION_DEFECT        Judge failed to detect cross-entity symptom swapping
  5. CLINICAL_SYNONYMY_DEFECT         Judge rejected recognized medical/regulatory synonym
  6. ABSTENTION_SEMANTIC_DEFECT       Judge inverted evidence-scoped limitation statement
  7. EVALUATOR_REASONING_DEFECT       Judge hallucinated reasoning or external world facts
  8. STRUCTURAL_VALIDATION_DEFECT     Judge output unparseable JSON or invalid chunk IDs
  9. HUMAN_LABEL_UNCERTAINTY          Human adjudicators disagreed or context was ambiguous
```

### 9.1 Structured Disagreement Record Schema
Every logged failure must contain the following fields:
```json
{
  "item_id": "DISAG-0001",
  "case_id": "E2E-VAL-0012",
  "statement": "Text of evaluated claim",
  "judge_verdict": 0,
  "human_consensus_label": "supported",
  "failure_category": "ABSTENTION_SEMANTIC_DEFECT",
  "root_cause_confidence": "confirmed",
  "cited_chunk_id": "[E2]",
  "cited_quote": "Verbatim quote or null",
  "diagnostic_notes": "Judge asserted context did not prove global nonexistence",
  "regression_test_id": "REG-ABS-014",
  "reproduced_in_isolation": true,
  "fix_regression_verified": true
}
```

---

## 10. Complete End-to-End Staged Workflow (Phases A–G)

The implementation and validation of the calibrated evaluator is organized into seven sequential, gated phases:

```
[Phase A: Methodology Design]  ──► [Phase B: Dataset & Annotation] ──► [Phase C: Architecture Implementation]
                                                                                       │
[Phase F: Clinical Review]     ◄── [Phase E: Independent Validation] ◄── [Phase D: Controlled Calibration]
              │
              ▼
[Phase G: Baseline Certification]
```

| Phase | Objective | Key Inputs | Key Deliverables / Outputs | Acceptance Gate | Prohibited Actions |
|---|---|---|---|---|---|
| **Phase A** | Methodology & Architecture Finalization | Revision 2.3 audit artifacts, forensic reports | Redesign package (8 documents) | Human architect approval of methodology package | Zero code implementation; zero prompt edits |
| **Phase B** | Dataset Governance & Annotation | Candidate cases, clinical reviewer panel | Dataset 2 ($M=13$), Dataset 3 (60–100 cases), Blind sheets | Dual-clinician agreement $\kappa \ge 0.75$; zero case leakage | Accessing sealed test data (`evaluation/e2e/data/sealed/`) |
| **Phase C** | Evaluator Architecture Implementation | Validated Layer A/B/C designs | Layer A validator, Layer B prompt, Layer C engine | 100% pass on 55 existing tests + new unit tests | Running benchmark scoring; modifying historical B0 files |
| **Phase D** | Controlled Calibration & Ablations | Dataset 2 ($M=13$ cases), Synthetic suite | Ablation logs (EXP-1 to EXP-8), EXP-FINAL manifest | Tier 1 and Tier 2 gates pass; 100% on 24 synthetic tests | Scoring Dataset 3; tuning on held-out failures |
| **Phase E** | Independent Validation Benchmark | Dataset 3 (unseen cases), Frozen evaluator | Single-pass validation report, Clustered bootstrap CIs | Tier 3 and Tier 4 gates pass; Repeatability MAD $\le 0.02$ | Iterative re-tuning on validation failures; caching |
| **Phase F** | Clinical & Safety Architecture Review | Disagreement inventory, Orthogonal 2x2 matrix | Safety audit report, Residual risk assessment | Clinical lead sign-off; Zero unmitigated high-risk errors | Suppressing observed failure modes |
| **Phase G** | Baseline B0 Certification | Validated B0 rescore pipeline | Certified B0 benchmark report, `STATUS.json` update | Baseline B0 transitions from `PROVISIONAL` to `ESTABLISHED` | Authorizing Prompt 4 without passing all gates |

---

## 11. Component Reuse vs. Redesign Map

To maximize engineering efficiency and preserve proven infrastructure, existing components are categorized into reusable vs. redesign assets:

### 11.1 Reused Without Modification (100% Preserved)
* **`judge_io.py`:** Native Ollama `/api/chat` client with deterministic payload options (`temp=0`, `seed=42`, `format="json"`, `num_ctx=12288`).
* **`cache_v2.py`:** SQLite-backed cache V2 with MD5 hashing, run isolation, and atomic commits.
* **`contamination_guard.py`:** Automatic regex and n-gram prompt leakage detection.
* **`manifest.py`:** SHA-256 run manifest generation and environment capture.
* **`eval_status.py`:** Centralized status reading and atomic JSON updates.

### 11.2 Modified / Refactored
* **`strict_scoring.py`:** Refactored to integrate Layer A decoupled error handling (retry on formatting defect; score as `null` rather than penalizing candidate).
* **`traceable_faithfulness.py`:** Refactored to output atomic proposition records, Layer A anchor verification status, and separate Layer C clinical correctness tags.
* **`reporting.py`:** Enhanced with Case-Clustered Bootstrap calculation and the $2 \times 2$ orthogonal evaluation matrix.

### 11.3 Newly Designed / Implemented
* **`structural_validator.py`:** Layer A deterministic JSON schema, chunk existence, and verbatim quotation validator.
* **`absence_scanner.py`:** Layer A programmatic entity token scanner across deduplicated chunks.
* **`clustered_bootstrap.py`:** Deterministic case-clustered bootstrap module ($B = 10,000$ iterations) with sparse-class handling.
* **`adjudication_intake.py`:** Dual-blind adjudication tool calculating Cohen's $\kappa$ and Gwet's $AC_1$.

---

## 12. Non-Negotiable Governance & Authorization Declarations

* **Authorized Judge Model:** Strictly `llama3.1:8b` via native Ollama `/api/chat`. No substitute models authorized.
* **Sealed Benchmark Protection:** `evaluation/e2e/data/sealed/` remains strictly sealed; `SEALED_AUTHORIZED` is NOT created.
* **Historical Artifact Immutability:** Historical B0 reports, caches, labels, and results are permanently read-only.
* **Baseline B0 Status:** Remains strictly **`PROVISIONAL`**.
* **All Authorization Flags Remain False:**
  * `methodology_design_complete: true`
  * `implementation_authorized: false`
  * `calibration_execution_authorized: false`
  * `human_readjudication_authorized: false`
  * `sealed_data_accessed: false`
  * `historical_artifacts_modified: false`
  * `prompt_4_authorized: false`

*This methodology redesign document is complete and submitted for senior technical and clinical review. Implementation must not commence until explicit human authorization is granted.*
