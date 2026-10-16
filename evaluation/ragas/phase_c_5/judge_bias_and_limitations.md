# Phase C.5 — Judge Bias, Reference Provenance & Methodological Limitations

**Document Version:** 1.0.0  
**Phase:** C.5 (Paired Ragas Evaluation of Baseline vs Graph-Assisted Responses)  
**Evaluator Framework:** Ragas `0.2.15`  
**Judge Model:** `llama3.1:8b` via Ollama (`http://localhost:11434`, `temperature=0.0`)  
**Generator Model:** `llama3.1:8b` (Phase C.4 frozen responses)  
**Date:** 2026-10-15  

---

## 1. Primary Methodological Caveat: Same-Model Self-Evaluation Bias

A central methodological constraint of this experiment is that **the same model architecture and family (`llama3.1:8b`) served as both the response generator (Phase C.4) and the evaluation judge (Phase C.5)**.

### 1.1 Structural Preference & Style Affinity
LLM judges exhibit well-documented self-preference biases:
1. **Stylistic Affinity:** An 8B Llama model naturally perceives Llama-generated phrasing, sentence rhythms, section headers, and bullet formatting as fluent and logically coherent.
2. **Correlated Evaluation Blindspots:** If the generator omitted a critical clinical caveat because the 8B parameter capacity failed to prioritize it, the identical 8B judge is prone to overlooking the omission during proposition extraction and verification.
3. **Optimistic Faithfulness Scoring:** Complex medical nuances that appear grounded to an 8B model might be flagged as ungrounded or clinically ambiguous by a higher-capacity model (e.g., Llama-3.1-70B or GPT-4o) or a qualified physician.

### 1.2 Mitigation & Experimental Control
- **Greedy Determinism:** The judge was configured with `temperature=0.0` to eliminate sampling jitter.
- **Identical Paired Treatment:** Both baseline and graph-assisted runs were evaluated by the exact same judge with identical prompts and runtime parameters. Relative deltas ($\Delta = \text{Score}_{\text{graph}} - \text{Score}_{\text{baseline}}$) control for baseline judge calibration bias, even if absolute scores reflect model self-favorability.
- **Exploratory Status:** All Ragas scores are explicitly reported as internal model comparative indicators rather than absolute clinical validation metrics.

---

## 2. Reference-Answer Provenance & Epistemic Boundaries

### 2.1 Research Reference Provenance
The reference answers used for Context Precision and Context Recall originate from the Phase C.1.2 corrected narrative reference dataset (`evaluation/benchmark/narrative_references/reference_answers.jsonl`).

Every record in this dataset explicitly carries non-gold metadata:
```json
"verification_provenance": {
  "adjudicator_type": "assistant_authored_source_backed_research",
  "human_reviewed": false,
  "clinical_reviewed": false,
  "official_human_gold": false,
  "basis": "Phase C.1.1 corrected reference answers with verified live external medical evidence (NHS, MedlinePlus, DailyMed, CDC, NIDDK, NHLBI)."
}
```

### 2.2 Gold Isolation Invariant
- **`evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.**
- At no point during Phase C.5 has any model output, reference answer, or AI-assisted judgment been promoted to official clinical gold.

---

## 3. Metric-Specific Limitations

### 3.1 Faithfulness (`faithfulness`)
- **What it measures:** Evidence fidelity—whether the claims in the generated response can be deduced from the retrieved text provided to that run.
- **What it does NOT measure:** Medical truth. If the retrieved context contains an outdated drug indication or inaccurate symptom association, a faithful response reproducing that error receives a high score (1.0).
- **Judge Sensitivity:** Proposition extraction relies on the judge parsing complex multi-clause clinical sentences into discrete claims. Ambiguous syntax can artificially depress faithfulness scores.

### 3.2 Answer Relevancy (`answer_relevancy`)
- **What it measures:** Semantic overlap between reverse-generated synthetic queries and the original user prompt, as computed by `all-MiniLM-L6-v2` cosine similarity.
- **What it does NOT measure:** Factual correctness or medical accuracy. An entirely fabricated answer that discusses the query's keywords with high fluency can achieve an Answer Relevancy score $> 0.95$.

### 3.3 Context Precision (`context_precision`)
- **What it measures:** Reference-guided chunk ranking efficiency. It evaluates whether chunks deemed relevant to the reference answer are placed ahead of irrelevant chunks.
- **Distinction from Phase B Precision@K:** Phase B evaluated deterministic source-ID matching against candidate relevance grades. Phase C.5 Context Precision evaluates whether the LLM judge perceives the text chunk as helpful to constructing the reference answer.
- **Negative Control Ineligibility:** Unanswerable queries have no target factual evidence; measuring retrieval precision against non-existent evidence is mathematically invalid. Thus, negative controls are marked `ineligible_unanswerable_negative_control`.

### 3.4 Context Recall (`context_recall`)
- **What it measures:** Factual claim coverage—whether the retrieved context contains all necessary facts to construct the reference answer.
- **What it does NOT measure:** Exhaustive clinical completeness. It is bounded by the specific facts documented in the narrative reference.

---

## 4. Benchmark Sample Size & Statistical Power

1. **Benchmark Scale ($N = 50$):**
   - The benchmark consists of 50 curated queries spanning 11 categories.
   - For Context Precision and Context Recall, 45 cases are eligible after excluding the 5 unanswerable negative controls.
2. **Statistical Power & Interpretation:**
   - Small sample sizes in stratified subgroups ($N=5$ per category) limit statistical power.
   - Observed differences must be interpreted as exploratory signals rather than generalizable clinical population claims.
   - We report bootstrap 95% confidence intervals and non-parametric Wilcoxon tests to prevent overstating marginal differences.

---

## 5. Summary Declaration

The results of Phase C.5 provide a comparative technical evaluation of baseline hybrid retrieval versus graph-assisted retrieval under controlled experimental conditions. **They do not constitute clinical validation, medical clearance, or proof of production readiness.**
