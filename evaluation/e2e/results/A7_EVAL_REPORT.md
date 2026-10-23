# MediScanAI A7 Evaluation Report (vs A6)

**Date:** 2026-10-23 19:40:34
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`
**Dataset:** `dev_subset_40.json` (40 frozen development cases)

## 1. Overall Faithfulness Summary

| Metric | A6 Baseline | A7 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.8021** | **0.6088** | **-0.1933** |
| Median Faithfulness | 1.0000 | 0.7500 | -0.2500 |
| Valid Cases (non-NaN) | 40/40 | 40/40 | +0 |
| NaN Count | 0 | 0 | +0 |
| Paired Mean Delta | - | - | -0.1933 |
| Wins / Losses / Ties | - | - | 3 wins / 21 losses / 16 ties |

## 2. Category-Level Faithfulness Breakdown

| Category | N | A6 Mean | A7 Mean | Delta | Valid |
|---|---|---|---|---|---|
| `medicine_only_clean_ocr` | 6 | 1.0000 | 0.7639 | -0.2361 | 6/6 |
| `medicine_only_noisy_ocr` | 5 | 0.8000 | 0.5100 | -0.2900 | 5/5 |
| `symptom_only` | 8 | 0.8500 | 0.7326 | -0.1174 | 8/8 |
| `symptom_plus_medicine_match` | 8 | 0.8793 | 0.7552 | -0.1241 | 8/8 |
| `symptom_plus_medicine_mismatch` | 6 | 0.8889 | 0.6361 | -0.2528 | 6/6 |
| `unanswerable` | 7 | 0.4167 | 0.2143 | -0.2024 | 7/7 |

## 3. Cheap Diagnostics and Resource Metrics

| Metric | A6 | A7 | Change |
|---|---|---|---|
| Avg Latency (ms) | 23881.5 | 19277.3 | -4604.2 |
| Avg Prompt Tokens | 946.8 | 978.8 | +32.0 |
| Avg Evidence Tokens | 647.2 | 642.4 | -4.8 |
| Avg Eval Tokens | 92.0 | 85.8 | -6.2 |
| Truncated Generations | 0 | 0 | +0 |
| Abstained Generations | 0 | 8 | +8 |
| Invalid Citation Tags | 0 | 0 | +0 |
| Total Citation Tags | 44 | 41 | -3 |

### Routing Distribution
- **A6:** `{'MEDICINE_ONLY': 11, 'SYMPTOM_ONLY': 8, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`
- **A7:** `{'SYMPTOM_ONLY': 8, 'MEDICINE_ONLY': 11, 'SYMPTOM_AND_MEDICINE': 14, 'UNANSWERABLE': 7}`

## 4. Unsupported Statements Analysis (70 statements)

Found 70 unsupported statements flagged by judge in A7 (vs 34 in A6).

| Case ID | Statement | Reason | Fuzzy Overlap |
|---|---|---|---|
| `E2E-042` | Labeled indications are not stated in the available sources. | The context explicitly mentions that labeled indications are mentioned for [E3] DRUG | id=36354 | Brand: Ursodiol | Generic: URSODIOL, which contradicts the statement. | 0.43 |
| `E2E-069` | The symptoms of bacteremia, abdominal tenderness, chill, decreased translucency, and diarrhea are consistent with a condition that can be treated with Penicillin V Potassium. | Bacteremia is mentioned as a condition in the context, but it does not explicitly state that these symptoms are consistent with a condition that can be treated with Penicillin V Potassium. Therefore, this statement cannot be directly inferred from the context. | 0.33 |
| `E2E-088` | The available sources do not state that this product treats cough. | There is no information in the context about the product treating cough. The context only mentions symptoms treated by other products. | 0.29 |
| `E2E-088` | The available sources do not state that this product treats fatigue. | Similar to the previous statement, there is no information in the context about the product treating fatigue. | 0.28 |
| `E2E-088` | The available sources do not state that this product treats feeling cold. | Again, there is no information in the context about the product treating feeling cold. | 0.28 |
| `E2E-093` | Clinical information about taking Lipitor to cure acute viral Covid-19 infection could not be verified. | The context mentions the indications for Lipitor, which include myocardial infarction, stroke, and angina in adults with multiple risk factors for coronary heart disease. However, it does not mention anything about treating acute viral Covid-19 infection. Therefore, it cannot be deduced that clinical information about taking Lipitor to cure acute viral Covid-19 infection could not be verified. | 0.37 |
| `E2E-032` | The labeled indications for this medicine are not stated. | The context provides information about the indications for several medicines, but it does not explicitly state that the indications for Hospicare 40R Adult Body Wipes are not stated. In fact, there is no mention of the indications for this specific medicine in the provided text. | 0.30 |
| `E2E-032` | The precautions for this medicine are not stated. | Similar to the previous statement, the context does provide information about the precautions for several medicines, but it does not explicitly state that the precautions for Hospicare 40R Adult Body Wipes are not stated. In fact, there is no mention of the precautions for this specific medicine in the provided text. | 0.29 |
| `E2E-044` | The indications of this medicine are not stated in the available sources. | The context does mention the indications for several medicines, but it does not explicitly state that the indications for Laura Mercier Flawless Skin Repair Day Creme Broad Spectrum SPF 15 Sunscreen are not stated. Therefore, we cannot directly infer this statement from the given context. | 0.33 |
| `E2E-009` | Neovascularization Proteinuria is a condition that has overlapping symptoms. | The context lists Neovascularization and Proteinuria as separate conditions, but does not explicitly state that they have overlapping symptoms. Therefore, it cannot be directly inferred. | 0.42 |
| `E2E-009` | Nephritis is a condition that has overlapping symptoms. | Nephritis is listed as a symptom of several conditions in the context, but not explicitly stated to have overlapping symptoms. Therefore, it cannot be directly inferred. | 0.42 |
| `E2E-009` | Nephrosis is a condition that has overlapping symptoms. | Nephrosis is listed as a symptom of several conditions in the context, but not explicitly stated to have overlapping symptoms. Therefore, it cannot be directly inferred. | 0.42 |
| `E2E-009` | No alternative medical illness was identified in the available sources. | The context lists multiple diseases and their symptoms, indicating that there are indeed conditions being discussed. However, it does not explicitly state that no alternative medical illnesses were found. Therefore, it cannot be directly inferred. | 0.35 |
| `E2E-073` | The scanned medicine contains meclizine hydrochloride as its active ingredient. | The context does not provide information about the active ingredients of the scanned medicine, so it cannot be inferred that meclizine hydrochloride is present. | 0.39 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is labeled for relieving intestinal gas. | The context mentions that Strophanthus hispidus and its derivatives are indicated for various purposes, but it does not explicitly mention relieving intestinal gas as one of them. | 0.38 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is labeled for relieving abdominal pain. | The context mentions that Strophanthus hispidus and its derivatives are indicated for various purposes, but it does not explicitly mention relieving abdominal pain as one of them. However, the medicine Kids Relief contains ingredients traditionally used to help relieve symptoms associated with colic, including abdominal pain. | 0.43 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is labeled for relieving bloating. | The context mentions that Strophanthus hispidus and its derivatives are indicated for various purposes, but it does not explicitly mention relieving bloating as one of them. However, the medicine Kids Relief contains ingredients traditionally used to help relieve symptoms associated with colic, including bloating. | 0.38 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is labeled for relieving nausea. | The context mentions that Strophanthus hispidus and its derivatives are indicated for various purposes, but it does not explicitly mention relieving nausea as one of them. However, the medicine Kids Relief contains ingredients traditionally used to help relieve symptoms associated with colic, including nausea. | 0.39 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is labeled for relieving burping. | The context mentions that Strophanthus hispidus and its derivatives are indicated for various purposes, but it does not explicitly mention relieving burping as one of them. However, the medicine Kids Relief contains ingredients traditionally used to help relieve symptoms associated with colic, including burping. | 0.38 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg contains CITRULLUS COLOCYNTHIS FRUIT PULP as an active ingredient. | The context mentions that the medicine Kids Relief contains CITRULLUS COLOCYNTHIS FRUIT PULP, but it does not explicitly mention Strophanthus (STROPHANTHUS) 20mg containing this ingredient. | 0.42 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg contains DIOSCOREA VILLOSA TUBER as an active ingredient. | The context mentions that the medicine Kids Relief contains DIOSCOREA VILLOSA TUBER, but it does not explicitly mention Strophanthus (STROPHANTHUS) 20mg containing this ingredient. | 0.42 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg contains MAGNESIUM PHOSPHATE, DIBASIC TRIHYDRATE as an active ingredient. | The context mentions that the medicine Kids Relief contains MAGNESIUM PHOSPHATE, DIBASIC TRIHYDRATE, but it does not explicitly mention Strophanthus (STROPHANTHUS) 20mg containing this ingredient. | 0.49 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg contains MATRICARIA CHAMOMILLA as an active ingredient. | The context mentions that the medicine Kids Relief contains MATRICARIA CHAMOMILLA, but it does not explicitly mention Strophanthus (STROPHANTHUS) 20mg containing this ingredient. | 0.41 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is indicated for relieving symptoms associated with colic, including intestinal gas. | The context mentions that the medicine Kids Relief contains ingredients traditionally used to help relieve symptoms associated with colic, including intestinal gas. However, it does not explicitly mention Strophanthus (STROPHANTHUS) 20mg being indicated for this purpose. | 0.34 |
| `E2E-082` | Strophanthus (STROPHANTHUS) 20mg is indicated for relieving symptoms associated with colic, including abdominal pain. | The context mentions that the medicine Kids Relief contains ingredients traditionally used to help relieve symptoms associated with colic, including abdominal pain. However, it does not explicitly mention Strophanthus (STROPHANTHUS) 20mg being indicated for this purpose. | 0.34 |
