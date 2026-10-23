# MediScanAI A3 Evaluation Report (vs A2)

**Date:** 2026-10-22 21:02:49
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`
**Dataset:** `dev_subset_40.json` (40 frozen development cases)

## 1. Overall Faithfulness Summary

| Metric | A2 Baseline | A3 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.5282** | **0.6558** | **+0.1276** |
| Median Faithfulness | 0.5000 | 0.7018 | +0.2018 |
| Valid Cases (non-NaN) | 39/40 | 40/40 | +1 |
| NaN Count | 1 | 0 | -1 |
| Paired Mean Delta | - | - | +0.1188 |
| Wins / Losses / Ties | - | - | 17 wins / 2 losses / 20 ties |

## 2. Category-Level Faithfulness Breakdown

| Category | N | A2 Mean | A3 Mean | Delta | Valid |
|---|---|---|---|---|---|
| `medicine_only_clean_ocr` | 6 | 0.5667 | 0.8929 | +0.3262 | 6/6 |
| `medicine_only_noisy_ocr` | 5 | 0.4867 | 0.7367 | +0.2500 | 5/5 |
| `symptom_only` | 8 | 0.6536 | 0.6744 | +0.0208 | 8/8 |
| `symptom_plus_medicine_match` | 8 | 0.4635 | 0.4948 | +0.0313 | 8/8 |
| `symptom_plus_medicine_mismatch` | 6 | 0.6468 | 0.5774 | -0.0694 | 6/6 |
| `unanswerable` | 7 | 0.3595 | 0.6250 | +0.2655 | 7/7 |

## 3. Cheap Diagnostics and Resource Metrics

| Metric | A2 | A3 | Change |
|---|---|---|---|
| Avg Latency (ms) | 24382.5 | 21052.2 | -3330.3 |
| Avg Prompt Tokens | 1136.0 | 1004.2 | -131.8 |
| Avg Evidence Tokens | 869.8 | 775.1 | -94.7 |
| Avg Eval Tokens | 116.2 | 102.0 | -14.2 |
| Truncated Generations | 0 | 0 | +0 |
| Abstained Generations | 5 | 7 | +2 |
| Invalid Citation Tags | 0 | 0 | +0 |
| Total Citation Tags | 54 | 56 | +2 |

### Routing Distribution
- **A2:** `{'SYMPTOM_AND_MEDICINE': 31, 'SYMPTOM_ONLY': 9}`
- **A3:** `{'SYMPTOM_ONLY': 8, 'MEDICINE_ONLY': 11, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`

## 4. Unsupported Statements Analysis (60 statements)

Found 60 unsupported statements flagged by judge in A3 (vs 87 in A2).

| Case ID | Statement | Reason | Fuzzy Overlap |
|---|---|---|---|
| `E2E-008` | Acanthosis nigricrans also includes acne or pimples. | The context lists acanthosis nigricans as a condition and lists acne or pimples as a symptom of seborrheic dermatitis, but not specifically for acanthosis nigricans. Therefore, it cannot be deduced that acanthosis nigricrans includes acne or pimples. | 0.45 |
| `E2E-008` | Acanthosis nigricrans also includes skin growth. | The context lists acanthosis nigricans as a condition and lists skin growth as a symptom of seborrheic keratosis, but not specifically for acanthosis nigricans. Therefore, it cannot be deduced that acanthosis nigricrans includes skin growth. | 0.37 |
| `E2E-008` | Acanthosis nigricrans also includes skin lesion. | The context lists acanthosis nigricans as a condition and lists skin lesion as a symptom of seborrheic keratosis, but not specifically for acanthosis nigricans. Therefore, it cannot be deduced that acanthosis nigricrans includes skin lesion. | 0.37 |
| `E2E-008` | Seborrheic dermatitis also includes abnormal appearing skin. | The context lists seborrheic dermatitis as a condition and lists abnormal appearing skin as a symptom of seborrheic keratosis, but not specifically for seborrheic dermatitis. Therefore, it cannot be deduced that seborrheic dermatitis includes abnormal appearing skin. | 0.55 |
| `E2E-008` | Seborrheic dermatitis also includes roughness. | The context lists seborrheic dermatitis as a condition and lists roughness as a symptom of seborrheic keratosis, but not specifically for seborrheic dermatitis. Therefore, it cannot be deduced that seborrheic dermatitis includes roughness. | 0.41 |
| `E2E-008` | Seborrheic dermatitis also includes peeling. | The context lists seborrheic dermatitis as a condition and lists peeling as a symptom of seborrheic keratosis, but not specifically for seborrheic dermatitis. Therefore, it cannot be deduced that seborrheic dermatitis includes peeling. | 0.40 |
| `E2E-008` | Seborrheic dermatitis also includes scaliness. | The context lists seborrheic dermatitis as a condition and lists scaliness as a symptom of seborrheic keratosis, but not specifically for seborrheic dermatitis. Therefore, it cannot be deduced that seborrheic dermatitis includes scaliness. | 0.39 |
| `E2E-008` | Seborrheic dermatitis also includes skin dryness. | The context lists seborrheic dermatitis as a condition and lists skin dryness as a symptom of seborrheic keratosis, but not specifically for seborrheic dermatitis. Therefore, it cannot be deduced that seborrheic dermatitis includes skin dryness. | 0.39 |
| `E2E-069` | The label evidence for Penicillin V Potassium lists uses that match your symptoms. | The context mentions the indications of Penicillin V Potassium, which include treating infections due to penicillin G-sensitive microorganisms. However, there is no information about the specific symptoms mentioned in the statement being matched by the label evidence. | 0.33 |
| `E2E-069` | Your symptoms are bacteremia, abdominal tenderness, chill, decreased translucency, and diarrhea. | The context lists several diseases and their corresponding symptoms. The statement mentions a combination of symptoms that can be found in multiple diseases listed in the context. Therefore, it cannot be directly inferred that these specific symptoms match any particular disease mentioned in the context. | 0.37 |
| `E2E-088` | The label evidence for Theraflu Severe Cold Relief lists uses that match your symptoms. | The context mentions the indications of Theraflu Severe Cold Relief, which include relieving minor aches and pains, sore throat pain, headache, cough due to minor throat and bronchial irritation, and reducing fever. Since the user's symptoms (muscular dystrophy, cough, fatigue, and feeling cold) are not explicitly mentioned in the context as being relieved by Theraflu Severe Cold Relief, it cannot be deduced that the label evidence lists uses that match the user's symptoms. | 0.35 |
| `E2E-093` | Lipitor is also used to reduce LDL-C in adults and pediatric patients 10 years of age or older with heterozygous familial hypercholesterolemia. | The context does not mention this specific indication for Lipitor, so it cannot be directly inferred from the given text. | 0.27 |
| `E2E-032` | Hospicare 40R Adult Body Wipes is used for surface cleaning and is gentle on skin. | The context mentions that Hospicare 40R Adult Body Wipes are 'Improves patient care and satisfaction ●Eliminates odour associated with incontinence changes ●Eliminates use of harsh soaps, rough washcloths and towel drying ●Helps you stay cool, clean, comfortable and refreshed anytime, anywhere'. Although it does not explicitly mention surface cleaning, the context implies that it is used for cleaning purposes. However, there is no information suggesting it is gentle on skin. | 0.29 |
| `E2E-044` | The label evidence lists active ingredients AVOBENZONE, OCTINOXATE, AND OXYBENZONE. | The context does not provide a list of active ingredients for Laura Mercier Flawless Skin Repair Day Creme Broad Spectrum SPF 15 Sunscreen. However, it is mentioned in the indications section that the product helps prevent sunburn if used as directed with other sun protection measures (see Directions ). | 0.40 |
| `E2E-044` | Using Laura Mercier Flawless Skin Repair Day Creme Broad Spectrum SPF 15 Sunscreen decreases the risk of skin cancer. | The context mentions that using the product helps prevent sunburn and decreases the risk of early skin aging caused by the sun, but it does not explicitly state that it decreases the risk of skin cancer. | 0.58 |
| `E2E-073` | The label evidence for Meclizine Hydrochloride lists uses that match your symptoms. | The context mentions several drug labels, but only one of them is for Meclizine Hydrochloride. The statement cannot be directly inferred from the given information. | 0.33 |
| `E2E-073` | Your symptoms include Vertigo, Brain Diseases, Brain Edema, Brain Infarction, and Brain Injuries. | The context lists several diseases and conditions, but it does not explicitly state that the user's symptoms match any of them. Therefore, this statement cannot be directly inferred from the given information. | 0.35 |
| `E2E-082` | The label evidence for Strophanthus lists uses that match your symptoms. | The context mentions several drug labels, but none of them explicitly mention matching symptoms. Therefore, it cannot be deduced that the label evidence for Strophanthus lists uses that match the user's symptoms. | 0.31 |
| `E2E-082` | Your symptoms are Arthralgia, Abdominal pain, and induced abortion. | The context mentions several disease labels, but none of them explicitly mention all three symptoms. The label for [E3] DISEASE | id=disease_chunk_2722 | Condition: induced abortion does list induced abortion as a symptom, but it also lists other symptoms that are not mentioned in the statement. | 0.41 |
| `E2E-034` | ANTICHOLIUM's label evidence lists active ingredients PHYSOSTIGMINE SALICYLATE. | The context explicitly mentions that ANTICHOLIUM is indicated for the use as an antidote and/or antagonist in case of intoxication with and/or overdose of alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine). However, it does not mention PHYSOSTIGMINE SALICYLATE as an active ingredient. Therefore, it cannot be deduced that ANTICHOLIUM's label evidence lists active ingredients PHYSOSTIGMINE SALICYLATE. | 0.40 |
| `E2E-034` | ANTICHOLIUM's label evidence indicates its use as an antidote and/or antagonist in case of overdose of alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine). | The context explicitly mentions that ANTICHOLIUM is indicated for the use as an antidote and/or antagonist in case of intoxication with and/or overdose of alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine). However, it does not mention overdose specifically. Therefore, it cannot be deduced that ANTICHOLIUM's label evidence indicates its use as an antidote and/or antagonist in case of overdose of alcohol tropane alkaloids (hyoscyamine, atropine, scopolamine). | 0.77 |
| `E2E-024` | Cerebral palsy includes cerebral palsy, blindness, cramps and spasms, infant feeding problem. | The context already lists these symptoms under the condition of cerebral palsy. Therefore, it cannot be deduced that this is an inclusion statement. | 0.38 |
| `E2E-024` | Synkinesis includes Cerebral Palsy. | The context explicitly mentions Synkinesis as a separate condition in [E2], and does not indicate that it includes cerebral palsy. Therefore, this cannot be directly inferred from the given information. | 0.58 |
| `E2E-024` | Neonatal jaundice includes infant feeding problem. | The context lists neonatal jaundice as a condition in [E3] and does not indicate that it includes infant feeding problem. Therefore, this cannot be directly inferred from the given information. | 0.61 |
| `E2E-024` | The medicine could not be identified from the available sources. | The context does mention Xeomin and Cuvposa as drugs in [E4] and [E5], but it does not provide information about identifying medicines. Therefore, this cannot be directly inferred from the given information. | 0.31 |
