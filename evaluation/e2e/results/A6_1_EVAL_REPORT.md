# MediScanAI Candidate Evaluation Report: A6.1 vs A6 (Baseline)

**Date:** 2026-10-24 14:37:17
**Candidate:** `A6.1` (Evidence format: `compact`, Prompt: `v5`, Routing: `v2`)
**Baseline:** `A6` (Evidence format: `compact`, Prompt: `v5`, Routing: `v2`)
**Dataset:** `dev_subset_40.json` (40 frozen development cases)
**Judge Model:** `llama3.1:8b` (temp=0, seed=42, num_ctx=12288, format=json)

## 1. Executive Summary

Candidate A6.1 introduces targeted negative-disclaimer sanitization and combination product-level indication attribution normalizations on top of A6.

| Metric | A6 (Baseline) | A6.1 (Candidate) | Delta |
|---|---:|---:|---:|
| **Mean Faithfulness** | **0.8021** | **0.7614** | **-0.0407** |
| **Median Faithfulness** | **1.0000** | **1.0000** | **+0.0000** |
| **Valid Scored Cases** | 40 / 40 | 39 / 40 | 0 |
| **Unsupported Statements** | 12 | 35 | +23 |
| **Paired Wins / Losses / Ties** | — | **4 Wins / 9 Losses / 26 Ties** | — |

## 2. Category-by-Category Performance

| Category | Count | A6 Mean | A6.1 Mean | Delta |
|---|---:|---:|---:|---:|
| `medicine_only_clean_ocr` | 6 | 1.0000 | 1.0000 | +0.0000 |
| `medicine_only_noisy_ocr` | 5 | 0.8000 | 0.8000 | +0.0000 |
| `symptom_only` | 8 | 0.8500 | 0.8021 | -0.0479 |
| `symptom_plus_medicine_match` | 8 | 0.8793 | 0.8849 | +0.0056 |
| `symptom_plus_medicine_mismatch` | 6 | 0.8889 | 0.7361 | -0.1528 |
| `unanswerable` | 7 | 0.4167 | 0.3810 | -0.0357 |

## 3. Targeted Fix Analysis

### Symptom-Only Cases
In symptom-only queries (`symptom_only`), unsupported negative disclaimers (e.g. `None identified in the available sources.`) previously written under `### Suggested Alternatives` are replaced with `Not applicable: no medicine provided.` or omitted deterministically, preventing the judge from extracting negative claims.

### Medicine & Product-Level Indication Attribution
In combination products and kits (`symptom_plus_medicine_match`), physical container phrasing is standardized to label evidence active ingredients, preserving sentence-boundary alignment and preventing cross-field indication contamination.

## 4. Unsupported Statements Detail

Total unsupported statements detected: **35**

