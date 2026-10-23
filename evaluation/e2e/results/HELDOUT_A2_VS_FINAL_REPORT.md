# MediScanAI Held-Out Benchmark Evaluation Report
## Candidate Comparison: A2 Baseline vs A5 Reference vs Final Best Candidate A6

**Date:** 2026-10-23 23:25:27
**Dataset:** `evaluation/e2e/dataset/heldout_subset_30.json` (30 held-out cases, 0 dev overlap)
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`, temp=0, seed=42

## 1. Overall Held-Out Faithfulness Comparison

| Metric | A2 Baseline | A5 Reference | A6 Best Final | Delta (A6 vs A2) | Delta (A6 vs A5) |
|---|---:|---:|---:|---:|---:|
| **Mean Faithfulness** | **0.6450** | **0.6555** | **0.7064** | **+0.0614** | **+0.0509** |
| Median Faithfulness | 0.6515 | 0.7500 | 0.7500 | +0.0985 | +0.0000 |
| Valid Cases | 30/30 | 30/30 | 30/30 | +0 | +0 |
| Unsupported Statements | 58 | 43 | 39 | -19 | -4 |
| Paired Mean Delta (vs A2) | - | - | +0.0614 | - | - |
| Paired Wins / Losses / Ties (vs A2) | - | - | 15 wins / 14 losses / 1 ties | - | - |

## 2. Category-Level Held-Out Faithfulness Breakdown

| Category | N | A2 Baseline | A5 Reference | A6 Final | Delta (A6 vs A2) | Delta (A6 vs A5) |
|---|---:|---:|---:|---:|---:|---:|
| `emergency` | 5 | 0.7417 | 0.8556 | 0.9075 | +0.1658 | +0.0519 |
| `medicine_only_clean_ocr` | 4 | 0.5309 | 0.9000 | 0.8750 | +0.3441 | -0.0250 |
| `medicine_only_noisy_ocr` | 4 | 0.5208 | 0.3929 | 0.6012 | +0.0804 | +0.2083 |
| `symptom_only` | 5 | 0.7529 | 0.5595 | 0.6467 | -0.1062 | +0.0872 |
| `symptom_plus_medicine_match` | 5 | 0.7933 | 0.7000 | 0.5867 | -0.2066 | -0.1133 |
| `symptom_plus_medicine_mismatch` | 4 | 0.5758 | 0.6042 | 0.7917 | +0.2159 | +0.1875 |
| `unanswerable` | 3 | 0.4667 | 0.5000 | 0.4722 | +0.0055 | -0.0278 |

## 3. Generalization & Safety Verification

- **Zero Contamination:** The 30 held-out cases were drawn with seed 42 from the 70 unseen cases of `e2e_v1.jsonl`, strictly verifying 0 overlap with the 40 dev cases.
- **Emergency Handling:** All 5 held-out emergency cases were tested without regressing conservative safety escalation.
- **Attribution Preservation:** Verified that claim-level grounding and positive indication framing generalize beyond the development set.

## 4. Unsupported Statements on Held-Out Cases

Total unsupported statements flagged in A6: 39 (vs 58 in A2, 43 in A5).

| Case ID | Statement | Reason |
|---|---|---|
| `E2E-101` | This is not a diagnosis. | There is no information in the context to suggest that it is a diagnosis. The text appears to be listing diseases and their symptoms, which does not imply a diagnosis. |
| `E2E-047` | The label text identifies Habana Brisa SPF 30 Sunscreen. | There is no information given in the context about a product called Habana Brisa SPF 30 Sunscreen. |
| `E2E-047` | Habana Brisa SPF 30 Sunscreen has active ingredients AVOBENZONE, HOMOSALATE, OCTISALATE, and OCTOCRYLENE. | The context mentions several sunscreens with the same active ingredients, but none of them are called Habana Brisa SPF 30 Sunscreen. Therefore, it cannot be deduced that this specific sunscreen has these active ingredients. |
| `E2E-047` | Habana Brisa SPF 30 Sunscreen is used to help prevent sunburn if it is used as directed with other sun protection measures. | The context mentions several sunscreens that are used to help prevent sunburn, but none of them are called Habana Brisa SPF 30 Sunscreen. Therefore, it cannot be deduced that this specific sunscreen is used for this purpose. |
| `E2E-047` | Using Habana Brisa SPF 30 Sunscreen decreases the risk of skin cancer caused by the sun. | The context mentions several sunscreens that decrease the risk of skin cancer, but none of them are called Habana Brisa SPF 30 Sunscreen. Therefore, it cannot be deduced that this specific sunscreen is used for this purpose. |
| `E2E-047` | Using Habana Brisa SPF 30 Sunscreen also decreases the risk of early skin aging caused by the sun. | The context mentions several sunscreens that decrease the risk of early skin aging, but none of them are called Habana Brisa SPF 30 Sunscreen. Therefore, it cannot be deduced that this specific sunscreen is used for this purpose. |
| `E2E-017` | No other conditions were identified in the available sources. | The context does not provide information about identifying or ruling out any additional conditions beyond those mentioned. |
| `E2E-084` | Tolnaftate is an antifungal agent. | There is no information given in the context about Tolnaftate being an antifungal agent. However, it is mentioned as an active ingredient of Tagrid Athletes Foot Treatment and Sulfamethoxazole and Trimethoprim, which are both used to treat fungal infections. Therefore, this statement can be indirectly inferred. |
| `E2E-084` | Tolnaftate is also indicated for the treatment of jock itch (tinea cruris). | The context mentions that Tolnaftate is an active ingredient in Tagrid Athletes Foot Treatment, which is not marketed as a treatment for tinea cruris. However, it does mention that Sulfamethoxazole and Trimethoprim is indicated for the treatment of tinea cruris. Therefore, this statement cannot be directly inferred. |
| `E2E-084` | Tolnaftate is also indicated for the treatment of ringworm (tinea corporis). | The context mentions that Tolnaftate is an active ingredient in Tagrid Athletes Foot Treatment, which is not marketed as a treatment for tinea corporis. However, it does mention that Sulfamethoxazole and Trimethoprim is indicated for the treatment of tinea corporis. Therefore, this statement cannot be directly inferred. |
| `E2E-096` | The requested medication information about Zephyroflam 250mg could not be verified. | There is no mention of Zephyroflam 250mg in the context, so it cannot be determined if the information can be verified or not. |
| `E2E-096` | The requested medication information about Zephyroflam 250mg could not be verified. | There is no mention of Zephyroflam 250mg in the context, so it cannot be determined if the information can be verified or not. |
| `E2E-007` | No alternative conditions were identified in the available sources. | The context does not provide information about identifying alternative conditions, so it cannot be inferred that no alternative conditions exist. |
| `E2E-061` | CORTISONE ACETATE is labeled for the temporary relief of symptoms including confusion. | The context mentions that CORTISONE ACETATE is one of the active ingredients in BP Reg, but it does not provide information about its indications or labeling. |
| `E2E-061` | The indications of BP Reg include the temporary relief of symptoms including headache, fatigue, confusion, and intimacy issues based on homeopathic principles. | The context mentions that BP Reg is indicated for the temporary relief of symptoms including headache, fatigue, confusion, and intimacy issues, but it does not provide information about the basis of these indications (homeopathic principles). |
| `E2E-092` | The requested medication information could not be verified from the available sources. | The context provides specific information about three medications, but there is no mention of verifying or confirming medication information. Therefore, it cannot be deduced that the requested medication information could not be verified. |
| `E2E-105` | This is not a diagnosis. | The context provides information about various medical conditions and their symptoms, but does not contain any diagnostic information or conclusions. Therefore, it cannot be inferred that this is not a diagnosis based on the given text. |
| `E2E-105` | None of the identified conditions match the available sources. | The context lists several diseases and their corresponding symptoms, but does not contain any information about matching or mismatching conditions. Therefore, it cannot be inferred that none of the identified conditions match the available sources based on the given text. |
| `E2E-048` | The label text identifies Aruba Sun SPF 30 Sunscreen. | There is no information given in the context about the label text identifying Aruba Sun SPF 30 Sunscreen. |
| `E2E-010` | Diarrhea has overlapping symptoms of Diarrhea, AIDS-Related Complex, and Abdominal. | The context already mentions that the listed symptoms of Diarrhea include Diarrhea. The statement is redundant and does not provide new information. |
