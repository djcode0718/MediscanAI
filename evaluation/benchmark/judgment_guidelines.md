# MediScanAI — Human Judgment Protocol & Labeling Guidelines

## 1. Overview & Purpose

This document provides the standard operating procedure for human clinical and technical reviewers establishing ground-truth relevance judgments for the **MediScanAI Retrieval Benchmark**.

Ground truth in this benchmark measures **retrieval relevance**, not LLM generation fluency or medical advice generation. A retrieved record is judged purely on whether it contains valid, verifiable source evidence that answers or substantiates the query task.

---

## 2. Graded Relevance Rubric

Relevance is evaluated on a 4-point ordinal scale (0 to 3). Reviewers must assign an integer grade based strictly on verifiable source text:

| Grade | Label | Definition | Retrieval Benchmark Meaning | Medical Example |
| :---: | :--- | :--- | :--- | :--- |
| **3** | **Directly Relevant** | Substantially answers the primary retrieval task with direct factual support. | Core gold document. Essential for answering the clinical query. | For query `"Lipitor"`, drug record `id=53548` (`brand_name="Lipitor"`). For `"absence of menstruation, infertility, and pelvic pain"`, disease chunk `chunk_3001` (`PCOS`). |
| **2** | **Relevant Supporting** | Substantially relates to the query or provides essential supporting context (e.g., generic alternative, multi-ingredient partner, or closely related pathology chunk). | High-value supporting context. Helpful but not the singular direct target. | For query `"Advil"`, drug record `id=44` (`generic_name="IBUPROFEN"`). For `"facial tenderness"`, an alternative sinusitis chunk detailing sinus pressure. |
| **1** | **Weakly Related** | Contains topical overlap or mentions an entity/symptom in a peripheral context, but lacks clinical utility for the specific query. | Weak contextual overlap. Should not be counted as a primary hit in strict Recall@K. | For query `"Metformin"`, a combination drug record with primary indication for hypertension where metformin is only listed as a secondary mention without dosage details. |
| **0** | **Not Relevant** | Fails to answer the task, mentions unrelated entities, is spurious keyword matching, or contradicts the query assertion. | Irrelevant. False positive if retrieved. | For query `"Lipitor"`, an unrelated antihypertensive record. For `"Does Lipitor cure acute viral Covid-19 infection?"`, a standard Lipitor record that contains no claim of antiviral efficacy. |

---

## 3. Human Review Workflow

For each evaluation case in `evaluation/benchmark/review_template.csv`:

1. **Understand Retrieval Task:** Read the `query`, `query_category`, and `retrieval_task`. Note whether the query is brand lookup, generic lookup, symptom-to-disease retrieval, or an unanswerable negative control.
2. **Inspect Source Record:** Examine the actual source record identified by `source_record_id` and `evidence_id` in `data/drugs_faiss_data.jsonl` or `data/diseases_faiss_data.jsonl`.
3. **Check Negative Constraints:** Verify that the source record actually contains the claimed fact rather than an inferred or hallucinated claim.
4. **Assign Grade:** Record the integer grade (`0`, `1`, `2`, or `3`) in column `reviewed_grade`.
5. **Document Rationale:** In `judgment_rationale`, write a concise sentence justifying why the source text meets the assigned grade.
6. **Flag Ambiguities:** If the case is borderline or requires multi-physician consensus, enter notes in `adjudication_notes` and set grade to unconfirmed until adjudicated.
7. **Sign Off:** Populate `reviewer_id` (e.g., `REV-CLIN-01`) and `reviewed_at` (ISO-8601 UTC timestamp, e.g., `2026-10-14T10:00:00Z`).

---

## 4. Special Medical Rules & Negative Constraints

### Rule 4.1: Drug Identity vs. Clinical Interchangeability
- Matching brand, generic, or active substance confirms **chemical/product identity**.
- Do **not** treat a brand/generic relationship as proof that two products are bioequivalent or interchangeable across all dosage forms, release mechanisms (e.g., extended-release vs immediate-release), or clinical indications unless explicitly documented in the source record.

