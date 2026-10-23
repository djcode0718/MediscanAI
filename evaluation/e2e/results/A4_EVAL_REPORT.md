# MediScanAI A4 Evaluation Report (vs A2)

**Date:** 2026-10-23 01:29:39
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`
**Dataset:** `dev_subset_40.json` (40 frozen development cases)

## 1. Overall Faithfulness Summary

| Metric | A2 Baseline | A4 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.5282** | **0.7256** | **+0.1974** |
| Median Faithfulness | 0.5000 | 0.8167 | +0.3167 |
| Valid Cases (non-NaN) | 39/40 | 40/40 | +1 |
| NaN Count | 1 | 0 | -1 |
| Paired Mean Delta | - | - | +0.1903 |
| Wins / Losses / Ties | - | - | 26 wins / 10 losses / 3 ties |

## 2. Category-Level Faithfulness Breakdown

| Category | N | A2 Mean | A4 Mean | Delta | Valid |
|---|---|---|---|---|---|
| `medicine_only_clean_ocr` | 6 | 0.5667 | 0.9583 | +0.3916 | 6/6 |
| `medicine_only_noisy_ocr` | 5 | 0.4867 | 0.8000 | +0.3133 | 5/5 |
| `symptom_only` | 8 | 0.6536 | 0.7250 | +0.0714 | 8/8 |
| `symptom_plus_medicine_match` | 8 | 0.4635 | 0.7688 | +0.3053 | 8/8 |
| `symptom_plus_medicine_mismatch` | 6 | 0.6468 | 0.6648 | +0.0180 | 6/6 |
| `unanswerable` | 7 | 0.3595 | 0.4762 | +0.1167 | 7/7 |

## 3. Cheap Diagnostics and Resource Metrics

| Metric | A2 | A4 | Change |
|---|---|---|---|
| Avg Latency (ms) | 24382.5 | 19073.2 | -5309.3 |
| Avg Prompt Tokens | 1136.0 | 1024.1 | -111.9 |
| Avg Evidence Tokens | 869.8 | 775.1 | -94.7 |
| Avg Eval Tokens | 116.2 | 98.8 | -17.4 |
| Truncated Generations | 0 | 0 | +0 |
| Abstained Generations | 5 | 9 | +4 |
| Invalid Citation Tags | 0 | 0 | +0 |
| Total Citation Tags | 54 | 46 | -8 |

### Routing Distribution
- **A2:** `{'SYMPTOM_AND_MEDICINE': 31, 'SYMPTOM_ONLY': 9}`
- **A4:** `{'SYMPTOM_ONLY': 8, 'MEDICINE_ONLY': 11, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`

## 4. Unsupported Statements Analysis (52 statements)

Found 52 unsupported statements flagged by judge in A4 (vs 87 in A2).

| Case ID | Statement | Reason | Fuzzy Overlap |
|---|---|---|---|
| `E2E-008` | Seborrheic dermatitis includes acne or pimples, skin growth and skin lesion as its symptoms. | The context explicitly lists the symptoms of Seborrheic dermatitis, which include seborrheic dermatitis, abnormal appearing skin, acne or pimples, dry or flaky scalp, irregular appearing scalp, itching of skin, or roughness, peeling, scaliness, skin dryness, skin growth, skin lesion. However, it does not explicitly mention acne or pimples, skin growth and skin lesion as its symptoms. | 0.33 |
| `E2E-073` | The indications for Meclizine Hydrochloride are stated in EVIDENCE block | While the context does contain information about Meclizine Hydrochloride's indications, it is not explicitly stated that this information can be found in an 'EVIDENCE' block. The indications are mentioned in several evidence blocks, but the specific wording of the statement cannot be directly inferred from the context. | 0.38 |
| `E2E-073` | EVIDENCE block states that Meclizine Hydrochloride is indicated for the treatment of vertigo associated with diseases affecting the vestibular system | The context does contain information about Meclizine Hydrochloride's indications, but it is not explicitly stated in an 'EVIDENCE' block. The statement can be found in several evidence blocks, including E5, E6, and E8. | 0.48 |
| `E2E-073` | Vertigo associated with diseases affecting the vestibular system matches one of the described conditions (Vertigo) in USER_TEXT | The context does contain information about vertigo being a condition that can be treated by Meclizine Hydrochloride, but it is not explicitly stated as matching one of the described conditions in 'USER_TEXT'. The statement can be found in several evidence blocks, including E5, E6, and E8. | 0.38 |
| `E2E-082` | The available sources do not mention the uses of Strophanthus for treating Arthralgia symptoms. | The context mentions Arthralgia under disease chunk 2102, but there is no information about its treatment with Strophanthus. | 0.30 |
| `E2E-082` | The available sources do not mention the uses of Strophanthus for treating Abdominal symptoms. | The context mentions several diseases and conditions, including induced abortion, which has abdominal pain as a symptom. However, there is no information about using Strophanthus to treat this symptom. | 0.28 |
| `E2E-082` | The available sources do not mention the uses of Strophanthus for treating Abnormalities symptoms. | There is no information in the context about Strophanthus being used to treat abnormalities, and it's unlikely that a medication would be labeled as Rx Only without any therapeutic use. | 0.27 |
| `E2E-082` | The available sources do not mention the uses of Strophanthus for treating Abortion symptoms. | The context mentions induced abortion under disease chunk 100 and 2722, but there is no information about using Strophanthus to treat this symptom. | 0.31 |
| `E2E-082` | Strophanthus is labeled as "Rx Only", which means it does not provide information on its therapeutic use. | The context explicitly states that Strophanthus hispidus and Strophanthus 4X are labeled as Rx Only, indicating they require a prescription but do not provide information on their therapeutic use. | 0.28 |
| `E2E-100` | The pediatric weight-based dosing for Glycozempra 5mg/mL solution is not stated. | There is no information given in the context about the pediatric weight-based dosing for Glycozempra 5mg/mL solution. However, there is a mention of Glycopyrrolate Oral Solution which has similar name but different indication and dosage. | 0.33 |
| `E2E-100` | The available sources do not state the pediatric weight-based dosing for Glycozempra 5mg/mL solution. | This statement is a rephrased version of the first statement, and it also cannot be directly inferred from the context. | 0.30 |
| `E2E-034` | The scanned drug label also mentions overdosing on alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine) as a reason to use ANTICHOLIUM. | The context explicitly mentions that ANTICHOLIUM is indicated for the use as an antidote and/or antagonist in case of intoxication with alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine). However, it does not mention overdosing on these substances as a reason to use ANTICHOLIUM. Therefore, it cannot be directly inferred that the scanned drug label also mentions overdosing on alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine) as a reason to use ANTICHOLIUM. | 0.60 |
| `E2E-024` | Neonatal jaundice is a condition that lists overlapping symptoms such as infant feeding problem. | The context mentions the symptoms of neonatal jaundice, which include changes in stool appearance and lack of growth. However, it does not mention infant feeding problem as one of its symptoms. Therefore, this statement cannot be directly inferred from the context. | 0.41 |
| `E2E-024` | No alternative medical illnesses were identified in the available sources. | The context mentions multiple diseases and their corresponding symptoms, but it does not provide any information about whether these conditions are the only possible explanations for the described symptoms. Therefore, this statement cannot be directly inferred from the context. | 0.32 |
| `E2E-062` | The Joette Calabrese Survivalist Kit is also labeled for dairy intolerance. | There is no information given in the context about the kit being labeled for dairy intolerance. AGNUS CASTUS 200C is listed as an active ingredient, but it is indicated for impotence/absentmindedness, not dairy intolerance. | 0.33 |
| `E2E-062` | The Joette Calabrese Survivalist Kit is also labeled for fever/glands. | There is no information given in the context about the kit being labeled for fever/glands. AILANTHUS GLANDULOSUS 30C is listed as an active ingredient, but it is indicated for fever/glands, not that the kit is labeled for it. | 0.33 |
| `E2E-062` | The Joette Calabrese Survivalist Kit is also labeled for itchy eyelids. | There is no information given in the context about the kit being labeled for itchy eyelids. AMBROSIA ARTEMISIAEFOLIA 30C is listed as an active ingredient, but it is indicated for itchy eyelids, not that the kit is labeled for it. | 0.33 |
| `E2E-062` | The Joette Calabrese Survivalist Kit is also labeled for breathing. | There is no information given in the context about the kit being labeled for breathing. AMMONIUM CARBONATE is listed as an active ingredient, but it is indicated for breathing, not that the kit is labeled for it. | 0.34 |
| `E2E-062` | The Joette Calabrese Survivalist Kit is also labeled for rash. | There is no information given in the context about the kit being labeled for rash. ANTIMONIUM CRUDUM 6C, 200C is listed as an active ingredient, but it is indicated for rash, not that the kit is labeled for it. | 0.36 |
| `E2E-062` | The kit also contains ingredients for associated symptoms such as dryness. | According to the context, the kit contains ingredients for various symptoms including dryness, irritation, inflammation, pain and hoarseness. However, there is no specific information about Aconitum NaPELLUS 1M being used for dryness. | 0.46 |
| `E2E-062` | The kit also contains ingredients for associated symptoms such as irritation. | According to the context, the kit contains ingredients for various symptoms including dryness, irritation, inflammation, pain and hoarseness. However, there is no specific information about Aconitum NaPELLUS 1M being used for irritation. | 0.48 |
| `E2E-062` | The kit also contains ingredients for associated symptoms such as inflammation. | According to the context, the kit contains ingredients for various symptoms including dryness, irritation, inflammation, pain and hoarseness. However, there is no specific information about Aconitum NaPELLUS 1M being used for inflammation. | 0.50 |
| `E2E-062` | The kit also contains ingredients for associated symptoms such as pain. | According to the context, the kit contains ingredients for various symptoms including dryness, irritation, inflammation, pain and hoarseness. However, there is no specific information about Aconitum NaPELLUS 1M being used for pain. | 0.44 |
| `E2E-062` | The kit also contains ingredients for associated symptoms such as hoarseness. | According to the context, the kit contains ingredients for various symptoms including dryness, irritation, inflammation, pain and hoarseness. However, there is no specific information about Aconitum NaPELLUS 1M being used for hoarseness. | 0.48 |
| `E2E-076` | The described condition in the user's query matches one of the labeled indications for Pyrimethamine. | There is no explicit match between the context and the statement. The context describes Toxoplasmosis, but it does not explicitly state that this condition matches any of the labeled indications for Pyrimethamine. | 0.34 |
