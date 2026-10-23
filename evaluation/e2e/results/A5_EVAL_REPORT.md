# MediScanAI A5 Evaluation Report (vs A4)

**Date:** 2026-10-23 14:48:21
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`
**Dataset:** `dev_subset_40.json` (40 frozen development cases)

## 1. Overall Faithfulness Summary

| Metric | A4 Baseline | A5 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.7256** | **0.7538** | **+0.0282** |
| Median Faithfulness | 0.8167 | 0.8000 | -0.0167 |
| Valid Cases (non-NaN) | 40/40 | 40/40 | +0 |
| NaN Count | 0 | 0 | +0 |
| Paired Mean Delta | - | - | +0.0283 |
| Wins / Losses / Ties | - | - | 12 wins / 8 losses / 20 ties |

## 2. Category-Level Faithfulness Breakdown

| Category | N | A4 Mean | A5 Mean | Delta | Valid |
|---|---|---|---|---|---|
| `medicine_only_clean_ocr` | 6 | 0.9583 | 0.9667 | +0.0084 | 6/6 |
| `medicine_only_noisy_ocr` | 5 | 0.8000 | 0.9333 | +0.1333 | 5/5 |
| `symptom_only` | 8 | 0.7250 | 0.6628 | -0.0622 | 8/8 |
| `symptom_plus_medicine_match` | 8 | 0.7688 | 0.8604 | +0.0916 | 8/8 |
| `symptom_plus_medicine_mismatch` | 6 | 0.6648 | 0.8056 | +0.1408 | 6/6 |
| `unanswerable` | 7 | 0.4762 | 0.3809 | -0.0953 | 7/7 |

## 3. Cheap Diagnostics and Resource Metrics

| Metric | A4 | A5 | Change |
|---|---|---|---|
| Avg Latency (ms) | 19073.2 | 24339.1 | +5265.9 |
| Avg Prompt Tokens | 1024.1 | 946.1 | -78.0 |
| Avg Evidence Tokens | 775.1 | 647.2 | -127.9 |
| Avg Eval Tokens | 98.8 | 102.8 | +4.0 |
| Truncated Generations | 0 | 0 | +0 |
| Abstained Generations | 9 | 3 | -6 |
| Invalid Citation Tags | 0 | 0 | +0 |
| Total Citation Tags | 46 | 54 | +8 |

### Routing Distribution
- **A4:** `{'MEDICINE_ONLY': 11, 'SYMPTOM_ONLY': 8, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`
- **A5:** `{'SYMPTOM_ONLY': 8, 'MEDICINE_ONLY': 11, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`

## 4. Unsupported Statements Analysis (40 statements)

Found 40 unsupported statements flagged by judge in A5 (vs 87 in A4).

| Case ID | Statement | Reason | Fuzzy Overlap |
|---|---|---|---|
| `E2E-008` | Seborrheic dermatitis includes acne or pimples, skin growth and skin lesion as symptoms. | The context lists the symptoms of Seborrheic dermatitis, but it does not explicitly mention acne or pimples, skin growth, and skin lesion. However, it does list seborrheic dermatitis, abnormal appearing skin, dry or flaky scalp, irregular appearing scalp, itching of skin, or roughness, peeling, scaliness, skin dryness, skin irritation, skin moles, skin rash, skin swelling, and warts as symptoms. | 0.34 |
| `E2E-069` | The symptoms of bacteremia, abdominal tenderness, chill, decreased translucency, and diarrhea are consistent with a condition that can be treated with Penicillin V Potassium. | Bacteremia is mentioned as a condition in the context, but it does not explicitly state that these symptoms are consistent with a condition that can be treated with Penicillin V Potassium. Therefore, this statement cannot be directly inferred from the context. | 0.33 |
| `E2E-009` | Nephrosis lists overlapping symptoms: Nephritis; Neovascularization . | The context lists the symptoms of Blindness and Proteinuria, but it does not explicitly state that Nephrosis lists these symptoms. Therefore, it cannot be deduced. | 0.43 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg is labeled for prescription only. | There is no information given in the context about the labeling of Strophanthus (STROPHANTHUS) 20mg being for prescription only. However, it can be inferred that since there are several other medicines with similar indications and "Rx Only*" labels, this medicine might also require a prescription. | 0.44 |
| `E2E-100` | The statement that the Glycozempra 5mg/mL solution evidence does not state the pediatric weight-based dosing information is a single statement. | There is no mention of Glycozempra 5mg/mL solution in the context, so it cannot be inferred that this statement is true or false based on the given text. | 0.34 |
| `E2E-100` | The statement that the Glycozempra 5mg/mL solution evidence does not state the pediatric weight-based dosing information can be broken down into two statements: The Glycozempra 5mg/mL solution evidence does not exist, and this evidence does not state the pediatric weight-based dosing information. | The context mentions several drugs, but there is no mention of Glycozempra 5mg/mL solution. Therefore, it cannot be inferred that this statement is true or false based on the given text. | 0.28 |
| `E2E-034` | ANTICHOLIUM is used to treat amantadine and diphenhydramine. | The context explicitly mentions that ANTICHOLIUM is indicated for treating amanita pantherina and amanita muscaria tricyclic antidepressants, which includes amitriptyline, imipramine, trimipramine, clomipramine, and doxepine. However, it does not explicitly mention the treatment of amantadine and diphenhydramine. | 0.41 |
| `E2E-034` | ANTICHOLIUM is used to treat baclofen and 4-hydroxybutyric acid (GHB). | The context explicitly mentions that ANTICHOLIUM is indicated for treating amanita pantherina and amanita muscaria tricyclic antidepressants, which includes amitriptyline, imipramine, trimipramine, clomipramine, and doxepine. However, it does not explicitly mention the treatment of baclofen and 4-hydroxybutyric acid (GHB). | 0.48 |
| `E2E-024` | The symptoms you describe overlap with the conditions listed below. | The context explicitly mentions that the symptoms described are related to specific conditions, but it does not provide a direct comparison or mention of overlapping symptoms. Therefore, this statement cannot be directly inferred from the given context. | 0.33 |
| `E2E-024` | Cerebral palsy lists overlapping symptoms: cerebral palsy; blindness; cramps and spasms. | The context explicitly mentions that cerebral palsy is a condition with listed symptoms, but it does not provide information about the specific symptoms being mentioned in this statement. Therefore, this statement cannot be directly inferred from the given context. | 0.48 |
| `E2E-024` | Xeomin is labeled for upper limb spasticity in pediatric patients 2 to 17 years of age, excluding spasticity caused by cerebral palsy. | The context explicitly mentions that Xeomin is indicated for upper limb spasticity in pediatric patients, but it does not provide information about the exclusion criteria. Therefore, this statement cannot be directly inferred from the given context. | 0.58 |
| `E2E-062` | The Joette Calabrese Survivalist Kit is labeled for confusion/memory. | The context mentions that the kit contains various homeopathic remedies with specific indications, and one of them is AMBRA GRISEA 30C which is indicated for confusion/memory. However, it does not explicitly state that the entire kit is labeled for this purpose. | 0.52 |
| `E2E-062` | ACONITUM NAPELLUS is labeled for shock, but also AMBRA GRISEA 30C, which is specifically indicated for confusion/memory. | The context lists the indications for ACONITUM NAPELLUS as shock, and it does not mention any indication of confusion/memory. However, it does mention that AMBRA GRISEA 30C is labeled for this purpose. | 0.40 |
| `E2E-091` | The information about the medicine could not be found. | The context explicitly mentions information about Alprazolam Extended Release and Ursodiol, but there is no mention of NonexistentDrugZ 500mg tablets. Therefore, it cannot be deduced that the information about this drug could not be found. | 0.26 |
| `E2E-091` | NonexistentDrugZ 500mg tablets were not mentioned in any available sources. | The context does mention Ursodiol and Alprazolam Extended Release, but there is no information about NonexistentDrugZ 500mg tablets. This statement cannot be directly inferred from the given context. | 0.35 |
| `E2E-091` | There is no evidence that NonexistentDrugZ 500mg tablets exist. | The context does not provide any information about the existence or non-existence of NonexistentDrugZ 500mg tablets. This statement cannot be directly inferred from the given context. | 0.40 |
| `E2E-025` | Breech presentation and adhesion are also mentioned as symptoms of HIV infections. | The context does not mention breech presentation or adhesion as symptoms of HIV infections. Breech presentation is actually listed under a different disease, and adhesion is listed under another disease with the same condition ID as HIV. Therefore, it cannot be directly inferred that these symptoms are associated with HIV infections. | 0.49 |
| `E2E-080` | The indications on the label of the medicine Neomycin and Polymyxin B Sulfates and Bacitracin Zinc do not include treating depression. | There is no information in the context about the indications for treating depression, but it does mention insomnia as a condition related to one of the drugs (Temazepam). | 0.48 |
| `E2E-080` | The indications on the label of the medicine Neomycin and Polymyxin B Sulfates and Bacitracin Zinc do not include treating headache. | There is no information in the context about the indications for treating headache, but it does mention insomnia as a condition related to one of the drugs (Temazepam). | 0.48 |
| `E2E-080` | The indications on the label of the medicine Neomycin and Polymyxin B Sulfates and Bacitracin Zinc do not include treating irritability. | There is no information in the context about the indications for treating irritability, but it does mention insomnia as a condition related to one of the drugs (Temazepam). | 0.47 |
| `E2E-097` | Novaproxin is labeled for the management of osteoarthritis pain. | There is no information given in the context about Novaproxin, but Meloxicam is mentioned as an active ingredient and it is indeed used to manage osteoarthritis pain. However, there is no direct mention of Novaproxin. | 0.56 |
| `E2E-097` | The medicine Novaproxin contains Meloxicam as its active ingredient. | There is no information given in the context about Novaproxin's composition. However, it does mention that Meloxicam is an active ingredient of a drug (Meloxicam capsules) used to manage osteoarthritis pain. | 0.32 |
| `E2E-041` | The label text identifies Glibenclarnide. | There is no information given in the context about Glibenclarnide. The only mention of a medication with a similar name (Glyburide) is in id=3489, but it's not explicitly stated as Glibenclarnide. | 0.38 |
| `E2E-041` | The active ingredients of Glibenclarnide include ALLOPURINOL is not stated in the available sources. | There is no information given in the context about the active ingredients of Glibenclarnide. The only mention of Allopurinol is in id=24160, but it's a separate medication with its own indications and warnings. | 0.45 |
| `E2E-041` | Allopurinol tablets, USP reduces serum and urinary uric acid concentrations. | The context mentions that 'Allopurinol tablets, USP reduces serum and urinary uric acid concentrations' for Allopurinol in id=24160. This is a specific action of the medication and does not necessarily apply to Glibenclarnide if it were mentioned. | 0.99 |
