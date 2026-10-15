# MediScanAI — Phase B Retrieval Evaluation & Evidence Pooling Harness

## 1. Overview & Purpose

The **Retrieval Evaluation & Evidence Pooling Harness** executes retrieval-only evaluations across the hybrid baseline pipeline (dense FAISS + BM25 + RRF + Cross-Encoder reranking) and optional Neo4j graph retrieval.

It is designed to:
1. **Reuse Existing Retrieval Engines:** Direct execution via `MultiRetriever` and `GraphRetriever` without creating duplicate mock or surrogate retrieval code.
2. **Collect Multi-Channel Evidence:** Retrieve candidates from baseline and graph channels independently, preserving native channel rankings.
3. **Deduplicate & Pool:** Merge candidate evidence using stable composite identifiers (`drug_<id>` and `disease_chunk_<chunk_num>`) while maintaining source provenance.
4. **Enforce Ground-Truth Eligibility:** Calculate official metrics (Recall@K, Precision@K, Baseline MRR, Graph-Added Evidence Coverage) strictly where reviewed gold labels exist. Distinguishes four explicit evaluation states:
   - `not_evaluable_no_reviewed_gold_labels`: zero reviewed gold records exist. Official quality scores are withheld.
   - `eligible_reviewed_gold`: case has reviewed relevant evidence; standard retrieval metrics are calculated.
   - `eligible_negative_control`: case has reviewed records confirming zero relevant items exist and is designated as an unanswerable/negative-control query. Evaluated for false-positive count and rejection accuracy.
   - `excluded_no_relevant_gold_evidence`: case has reviewed records with zero relevant items but is not a designated negative control. Excluded from standard retrieval macro-denominators.
5. **No Synthetic Graph or Pooled Ranking:** Baseline MRR is calculated strictly from the baseline retriever's genuine ordered ranking. Because Neo4j graph retrieval orders matches by database identifier (`source_id ASC`), graph results are treated as an unordered candidate set. The harness prohibits emitting synthetic graph MRR or pooled MRR over concatenated lists.
6. **Safely Merge Reviews:** Export pooled evidence to a dedicated run directory without ever overwriting `review_template.csv`. Pre-existing candidate grades and notes are preserved.

---

## 2. Directory Layout & Module Structure

```text
evaluation/retrieval/
├── __init__.py                     # Package initialization
├── schemas.py                      # Data models (RetrievedItem, PooledEvidence, EvaluationSummary)
├── metrics.py                      # Deterministic metric calculations, negative-control metrics & latency percentiles
├── pool_evidence.py                # Identity normalization, cross-channel pooling, and review merge
├── run_retrieval_evaluation.py     # Main CLI orchestrator
└── README.md                       # This documentation
```

---

## 3. Evaluation Modes

The runner supports three evaluation modes via `--mode`:

| Mode | Channels Executed | Intended Use Case | Ranking Semantics |
| :--- | :--- | :--- | :--- |
| `baseline` | `MultiRetriever` (Dense FAISS + BM25 + RRF + Cross-Encoder) | Standalone baseline retrieval benchmarking. Requires no Neo4j connection. | Full genuine relevance ranking (RRF + CrossEncoder scores). Calculates Recall@K, Precision@K, Baseline MRR. |
| `graph` | `GraphRetriever` (Standalone Neo4j Cypher queries) | Standalone graph retrieval benchmarking. Requires Neo4j connection. | Unordered candidate set (`ORDER BY d.source_id ASC`). No synthetic graph MRR emitted. |
| `both` | Baseline + Graph in parallel per case, followed by pooling | Graph ON vs. Graph OFF comparative evaluation and evidence pooling. | Baseline ranking used for Baseline MRR. No synthetic pooled ranking. Graph value measured via overlap, candidate counts, and graph-added coverage. |

---

## 4. Canonical Benchmark Cases & Evidence Counts

Verified machine-generated retrieval counts from canonical benchmark queries:

- **`MED-BENCH-001` (`Lipitor`, `drug_brand_lookup`):**
  - Canonical query: `"Lipitor"` (matches primary target `drug_53548`).
  - Baseline retrieved: 5 candidates (`drug_53548`, `drug_63899`, `drug_3`, `drug_2`, `drug_41823`).
  - Graph retrieved: 2 candidates (`drug_53548`, `drug_63899`).
  - Channel overlap: 2 identical source IDs (`drug_53548`, `drug_63899`).
  - Pooled unique candidates: 5 items.
  - *Note:* Any previous narrative text referring to `MED-BENCH-001` as "aspirin 81 mg" was a typographical error corrected to the canonical query "Lipitor".

- **`MED-BENCH-036` (`Metformin`, `ambiguous_queries`):**
  - Canonical query: `"Metformin"` (tests high-cardinality entity pooling).
  - Baseline retrieved: 5 candidates (`drug_57256`, `drug_20422`, `drug_76560`, `drug_6269`, `drug_8100`).
  - Graph retrieved: 5 candidates (`drug_1397`, `drug_2617`, `drug_3216`, `drug_10756`, `drug_28373`).
  - Channel overlap: 0 identical source IDs (all 10 are distinct valid Metformin formulations).
  - Pooled unique candidates: 10 items preserved with individual source provenance.

---

## 4. Evidence Identity & Provenance

