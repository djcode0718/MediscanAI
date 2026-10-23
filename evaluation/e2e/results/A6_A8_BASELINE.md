# MediScanAI — A6–A8 Optimization Program Baseline Document (A5 Reference)

**Date:** 2026-10-23  
**Branch:** `exp/ragas-opt`  
**Baseline Commit:** `ca0f8dc` (HEAD)  
**Evaluator:** `SELF-JUDGED (llama3.1:8b)` via Ollama, TraceableFaithfulness (`num_ctx=12288`, `format="json"`, `temp=0.0`, `seed=42`)  
**Generator:** `llama3.1:8b` via Ollama (`num_ctx=8192`, `num_predict=700`, `temp=0.0`, `seed=42`)  

---

## 1. Verified Dataset Identity

- **Development Benchmark:** `evaluation/e2e/dataset/dev_subset_40.json` (40 frozen cases)
  - **SHA256:** `0fe04836c87168ee57447a9ebc2948af9ff033869f0a7eb23a2534a47590e04d`
- **Master Evaluation Pool:** `evaluation/e2e/dataset/e2e_v1.jsonl` (110 total cases)
  - **SHA256:** `f0de53c33cb587cd900582148337504b59ee40d8be2cd88608cab18a10916415`
  - **Held-Out Candidates Available:** 70 cases outside `dev_subset_40.json` (10 emergency, 17 symptom_only, 12 match, 10 noisy OCR, 9 clean OCR, 9 mismatch, 3 unanswerable)

---

## 2. A5 Configuration Parameters

- `EVIDENCE_FORMAT="compact"`
  - `EVIDENCE_MAX_ITEMS_PER_CHANNEL=3`
  - `EVIDENCE_FIELD_CAPS={'indications': 700, 'warnings': 300, 'dosage': 300, 'adverse_reactions': 300, 'symptoms': 12}`
  - Formulation parser (`parse_multi_ingredient_formulations`) prioritizing matching active ingredient / purpose
  - Strong brand filtering (`drugs_from_ocr` retains retrieved records matching brand name in `ocr_text`)
  - Bounded ingredient list caps
- `PROMPT_VERSION="v4"`
  - Scanned medicine anchoring via `LABEL_TEXT`
  - Explicit formulation-level attribution (`<Brand> contains <Ingredient>, labeled for <use>. [E#]`)
  - Clean bounded negative abstention protocol
  - Template meta-token leak sanitization
- `ROUTING_VERSION="v2"`
  - Deterministic 4-way intent classification: `SYMPTOM_ONLY`, `MEDICINE_ONLY`, `SYMPTOM_AND_MEDICINE`, `UNANSWERABLE`
  - Disease index bypass for medicine-directed queries and probes

---

## 3. Measured A5 Baseline Metrics

| Metric | A2 Baseline | A4 Candidate | **A5 Candidate (Current Baseline)** | A5 vs A2 Delta | A5 vs A4 Delta |
|---|---:|---:|---:|---:|---:|
| **Mean Faithfulness** | 0.5282 | 0.7256 | **0.7538** | **+0.2256** | **+0.0282** |
| **Median Faithfulness** | 0.5000 | 0.8167 | **0.8000** | **+0.3000** | -0.0167 |
| **Valid Cases (non-NaN)** | 39/40 | 40/40 | **40/40** | +1 | +0 |
| **Unsupported Statements** | 87 | 52 | **40** | **-47 (-54.0%)** | **-12 (-23.1%)** |
| **Average Evidence Tokens** | ~2,400 | 775.1 | **647.2** | -73.0% | -127.9 (-16.5%) |
| **Average Prompt Tokens** | ~3,100 | 1024.1 | **946.1** | -69.5% | -78.0 (-7.6%) |
| **Invalid Citation Tags** | 0 | 0 | **0 (100% valid)** | +0 | +0 |
| **Head-to-head Paired Record** | — | 26W / 10L / 3T | **27W / 9L / 3T** | $p = 0.00024$ | 12W / 8L / 20T |

### Category Breakdown

| Category | Cases | A2 Mean | A4 Mean | A5 Mean | Delta (vs A4) |
|---|---:|---:|---:|---:|---:|
| `medicine_only_clean_ocr` | 6 | 0.9000 | 0.9583 | **0.9667** | +0.0084 |
| `medicine_only_noisy_ocr` | 5 | 0.5800 | 0.8000 | **0.9333** | +0.1333 |
| `symptom_plus_medicine_match` | 8 | 0.4354 | 0.7688 | **0.8604** | +0.0916 |
| `symptom_plus_medicine_mismatch` | 6 | 0.3889 | 0.6648 | **0.8056** | +0.1408 |
| `symptom_only` | 8 | 0.5979 | 0.7250 | **0.6628** | -0.0622 |
| `unanswerable` | 7 | 0.3214 | 0.4762 | **0.3809** | -0.0953 |

---

## 4. Top Residual Failure Cases in A5

Of the 40 unsupported statements remaining in A5, the primary clusters are:

1. **`E2E-001` (Symptom-only): 5 unsupported statements.**
   - Generates expansive narrative on related dermatologic symptoms (flaking, redness, scales) not verbatim in disease chunk.
2. **`E2E-091` (Unanswerable): 3 unsupported statements.**
   - Negative abstention on fictitious entity `NonexistentDrugZ 500mg`. Judge penalizes statement because entity name is absent from context.
3. **`E2E-080` (Mismatch): 3 unsupported statements.**
   - Explicit negative enumeration of unindicated symptoms ("does not treat depression, headache, irritability").
4. **`E2E-041` (Noisy OCR): 3 unsupported statements.**
   - Corrupted brand string `Glibenclarnide` echoed in claim; judge flags entity absence.
5. **`E2E-024` (Symptom-only): 3 unsupported statements.**
   - Overgeneralized symptom association claims for cerebral palsy.
6. **`E2E-062` (Multi-ingredient kit): 2 unsupported statements.**
   - Down from 10 unsupported in A4 to 2 in A5; remaining 2 stem from attributing kit name to single formulation purpose.
7. **`E2E-100`, `E2E-094`, `E2E-097`, `E2E-099` (Unanswerable): 2 unsupported statements each.**
   - Fictitious probe entity echoes in negative sentences.

---

## 5. Test Suite Baseline Status

- Full Fast Suite (`./run_tests.sh`): **203/203 passed (0 failures) in 385.37s**.
- Unit test modules: 100% green across all existing regression suites.

---

## 6. Immutable Artifact Locations

- Baseline Scored Results: `evaluation/e2e/results/A5/scored_results.jsonl`
- Baseline Generated Cases: `evaluation/e2e/results/A5/generated_cases.jsonl`
- Baseline Unsupported Statements: `evaluation/e2e/results/A5/unsupported_statements.jsonl`
- Baseline Comparison Report: `evaluation/e2e/results/A5_EVAL_REPORT.md`
- Judge Cache: `evaluation/e2e/results/judge_cache.json`
