# Steps 1-5 Findings: contract audit, dev trace, deterministic retrieval matrix

Branch `exp/ragas-opt` (from `eval/phase01` @ `5e5a10a`). Step 4 commit `1467cdc`. No LLM calls in this document.
All judge numbers elsewhere remain SELF-JUDGED (llama3.1:8b). Tests: 194 passed (187 existing + 7 new).

## A. Corrections to the earlier diagnosis
- I wrote that symptom_only cases have no reference ids and that hit@k "cannot be computed". Wrong:
  symptom_only cases carry a `disease_chunk_N` reference. My earlier 0/8 "reference hit" was an artifact of an
  **id-scheme mismatch**: `app/evidence.py::extract_item_id` labels disease blocks with the 0-based JSONL `id`
  (`disease_chunk_2111`), while the dataset reference and `core.extract_retrieved_ids_per_channel` use the 1-based
  `chunk.id` (`disease_chunk_2112`). Evidence block ids for diseases are therefore off by one relative to the corpus
  chunk id (seen in E2E-035). This is a real traceability bug in the compact (opt-in) path. Not fixed yet (Step 6 proposal).
- Estimator vs reality: E2E-035 prompt = 1131 tokens (tiktoken) vs 1459 `prompt_eval_count` from Ollama (+29%, chat template
  and tokenizer difference). tiktoken numbers are diagnostics only.

## B. Dataset contract audit
Sources: `build_dataset.py`, `dataset/README.md`, `dataset_stats.json`, `tests/unit/test_dataset_builder.py`, `backend/main.py`.

| Category | user_text (as built) | ocr_text | reference / ids | expected |
|---|---|---|---|---|
| symptom_only | template + first 4 entries of the disease's `symptoms` list (list includes the disease name itself) | empty | "X lists symptoms: ..." ; `disease_chunk_N` | answer |
| medicine_only_clean/noisy | generic question about "this medicine/label" (3-4 fixed templates); no symptoms | label text (clean / noisy synthetic) | "Brand (generic) contains ...; label lists ..." ; `drug_N` + equivalent_ids | answer |
| match | "I am experiencing symptoms of <5 symptoms>... is it appropriate?" | label text, "Indications: See package insert" | disease chunk + drug | answer |
| mismatch | "I have <4 symptoms>. Can I take this medicine?" | label text (some are cosmetics, e.g. E2E-076) | disease chunk + drug; `heuristic=true` | answer (reference says "do not correspond") |
| unanswerable | a question (drug dosage/approval, cure claims); not symptoms | fictitious/real label or empty | no ids | abstain |

Findings:
1. `user_text` is **always a natural-language question**, never empty; its meaning varies by category (symptom narrative,
   question about the label, or an unanswerable factual question). The README defines it only as "Real-world patient query".
2. In production (`backend/main.py:350`) `user_text` = `combined_symptoms` (text field + transcribed voice), and an image-only
   request has **empty** `user_text`. So the dataset's medicine-only convention (non-empty generic question) does not occur
   in the production form for image-only use. Whether a user can also type a question about the label is not documented.
3. Neither convention is proven "wrong". But `determine_case_type` treats "non-empty user_text" as "user described symptoms",
   which is false for 11/11 medicine-only and 6/7 unanswerable dev cases (and 1/7 unanswerable is routed SYMPTOM_ONLY for a
   non-symptom question, e.g. "chocolate syrup for appendicitis").
4. Retrieval has the same problem: the generic question is used as the **disease/drug query** (`user_norm`), producing disease
   and drug blocks that match the wording of the question, not the label. This is why disease blocks are 27% of shown
   evidence even for medicine-only cases.
5. Documentation inconsistencies: README says "110 cases" and "Total 120"; its table sums to 110 (100 RAGAS + 10 emergency).
   README says mismatches have "0 token overlap", but the builder only tests words >= 4 letters. The symptom lists contain
   the disease name as a "symptom" (source of DISEASE_NAME_AS_SYMPTOM statements).