### Rule 4.2: Free-Text Inference Prohibition
- Never infer clinical facts, off-label indications, contraindications, or side effects that are not explicitly stated in the source record.
- If a drug is known in clinical practice to treat condition X, but record `Y` does not state condition X in `indications_and_usage`, the record cannot be graded `3` for treating condition X.

### Rule 4.3: LLM Independence
- Never use an LLM output, model generation, or AI summary to decide whether a retrieved document is relevant. Ground truth must be established solely by human inspection of the immutable source records.

### Rule 4.4: Graph Evidence Provenance
- Graph-retrieved evidence must be traced directly to real node IDs and relationships in the knowledge graph.
- If a graph result cannot be mapped back to a real `DrugProduct` (integer source ID) or `DiseaseChunk` (chunk ID / integer source ID), it must be assigned grade `0` (unverifiable).

### Rule 4.5: Disease Chunk First-Entry Rule
- In `data/diseases_faiss_data.jsonl`, a disease chunk's first symptom element frequently repeats the disease title verbatim (e.g., `chunk.symptoms[0] == "Gestational Cholestasis"`).
- Reviewers **must exclude** this first symptom entry when assessing symptom relevance if it is merely the disease name after whitespace normalization.

### Rule 4.6: Spelling and Field Irregularities
- Preserve known source anomalies. Specifically, record `id=2305` (`Cinzan`) uses the key `adréactions` instead of `adverse_reactions`. Reviewers must judge the content of this field as valid adverse reaction evidence.

### Rule 4.7: Normalizing Placeholders
- Source fields containing `"none"`, `"n/a"`, `"unknown"`, or whitespace-only strings must be treated as empty/missing data during evaluation comparisons, but the source record itself remains unmodified.

### Rule 4.8: Missing Labels vs. Irrelevant Evidence
- In an incomplete candidate set, an unjudged document is **UNKNOWN**, not grade `0`.
- In official metric calculation, unreviewed items must never be silently converted to grade `0`. They are treated as unadjudicated and trigger pooled review.

### Rule 4.9: Unanswerable & Negative Control Queries
- Queries in category `insufficient_evidence_unanswerable` represent queries with no valid supporting evidence in the corpus.
- If a retriever returns a document that lexically overlaps with keywords in an unanswerable query (e.g., returning Lipitor for `"Does Lipitor cure Covid-19?"`), that document must be graded `0` because it does not support the therapeutic assertion.

---

## 5. Multi-Reviewer Adjudication & Agreement Measurement

When multiple clinical reviewers are participating:

1. **Independent Review:** Reviewers evaluate queries independently without discussing preliminary scores.
2. **Inter-Reviewer Agreement:** Compute Cohen's Quadratic Weighted $\kappa$ (for pair-wise review) or Fleiss's $\kappa$ (for $\ge 3$ reviewers) across the 4-level scale.
3. **Disagreement Adjudication:** Any item where $|\text{grade}_A - \text{grade}_B| \ge 1$ is flagged for consensus conference.
4. **Consensus Rule:** If consensus is achieved, record the agreed grade with `adjudication_notes="Consensus agreed"`. If consensus cannot be achieved, record the conservative lower grade and document the differing clinical interpretations.
5. **Single-Reviewer Transparency:** If only a single reviewer is available, state clearly in `benchmark_metadata.json`: `"inter_reviewer_agreement": "N/A - Single Reviewer"`. Never synthesize or fabricate multi-reviewer scores.

---

## 6. Promotion to Gold Dataset

Only records that satisfy all of the following criteria may be appended to `evaluation/benchmark/gold_judgments.jsonl`:

- `judgment_status` == `"human_reviewed"`
- `reviewer_id` is a verified, non-null reviewer identifier
- `reviewed_at` is an ISO-8601 timestamp
- `relevance_grade` is an integer in $\{0, 1, 2, 3\}$
- `source_record_id` resolves to an existing line in `data/drugs_faiss_data.jsonl` or `data/diseases_faiss_data.jsonl`