| Case ID | Statement | Reason |
|---|---|---|
| `E2E-009` | Blindness is documented to have overlapping symptoms, which include Blindness and Neovascularization. | The context explicitly lists Blindness as a symptom of Blindness. It does not provide information about overlapping symptoms for this condition. |
| `E2E-009` | Proteinuria is documented to have overlapping symptoms, which include Nephritis and Nephrosis. | The context lists Proteinuria as a condition with several symptoms. However, it does not explicitly mention that these symptoms overlap with Nephritis and Nephrosis. |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is a medication that requires a prescription. | The context does not explicitly state that Strophanthus (STROPHANTHUS) 20mg requires a prescription. However, it is listed as Rx Only* in [E7] and Directions: FOR ORAL USE ONLY. in [E8] and [E9]. |
| `E2E-100` | The requested medication information about Glycozempra 5mg/mL solution could not be verified. | There is no mention of Glycozempra 5mg/mL solution in the provided context, so it cannot be deduced that the requested medication information was found or not. |
| `E2E-100` | The pediatric weight-based dosing for Glycozempra 5mg/mL solution was not found in the provided evidence. | There is no mention of Glycozempra 5mg/mL solution in the provided context, so it cannot be deduced that the pediatric weight-based dosing was found or not. |
| `E2E-080` | Albert Einstein was a German-born theoretical physicist. | The context and statement are unrelated |
| `E2E-080` | Albert Einstein is recognized as one of the greatest and most influential physicists of all time. | The context and statement are unrelated |
| `E2E-080` | Albert Einstein was best known for developing the theory of relativity. | The context and statement are unrelated |
| `E2E-080` | Albert Einstein also made important contributions to the development of the theory of quantum mechanics. | The context and statement are unrelated |
| `E2E-097` | The requested medication information about Novaproxin capsules for severe chronic osteoarthritis pain could not be verified. | There is no mention of Novaproxin in the context, but there is a mention of Meloxicam which is used to manage OA pain. However, it does not explicitly state that it's for severe chronic osteoarthritis pain. |
| `E2E-097` | The requested medication information about Novaproxin capsules for severe chronic osteoarthritis pain could not be verified. | There is no mention of Novaproxin in the context, but there is a mention of Meloxicam which is used to manage OA pain. However, it does not explicitly state that it's for severe chronic osteoarthritis pain. |
| `E2E-041` | The label text identifies Glibenclarnide. | There is no information given in the context about Glibenclarnide. The context only mentions Allopurinol and other medications, but not Glibenclarnide. |
| `E2E-041` | Glibenclarnide is also known as Glyburide. | The context contains a Drug Name Match with id=3489, which has the name glyburide. This implies that Glibenclarnide and Glyburide are related, but it does not explicitly state that they are the same medication. |
| `E2E-041` | Glibenclarnide contains active ingredients glyburide. | The context contains a Drug Name Match with id=3489, which has the name glyburide. This implies that Glibenclarnide and Glyburide are related, but it does not explicitly state that Glibenclarnide contains glyburide as an active ingredient. |
| `E2E-041` | Glibenclarnide is used to treat indications. | The context mentions Allopurinol, which has several indications listed. However, it does not explicitly state that Glibenclarnide is used to treat any of these indications. |
| `E2E-041` | This medication is not innocuous. | The context mentions Allopurinol, which has a warning stating 'This is not an innocuous drug.' This implies that the medication in question (Allopurinol) is not innocuous. However, it does not explicitly state that Glibenclarnide is not innocuous. |
| `E2E-041` | It is not recommended for the treatment of asymptomatic hyperuricemia. | The context mentions Allopurinol, which has a warning stating 'It is not recommended for the treatment of asymptomatic hyperuricemia.' This implies that Allopurinol should not be used to treat asymptomatic hyperuricemia. However, it does not explicitly state that Glibenclarnide should not be used to treat this condition. |
| `E2E-041` | Allopurinol tablets, USP reduces serum and urinary uric acid concentrations. | The context mentions Allopurinol, which has a description stating 'reduces serum and urinary uric acid concentrations.' This implies that Allopurinol has this effect. However, it does not explicitly state that Glibenclarnide reduces serum and urinary uric acid concentrations. |
| `E2E-041` | The use of this medication should be individualized for each patient. | The context mentions Allopurinol, which has a description stating 'Its use should be individualized for each patient.' This implies that the use of Allopurinol should be individualized. However, it does not explicitly state that Glibenclarnide's use should be individualized. |
| `E2E-041` | Understanding its mode of action is required. | The context mentions Allopurinol, which has a description stating 'Its mode of action and pharmacokinetics (see CLINICAL PHARMACOLOGY, CONTRAINDICATIONS, WARNINGS, and PRECAUTIONS) should be understood.' This implies that understanding the mode of action of Allopurinol is required. However, it does not explicitly state that understanding Glibenclarnide's mode of action is required. |
| ... | *and 15 more* | ... |

## 5. Resource Usage Summary

- **Generator Provider / Model:** `ollama/llama3.1:8b`
- **Total Generator Tokens:** 58,972 (55,383 input / 3,589 output)
- **Average Generator Tokens / Case:** 1474.3 (1384.6 prompt / 89.7 completion)
- **Generator Latency:** Avg 17600.1ms, Median 17460.5ms
- **Judge Provider / Model:** `ollama/llama3.1:8b`
- **Judge Tokens (Live Calls):** 61,889 (47,616 input / 14,273 output)
- **Judge Calls:** 46 live calls across 40 cases
- **Estimated Cloud Cost:** $0.00 (local inference; zero paid API calls)

