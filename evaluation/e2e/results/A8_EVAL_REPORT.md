# MediScanAI A8 Evaluation Report (vs A5)

**Date:** 2026-10-23 20:30:26
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`
**Dataset:** `dev_subset_40.json` (40 frozen development cases)

## 1. Overall Faithfulness Summary

| Metric | A5 Baseline | A8 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.7538** | **0.7096** | **-0.0442** |
| Median Faithfulness | 0.8000 | 0.9091 | +0.1091 |
| Valid Cases (non-NaN) | 40/40 | 39/40 | -1 |
| NaN Count | 0 | 1 | +1 |
| Paired Mean Delta | - | - | -0.0550 |
| Wins / Losses / Ties | - | - | 7 wins / 13 losses / 19 ties |

## 2. Category-Level Faithfulness Breakdown

| Category | N | A5 Mean | A8 Mean | Delta | Valid |
|---|---|---|---|---|---|
| `medicine_only_clean_ocr` | 6 | 0.9667 | 1.0000 | +0.0333 | 6/6 |
| `medicine_only_noisy_ocr` | 5 | 0.9333 | 0.8667 | -0.0666 | 5/5 |
| `symptom_only` | 8 | 0.6628 | 0.7326 | +0.0698 | 8/8 |
| `symptom_plus_medicine_match` | 8 | 0.8604 | 0.8799 | +0.0195 | 7/8 |
| `symptom_plus_medicine_mismatch` | 6 | 0.8056 | 0.6365 | -0.1691 | 6/6 |
| `unanswerable` | 7 | 0.3809 | 0.2143 | -0.1666 | 7/7 |

## 3. Cheap Diagnostics and Resource Metrics

| Metric | A5 | A8 | Change |
|---|---|---|---|
| Avg Latency (ms) | 24339.1 | 22863.7 | -1475.4 |
| Avg Prompt Tokens | 946.1 | 933.9 | -12.2 |
| Avg Evidence Tokens | 647.2 | 642.4 | -4.8 |
| Avg Eval Tokens | 102.8 | 96.4 | -6.4 |
| Truncated Generations | 0 | 0 | +0 |
| Abstained Generations | 3 | 1 | -2 |
| Invalid Citation Tags | 0 | 0 | +0 |
| Total Citation Tags | 54 | 41 | -13 |

### Routing Distribution
- **A5:** `{'MEDICINE_ONLY': 11, 'SYMPTOM_ONLY': 8, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`
- **A8:** `{'SYMPTOM_ONLY': 8, 'MEDICINE_ONLY': 11, 'SYMPTOM_AND_MEDICINE': 14, 'UNANSWERABLE': 7}`

## 4. Unsupported Statements Analysis (49 statements)

Found 49 unsupported statements flagged by judge in A8 (vs 40 in A5).

| Case ID | Statement | Reason | Fuzzy Overlap |
|---|---|---|---|
| `E2E-093` | Clinical information about taking Lipitor to cure acute viral Covid-19 infection could not be verified. | The context mentions the indications for Lipitor, which include myocardial infarction, stroke, and angina in adults with multiple risk factors for coronary heart disease. However, it does not mention anything about treating acute viral Covid-19 infection. Therefore, it cannot be deduced that clinical information about taking Lipitor to cure acute viral Covid-19 infection could not be verified. | 0.37 |
| `E2E-009` | Neovascularization Proteinuria is a condition that has overlapping symptoms. | The context lists Neovascularization and Proteinuria as separate conditions, but does not explicitly state that they have overlapping symptoms. Therefore, it cannot be directly inferred. | 0.42 |
| `E2E-009` | Nephritis is a condition that has overlapping symptoms. | Nephritis is listed as a symptom of several conditions in the context, but not explicitly stated to have overlapping symptoms. Therefore, it cannot be directly inferred. | 0.42 |
| `E2E-009` | Nephrosis is a condition that has overlapping symptoms. | Nephrosis is listed as a symptom of several conditions in the context, but not explicitly stated to have overlapping symptoms. Therefore, it cannot be directly inferred. | 0.42 |
| `E2E-009` | No alternative medical illness was identified in the available sources. | The context lists multiple diseases and their symptoms, indicating that there are indeed conditions being discussed. However, it does not explicitly state that no alternative medical illnesses were found. Therefore, it cannot be directly inferred. | 0.35 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg is labeled for relieving abdominal pain. | There is no information given in the context about the specific indications of the medicine Strophanthus (STROPHANTHUS) 20mg, but it does mention that one of its indications is "Rx Only*", which suggests it may be used to relieve various symptoms. However, there is no explicit mention of abdominal pain. | 0.41 |
| `E2E-100` | The pediatric weight-based dosing for Glycozempra 5mg/mL solution could not be verified. | There is no information given in the context about Glycozempra 5mg/mL solution, let alone its pediatric weight-based dosing. | 0.32 |
| `E2E-100` | The available clinical sources do not provide the specific information about the pediatric weight-based dosing for Glycozempra 5mg/mL solution. | There is no information given in the context about Glycozempra 5mg/mL solution, let alone its pediatric weight-based dosing. The statement is a paraphrase of the first statement, but it's still not directly inferable from the context. | 0.28 |
| `E2E-024` | No alternative medical illness was identified in the available sources. | The context does not provide information about identifying or ruling out alternative medical illnesses. Therefore, it cannot be directly inferred that no alternative medical illness was identified. | 0.35 |
| `E2E-062` | The medicine Strophanthus (STROPHANTHUS) 20mg is labeled for relieving abdominal pain. | There is no information given in the context about the specific indications of the medicine Strophanthus (STROPHANTHUS) 20mg, but it does mention that one of its indications is "Rx Only*", which suggests it may be used to relieve various symptoms. However, there is no explicit mention of abdominal pain. | 0.35 |
| `E2E-076` | This medicine contains titanium dioxide as its active ingredient, which prevents sunburn and reduces the risk of skin cancer and early skin aging caused by the sun. | The context states that the product is a sunscreen with titanium dioxide as its active ingredient, but it does not explicitly state that titanium dioxide prevents sunburn and reduces the risk of skin cancer and early skin aging caused by the sun. This statement cannot be directly inferred from the context. | 0.58 |
| `E2E-091` | The requested clinical information about NonexistentDrugZ 500mg tablets could not be verified. | There is no mention of NonexistentDrugZ in the context, so it cannot be inferred that the clinical information for this drug could not be verified. | 0.45 |
| `E2E-091` | Available clinical sources do not state the specific dosage for NonexistentDrugZ 500mg tablets. | The context mentions the indications and dosages for Alprazolam Extended Release (1775) and Ursodiol (5508, 36354), but there is no information about NonexistentDrugZ. Therefore, it cannot be inferred that available clinical sources do not state the specific dosage for this drug. | 0.45 |
| `E2E-091` | Available clinical sources do not state the specific administration schedule for NonexistentDrugZ 500mg tablets. | The context mentions the administration instructions for Alprazolam Extended Release (1775), but there is no information about NonexistentDrugZ. Therefore, it cannot be inferred that available clinical sources do not state the specific administration schedule for this drug. | 0.40 |
| `E2E-025` | A disease that matches all described symptoms could not be verified from available sources. | Although multiple diseases are mentioned, none of them match all the described symptoms. The context does not provide a clear indication of a single disease matching all symptoms. | 0.36 |
| `E2E-025` | No alternative diseases were identified in the available sources. | The context mentions multiple diseases but does not explicitly state that no other diseases match the described symptoms. Therefore, it cannot be directly inferred that no alternative diseases exist. | 0.40 |
| `E2E-097` | The requested clinical information about Novaproxin capsules for severe chronic osteoarthritis pain could not be verified from the available sources. | There is no mention of Novaproxin in the context, only Meloxicam and Indomethacin are mentioned as treatments for osteoarthritis pain. | 0.37 |
| `E2E-097` | The available clinical sources do not state the specific information requested about using Novaproxin capsules for severe chronic osteoarthritis pain. | Similar to the previous statement, there is no mention of Novaproxin in the context. The only relevant information is about Meloxicam and Indomethacin. | 0.39 |
| `E2E-041` | The label text identifies Glibenclarnide. | There is no information given in the context about Glibenclarnide. The only mention of a medication with a similar name is Glyburide, but it's not explicitly stated as Glibenclarnide. | 0.38 |
| `E2E-041` | Glibenclarnide is also known as Glyburide. | The context mentions that the medication with the generic name Glyburide has a brand name of glyburide, which is similar to Glibenclarnide. However, it's not explicitly stated that they are the same medication. | 0.36 |
| `E2E-081` | Thymoglobulin is not labeled for treating Headache. | The context mentions that Thymoglobulin is indicated for the prophylaxis and treatment of acute rejection in patients receiving a kidney transplant, but it does not mention anything about treating Headache. Therefore, it cannot be deduced that Thymoglobulin is not labeled for treating Headache. | 0.48 |
| `E2E-081` | Thymoglobulin is not labeled for treating Spinal Osteophytosis. | The context mentions that Thymoglobulin contains ANTI-THYMOCYTE GLOBULIN (RABBIT) and is indicated for the prophylaxis and treatment of acute rejection in patients receiving a kidney transplant, but it does not mention anything about treating Spinal Osteophytosis. Therefore, it cannot be deduced that Thymoglobulin is not labeled for treating Spinal Osteophytosis. | 0.48 |
| `E2E-081` | Thymoglobulin is not labeled for treating Spinal Stenosis. | The context mentions that Thymoglobulin contains ANTI-THYMOCYTE GLOBULIN (RABBIT) and is indicated for the prophylaxis and treatment of acute rejection in patients receiving a kidney transplant, but it does not mention anything about treating Spinal Stenosis. Therefore, it cannot be deduced that Thymoglobulin is not labeled for treating Spinal Stenosis. | 0.55 |
| `E2E-081` | Thymoglobulin is not labeled for treating Spirurida Infections. | The context mentions that Thymoglobulin contains ANTI-THYMOCYTE GLOBULIN (RABBIT) and is indicated for the prophylaxis and treatment of acute rejection in patients receiving a kidney transplant, but it does not mention anything about treating Spirurida Infections. Therefore, it cannot be deduced that Thymoglobulin is not labeled for treating Spirurida Infections. | 0.50 |
| `E2E-081` | Thymoglobulin does not cover Headache. | The context mentions that Thymoglobulin contains ANTI-THYMOCYTE GLOBULIN (RABBIT) and is indicated for the prophylaxis and treatment of acute rejection in patients receiving a kidney transplant, but it does not mention anything about treating Headache. Therefore, it cannot be deduced that Thymoglobulin does not cover Headache. | 0.43 |