### Routing trace (current `determine_case_type`, real inputs)
| Case | Category | user_text | ocr_text | -> case_type / task |
|---|---|---|---|---|
| E2E-001 | symptom_only | "I am experiencing Coronary Atherosclerosis, Chest pain..." | "" | SYMPTOM_ONLY / symptom task |
| E2E-035 | medicine_only_clean | "Please provide the therapeutic indications, active ingredients, and important warnings..." | "Deriphyllin (Etofylline/Theophylline) 20mg" | **SYMPTOM_AND_MEDICINE** / "uses that match your symptoms" |
| E2E-041 | medicine_only_noisy | "I scanned my pill container label..." | "Da0nil 50mg Capsules..." | **SYMPTOM_AND_MEDICINE** |
| E2E-056 | match | "I am experiencing symptoms of Vaginitis..." | "ESTRADIOL VAGINAL INSERTS..." | SYMPTOM_AND_MEDICINE (correct) |
| E2E-076 | mismatch | "I have Toxoplasmosis..." | "Chantecaille ... Sunscreen" | SYMPTOM_AND_MEDICINE (correct) |
| E2E-091 | unanswerable | "What is the recommended dosage ... NonexistentDrugZ" | "NonexistentDrugZ 500mg" | **SYMPTOM_AND_MEDICINE** |
| E2E-095 | unanswerable | "...chocolate syrup for treating acute appendicitis?" | "" | **SYMPTOM_ONLY** |

### Contract-consistent recommendation (not implemented; Step 6 proposal)
- Do **not** edit `e2e_v1.jsonl`. Future dataset `e2e_v2` (versioned, additive) should add an explicit `task` field
  (`symptom | medicine_label | symptom_vs_label | unanswerable_probe`) used for analysis and as test labels only.
- Production routing must not depend on dataset metadata. Add an opt-in deterministic intent classifier
  (`ROUTING_VERSION=v2`) on (`user_text`, `ocr_text`): a query is *symptom-bearing* only if it contains a first-person
  symptom statement; generic label-questions ("this medicine/label/pill", asks for indications/warnings/dosage) are
  *medicine-directed*. Evaluate the classifier against the dataset categories as a labelled test set (accuracy per class)
  before using it, and keep the legacy rule as default. Medicine-directed queries should also skip disease retrieval keyed on
  the question text. Both are measurable without the judge.

## C. Step 4: dev trace (done, opt-in)
`DEV_TRACE_ENABLED` (default false), `DEV_TRACE_INCLUDE_TEXT` (default false: only sha256 prefix and char counts),
`DEV_TRACE_DIR`. Adds `result["dev_trace"]` containing effective settings, token budget (system / user / evidence by channel,
Ollama `prompt_eval_count`, actual headroom), per-stage retrieval lists (dense / BM25 / fused / reranked with scores and
timings), final evidence, and a reason for each retrieved-but-not-shown id (`merged_duplicate_into`, `token_budget_drop`,
`per_channel_cap`). `MultiRetriever.search_specific` gained keyword-only `candidate_pool_size`, `rerank_depth`, `debug`
(defaults reproduce the old behavior). Observation: the compact budget (`num_ctx - num_predict - 756 = 6736` tokens) never
binds (evidence is ~870 tokens); the real limiter is the 3-items-per-channel cap.

## D. Step 5: deterministic retrieval matrix (`exp01_retrieval_matrix/`)
Zero LLM calls. 40 frozen dev cases; 25 have a reference drug, 22 have a reference disease chunk (one case = 4.0 / 4.5
percentage points). Replay vs real `search_specific`: **283/284 identical; 1 mismatch** (E2E-072, drugs_from_ocr, P60/R30), most
likely an RRF/L2 tie ordering difference; not investigated further. Metrics are ID-based, not RAGAS context precision/recall.
"Shown" = after production dedup + per-channel cap. Equivalent-drug ids count as hits; strict rates are in `summary.json`.

Baseline (P15, R15, top_k 5, cap 3) and retrieval modes:

| Mode | drug hit shown | drug MRR (OCR ch.) | disease hit | ID recall shown | evidence tok mean / p95 | duplicate rate |
|---|---|---|---|---|---|---|
| dense only | 0.72 | 0.607 | 0.727 | 0.697 | 803 / 1221 | 0.32 |
| BM25 only | 0.80 | 0.723 | 0.864 | 0.833 | 815 / 1196 | 0.35 |
| RRF only | 0.84 | 0.755 | 0.909 (shown 0.773) | 0.803 | 837 / 1196 | 0.27 |
| **RRF + rerank (production)** | **0.80** | **0.757** | **0.909** | **0.849** | **870 / 1334** | 0.37 |