To prevent duplicate evidence representation and avoid collapsing distinct products:
- **Drug Products:** `drug_<source_id>` where `<source_id>` is the integer row index in `data/drugs_faiss_data.jsonl`.
- **Disease Chunks:** `disease_chunk_<chunk_number>` where `<chunk_number>` matches `chunk.id` in `data/diseases_faiss_data.jsonl`.
- **Unresolved Evidence:** Any graph result without verified source provenance is flagged `is_resolved=False` and excluded from coverage calculations.

---

## 5. Output Artifacts

Each evaluation run writes to a timestamped run directory under `evaluation/results/eval_<mode>_<timestamp>/`:

- `run_metadata.json`: Complete execution metadata, git branch, configurations, and summary statistics.
  - `is_dirty` tri-state: `true` (uncommitted modifications or untracked files confirmed), `false` (cleanliness confirmed via `git status --porcelain`), or `null` (cleanliness cannot be established; never falsely assumed clean).
- `per_case_results.jsonl`: Detailed per-case telemetry, latencies, channel counts, and metric eligibility.
- `retrieved_evidence.jsonl`: Raw observations for every retrieved candidate, including channel-specific ranks and scores.
- `pooled_evidence_review.csv`: Deduplicated review spreadsheet merging newly discovered pooled evidence with prior annotations.
- `summary.json`: High-level execution summary, latency percentiles, and channel overlap statistics.
- `summary.csv`: Tabular case-level summary of retrieval counts, latencies, and eligibility.
- `errors.jsonl`: Case errors and failure diagnostics (if any occurred).
- `README.md`: Run-specific documentation and limitations disclosure.

---

## 6. Execution Commands

### Run Full Baseline Evaluation (Official Gold Track, 50 Cases)
```bash
conda run -n med-env python evaluation/retrieval/run_retrieval_evaluation.py --mode baseline --top-k 5
```
*Note: With `gold_judgments.jsonl` at 0 bytes awaiting Phase A.2 human adjudication, the official track safely reports `not_evaluable_no_reviewed_gold_labels`.*

### Run AI-Assisted Evidence-Verified Evaluation (Research Track, All 50 Cases)
```bash
conda run -n med-env python evaluation/retrieval/run_retrieval_evaluation.py \
  --mode both \
  --top-k 5 \
  --evidence-judgments
```

### Run Controlled Evidence-Verified Smoke Evaluation (`MED-BENCH-001` & `MED-BENCH-036`)
```bash
conda run -n med-env python evaluation/retrieval/run_retrieval_evaluation.py \
  --mode both \
  --cases MED-BENCH-001 MED-BENCH-036 \
  --evidence-judgments
```

### Run Brand and Generic Lookup Categories in Both Channels
```bash
conda run -n med-env python evaluation/retrieval/run_retrieval_evaluation.py --mode both --categories drug_brand_lookup drug_generic_lookup --top-k 5
```

### Force-Disable Neo4j in Graph / Both Mode (Testing Fallback Resilience)
```bash
conda run -n med-env python evaluation/retrieval/run_retrieval_evaluation.py --mode both --disable-neo4j --top-k 5
```

---

## 7. Dual-Track Architecture & Validity Boundaries

The evaluation harness implements two strictly isolated evaluation tracks:

```text
                                  ┌──────────────────────────────────────────────┐
                                  │ run_retrieval_evaluation.py CLI Orchestrator │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                           ┌─────────────────────────────┴─────────────────────────────┐
                           ▼                                                           ▼
       [Default: Official Gold Track]                            [Explicit: --evidence-judgments]
┌──────────────────────────────────────────────┐        ┌──────────────────────────────────────────────┐
│ Input: evaluation/benchmark/                 │        │ Input: evaluation/benchmark/evidence_        │
│        gold_judgments.jsonl (0 bytes)        │        │        adjudication/phase_a_3/               │
│                                              │        │        evidence_verified_judgments.jsonl     │
│ Track ID: official_human_gold                │        │ Track ID: ai_assisted_evidence_verified      │
│ Required status: "human_reviewed"            │        │ Required provenance:                         │
│ Output: eval_<mode>_<timestamp>/             │        │   human_reviewed == False                    │
│ Metric status:                               │        │   adjudicator_type == "ai_assisted_..."      │
│   not_evaluable_no_reviewed_gold_labels      │        │ Output: eval_evidence_verified_<mode>_<time>/│
│                                              │        │ Mandatory Disclaimer:                        │
│ Quality claims: Blocked until clinical sign- │        │   "AI-Assisted Evidence-Verified Evaluation  │
│                 off in Phase A.2             │        │    — Not Human-Adjudicated Gold"             │
└──────────────────────────────────────────────┘        └──────────────────────────────────────────────┘
```

### Validity Boundary Principles
1. **Never Overwrite or Confuse:** AI-assisted research judgments are never written to `gold_judgments.jsonl`. Official gold file remains strictly 0 bytes.
2. **Strict Provenance Validation:** Research-track loader raises an error if `human_reviewed` is `True` or `adjudicator_type` is anything other than `ai_assisted_external_evidence`.
3. **No Synthetic Fallback:** A missing or invalid research dataset halts evaluation immediately; it will never silently fall back to official gold.
4. **Scoring on Verified Grades:** Only `evidence_based_grade` is used for relevance scoring. Preliminary grades that were downgraded during external evidence adjudication are strictly non-relevant.
5. **Negative Control Integrity:** Unanswerable negative controls are evaluated solely on rejection accuracy and false-positive counts; `"none"` is never counted as a retrieved candidate.

