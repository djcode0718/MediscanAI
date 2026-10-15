# MediScanAI — Ground-Truth Evaluation Benchmark (Phase A)

## 1. Executive Summary

This directory contains the **Phase A Ground-Truth Retrieval Benchmark** for MediScanAI. The benchmark serves as the reproducible, scientifically grounded foundation for evaluating:
- Dense FAISS + BM25 + RRF + Cross-Encoder hybrid retrieval
- Optional Neo4j graph retrieval (graph ON vs. graph OFF)
- Future Ragas end-to-end evaluation and Langfuse experiment tracking

The design prioritizes evidence traceability, absence of LLM-hallucinated ground truth, explicit disclosure of unreviewed candidate status, and protection against incomplete-ground-truth bias through a systematic pooling protocol.

---

## 2. Directory Layout

```text
evaluation/benchmark/
├── README.md                      # This document (scope, usage, architecture)
├── build_benchmark.py             # Deterministic benchmark generator (seed=42)
├── benchmark_schema.json          # JSON Schema (Draft 7) for queries and judgments
├── benchmark_metadata.json        # Provenance, versioning, counts, disclaimers
├── candidate_queries.jsonl        # 50 representative evaluation cases across 11 categories
├── candidate_judgments.jsonl      # 57 unverified candidate evidence judgments
├── gold_judgments.jsonl           # 0 rows initially; reserved strictly for human-reviewed records
├── review_template.csv            # Tabular spreadsheet template for human clinical adjudication
├── judgment_guidelines.md         # Detailed human labeling protocol & special medical rules
└── metric_contract.md             # Formal mathematical definitions (Recall@K, MRR, Graph Coverage)
```

---

## 3. Candidate Query Coverage

The benchmark defines **50 representative candidate queries** spanning 11 structured categories:

| Category | Count | Intended Retrieval Task | Example Query |
| :--- | :---: | :--- | :--- |
| `drug_brand_lookup` | 5 | Exact and brand-name product retrieval | `"Lipitor"`, `"Cinzan"` |
| `drug_generic_lookup` | 5 | Generic name formulation retrieval | `"Atorvastatin calcium"`, `"Cinnarizine"` |
| `active_ingredient_lookup` | 5 | Active chemical substance retrieval | `"Metformin"`, `"Lisinopril"` |
| `brand_generic_ingredient_relationship` | 5 | Relational equivalence queries | `"What is the active ingredient in Lipitor?"` |
| `single_symptom_disease_retrieval` | 5 | Isolated clinical symptom search | `"oliguria"`, `"absence of menstruation"` |
| `multi_symptom_disease_retrieval` | 5 | Co-occurring symptom constellation | `"itchy skin particularly on hands and feet during pregnancy"` |
| `synonym_wording_variants` | 5 | Patient lay phrasing & clinical synonyms | `"blocked nose and sinus headache"` |
| `ambiguous_queries` | 5 | Broad or polysemic clinical keywords | `"Metformin"`, `"Cough and fever"`, `"Chest pain"` |
| `insufficient_evidence_unanswerable` | 5 | Negative controls (fictitious/unsupported) | `"NonexistentDrugZ 500mg dosage"`, `"Does Lipitor cure Covid-19?"` |
| `graph_relevant` | 3 | Multi-hop graph relationship retrieval | `"Find all drug products containing Cinnarizine"` |
| `graph_neutral` | 2 | Exact single-record lookups (zero graph benefit) | `"Cinzan adverse reactions"`, `"Tension Headache symptoms"` |
| **Total** | **50** | | |

---

## 4. Evidence Identity Strategy & Composite Keys

To ensure distinct records cannot collapse into duplicate identifiers:
- **Drug Products:** `drug_<source_record_id>` where `<source_record_id>` is the integer row ID in `data/drugs_faiss_data.jsonl` (e.g., `drug_53548`, `drug_2305`).
- **Disease Chunks:** `disease_chunk_<chunk_number>` where `<chunk_number>` matches `chunk.id` in `data/diseases_faiss_data.jsonl` (e.g., `disease_chunk_1`, `disease_chunk_501`).
- **Judgment Identity:** Composite unique key `(case_id, evidence_id)` (e.g., `("MED-BENCH-001", "drug_53548")`).

---

## 5. Candidate Generation vs. Human Ground Truth

A core scientific principle of this benchmark is the strict separation between candidate generation and human gold ground truth:
- **`candidate_judgments.jsonl` (57 records):** Contains candidate source records identified via deterministic matching against source files. Every record has `judgment_status="unverified_candidate"`, `reviewer_id=null`, and `reviewed_at=null`.
- **`gold_judgments.jsonl` (0 records):** Empty file initialized in Phase A. No record may be written here without genuine human clinical review.
- **`review_template.csv`:** Pre-populated spreadsheet for human reviewers to assign grades, write rationales, and record timestamps.

---

## 6. How to Review and Extend the Benchmark

### Reviewing Existing Candidates
1. Open `evaluation/benchmark/review_template.csv` in your preferred spreadsheet or tabular editor.
2. Follow the clinical criteria in [judgment_guidelines.md](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/judgment_guidelines.md).
3. Assign an integer grade (`0`, `1`, `2`, `3`) in column `reviewed_grade`.
4. Enter your reviewer pseudonym in `reviewer_id` and timestamp in `reviewed_at`.
5. Run the promotion script or import reviewed rows into `gold_judgments.jsonl`.

### Adding New Queries
1. Edit `build_benchmark.py` to add new case definitions with verified source record IDs.
2. Re-run `python evaluation/benchmark/build_benchmark.py` (preserves deterministic seed 42).
3. Run benchmark integrity tests: `pytest tests/unit/test_evaluation_benchmark.py`.

---

## 7. Known Repository Constraints Preserved

- **Off-Limits Directory:** `entity_resolution/` is strictly off-limits and was never accessed, inspected, or imported.
- **Source Immutability:** `data/drugs_faiss_data.jsonl` (79,518 records) and `data/diseases_faiss_data.jsonl` (3,411 chunks) are treated as read-only.
- **Drug Dict Boundary:** `data/drug_dict_faiss_data.jsonl` is preserved for baseline lexical/dense retrieval only and never used for graph ground truth.
- **Spelling Anomaly:** Record `id=2305` (`Cinzan`) with key `adréactions` is preserved and accounted for in benchmark queries `MED-BENCH-002`, `MED-BENCH-007`, `MED-BENCH-018`, `MED-BENCH-046`, and `MED-BENCH-049`.
- **First Symptom Entry:** Disease chunks repeating disease name in `symptoms[0]` are filtered during symptom evaluation.