Selected grid rows (rerank mode, cap = top_k; full table in `summary.json`):

| P | R | top_k | drug hit shown | drug MRR | disease hit | ID recall | tokens mean | latency (10-case sample, 4 queries/case) |
|---|---|---|---|---|---|---|---|---|
| 15 | 15 | 5 (cap 3) baseline | 0.80 | 0.757 | 0.909 | 0.849 | 870 | 1.26 s |
| 15 | 15 | 2 | 0.72 | 0.720 | 0.909 | 0.803 | 612 | 1.26 s |
| 30 | 15 | 5 | 0.88 | 0.765 | 1.000 | 0.909 | 1185 | 1.26 s |
| 30 | 15 | 8 | 0.88 | 0.765 | 1.000 | 0.909 | 1765 | 1.26 s |
| 60 | 30 | 5 | 0.80 | 0.743 | 1.000 | 0.879 | 1261 | 2.75 s |
| 60 | 60 | 5 | 0.88 | 0.797 | 1.000 | 0.924 | 1311 | 5.21 s |

Latency (retrieval stage only, warm, mean of 10 cases): R=15 1.26 s, R=30 2.5-2.7 s, R=60 5.2 s; candidate pool P has no
measurable effect (the cross-encoder on R candidates dominates, roughly 20 ms per candidate-query).

What the data supports (and its limits):
- Retrieval is **not the main bottleneck**: the reference drug is already shown for 20/25 cases (0.80). Even the deepest
  setting (P60/R60/top_k 8) only reaches 0.88 (22/25); E2E-034 and E2E-042 are never found. Gains between settings are 1-3 cases and
  within noise for n=25/22.
- Reranking helps vs dense-only (+0.08 drug, +0.18 disease) and is on par with BM25 for drugs; RRF alone is not worse for drugs.
- A larger candidate pool at the **same rerank depth** (P30/R15) is free in latency and raised disease hit 0.909 -> 1.0
  (fixes E2E-065, E2E-082) and drug hit shown 0.80 -> 0.88 (fixes E2E-072, E2E-082). But P60/R15 does not (0.80), so this is not
  a monotone effect; selecting it from 40 cases risks overfitting and needs held-out confirmation.
- Increasing evidence count raises tokens (870 -> 1185 at cap 5 -> 1765 at cap 8) with no recall gain beyond cap 5.
  Top 2 loses 0.08 drug hit. Disease-block share stays 33-39% at every setting: top-k cannot remove it.
- Remaining misses are in noisy OCR (E2E-041, E2E-042; drug hit 0.60 for noisy vs 0.83 clean) and E2E-034 (clean).
- Evidence granularity (smaller passages) was **not** testable here: indexes store whole records and re-indexing is out of
  scope. Only formatter field caps could change it.
- Not measured: RAGAS context precision/recall, response relevancy, faithfulness (judge deliberately not run).

## E. Recommended smallest set of Step 6 opt-in changes (all default-off, each with a regression test)
1. `ROUTING_VERSION=v2`: deterministic intent classifier for case type (and medicine-directed queries skip disease retrieval on
   the question text). Verify classifier accuracy on dataset categories first.
2. Fix the disease evidence id (0-based vs 1-based) in `extract_item_id` under the compact path so tags map to corpus ids.
3. Evidence selection: for medicine-directed or label-bearing requests, drop or demote DISEASE blocks whose symptoms do not
   overlap the user's words; keep drug identity and Indications fields prominent (no new facts).
4. Optionally `candidate_pool_size=30, rerank_depth=15` (latency-neutral), only if confirmed on a held-out set. Keep top_k 5 / cap 3.
Items 1-3 address the diagnosed bottlenecks; item 4 is a small, uncertain retrieval gain. Judge-score only after 1-3 are built,
on the same 40 cases plus a separate held-out set, comparing to the saved A2 numbers.

## Reproduce
```
conda run -n med-env python evaluation/e2e/run_retrieval_matrix.py   # ~8 min, no LLM
conda run -n med-env pytest tests/unit tests/api tests/database tests/test_e2e_smoke.py -q   # 194 passed
```
