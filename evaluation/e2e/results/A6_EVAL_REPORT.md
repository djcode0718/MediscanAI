# MediScanAI A6 Evaluation Report (vs A5)

**Date:** 2026-10-23 18:21:11
**Evaluator:** `SELF-JUDGED (llama3.1:8b)`
**Dataset:** `dev_subset_40.json` (40 frozen development cases)

## 1. Overall Faithfulness Summary

| Metric | A5 Baseline | A6 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.7538** | **0.8021** | **+0.0483** |
| Median Faithfulness | 0.8000 | 1.0000 | +0.2000 |
| Valid Cases (non-NaN) | 40/40 | 40/40 | +0 |
| NaN Count | 0 | 0 | +0 |
| Paired Mean Delta | - | - | +0.0483 |
| Wins / Losses / Ties | - | - | 11 wins / 7 losses / 22 ties |

## 2. Category-Level Faithfulness Breakdown

| Category | N | A5 Mean | A6 Mean | Delta | Valid |
|---|---|---|---|---|---|
| `medicine_only_clean_ocr` | 6 | 0.9667 | 1.0000 | +0.0333 | 6/6 |
| `medicine_only_noisy_ocr` | 5 | 0.9333 | 0.8000 | -0.1333 | 5/5 |
| `symptom_only` | 8 | 0.6628 | 0.8500 | +0.1872 | 8/8 |
| `symptom_plus_medicine_match` | 8 | 0.8604 | 0.8793 | +0.0189 | 8/8 |
| `symptom_plus_medicine_mismatch` | 6 | 0.8056 | 0.8889 | +0.0833 | 6/6 |
| `unanswerable` | 7 | 0.3809 | 0.4167 | +0.0358 | 7/7 |

## 3. Cheap Diagnostics and Resource Metrics

| Metric | A5 | A6 | Change |
|---|---|---|---|
| Avg Latency (ms) | 24339.1 | 23881.5 | -457.6 |
| Avg Prompt Tokens | 946.1 | 946.8 | +0.7 |
| Avg Evidence Tokens | 647.2 | 647.2 | +0.0 |
| Avg Eval Tokens | 102.8 | 92.0 | -10.8 |
| Truncated Generations | 0 | 0 | +0 |
| Abstained Generations | 3 | 0 | -3 |
| Invalid Citation Tags | 0 | 0 | +0 |
| Total Citation Tags | 54 | 44 | -10 |

### Routing Distribution
- **A5:** `{'MEDICINE_ONLY': 11, 'SYMPTOM_ONLY': 8, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`
- **A6:** `{'SYMPTOM_ONLY': 8, 'MEDICINE_ONLY': 11, 'SYMPTOM_AND_MEDICINE': 15, 'UNANSWERABLE': 6}`

## 4. Unsupported Statements Analysis (34 statements)

Found 34 unsupported statements flagged by judge in A6 (vs 40 in A5).

| Case ID | Statement | Reason | Fuzzy Overlap |
|---|---|---|---|
| `E2E-069` | Mild to moderately severe infections are caused by penicillin G-sensitive microorganisms. | The context mentions that Penicillin V Potassium should be used only to treat or prevent infections that are proven or strongly suspected to be caused by susceptible bacteria, and it specifically states that the medication is indicated for mild to moderately severe infections due to penicillin G-sensitive microorganisms. However, this does not directly imply that all mild to moderately severe infections are caused by penicillin G-sensitive microorganisms. | 0.68 |
| `E2E-009` | No medical illness was identified in the available sources. | The context lists several conditions and their associated symptoms, but there is no information suggesting that none of these conditions match the described symptoms. Therefore, it cannot be inferred that no medical illness was identified. | 0.34 |
| `E2E-082` | The medicine Strophanthus (STROPHANTHUS) 20mg is labeled for treatment of induced abortion. | There is no information given in the context about Strophanthus being used to treat induced abortion. The context mentions several diseases and medications, but none of them are related to Strophanthus or induced abortion. | 0.46 |
| `E2E-082` | STROPHANTHUS HISPIDUS SEED is labeled for the treatment of induced abortion. | There is no information given in the context about STROPHANTHUS HISPIDUS SEED being used to treat induced abortion. The context mentions several diseases and medications, but none of them are related to STROPHANTHUS HISPIDUS SEED or induced abortion. | 0.37 |
| `E2E-100` | The requested medication information about Glycozempra 5mg/mL solution could not be verified. | There is no mention of Glycozempra 5mg/mL solution in the provided context, so it cannot be deduced that the requested medication information was found or not. | 0.33 |
| `E2E-100` | The pediatric weight-based dosing for Glycozempra 5mg/mL solution was not found in the provided evidence. | There is no mention of Glycozempra 5mg/mL solution in the provided context, so it cannot be deduced that the pediatric weight-based dosing was found or not. | 0.35 |
| `E2E-062` | ACONITUM NAPELLUS is labeled for confusion/memory. | The context mentions that ACONITUM NAPELLUS is indicated for shock, but it does not mention any indication of confusion/memory. Therefore, this statement cannot be directly inferred from the given context. | 0.51 |
| `E2E-062` | According to its indications, it is labeled for various conditions. | The context mentions that the Joette Calabrese Survivalist Kit has multiple indications, but it does not specify what these conditions are. Therefore, this statement cannot be directly inferred from the given context. | 0.44 |
| `E2E-062` | Confusion/memory is one of these various conditions. | The context explicitly mentions that ACONITUM NAPELLUS is indicated for shock, but it does not mention any indication of confusion/memory. Therefore, this statement cannot be directly inferred from the given context. | 0.32 |
| `E2E-097` | The Novaproxin capsules are labeled for managing osteoarthritis pain. | There is no information given in the context about Novaproxin capsules. However, Meloxicam capsules are mentioned as being indicated for management of osteoarthritis pain. | 0.57 |
| `E2E-097` | The scanned medicine, Novaproxin 100mg (Novapharma Inc), is a non-steroidal anti-inflammatory drug. | Although Meloxicam capsules are mentioned as being indicated for management of osteoarthritis pain and are classified as a non-steroidal anti-inflammatory drug, there is no information given in the context about Novaproxin 100mg (Novapharma Inc). | 0.47 |
| `E2E-097` | The active ingredient of the scanned medicine, Novaproxin 100mg (Novapharma Inc), is Meloxicam. | There is no information given in the context about the active ingredient of Novaproxin 100mg (Novapharma Inc). However, it is mentioned that Meloxicam capsules are indicated for management of osteoarthritis pain and contain Meloxicam as an active ingredient. | 0.31 |
| `E2E-041` | The label text identifies Glibenclarnide. | There is no information given in the context about Glibenclarnide. The context only mentions Allopurinol and other medications, but not Glibenclarnide. | 0.38 |
| `E2E-041` | Glibenclarnide is also known as Glyburide. | The context contains a Drug Name Match with id=3489, which has the name glyburide. This implies that Glibenclarnide and Glyburide are related, but it does not explicitly state that they are the same medication. | 0.36 |
| `E2E-041` | Glibenclarnide contains active ingredients glyburide. | The context contains a Drug Name Match with id=3489, which has the name glyburide. This implies that Glibenclarnide and Glyburide are related, but it does not explicitly state that Glibenclarnide contains glyburide as an active ingredient. | 0.52 |
| `E2E-041` | Glibenclarnide is used to treat indications. | The context mentions Allopurinol, which has several indications listed. However, it does not explicitly state that Glibenclarnide is used to treat any of these indications. | 0.40 |
| `E2E-041` | This medication is not innocuous. | The context mentions Allopurinol, which has a warning stating 'This is not an innocuous drug.' This implies that the medication in question (Allopurinol) is not innocuous. However, it does not explicitly state that Glibenclarnide is not innocuous. | 0.34 |
| `E2E-041` | It is not recommended for the treatment of asymptomatic hyperuricemia. | The context mentions Allopurinol, which has a warning stating 'It is not recommended for the treatment of asymptomatic hyperuricemia.' This implies that Allopurinol should not be used to treat asymptomatic hyperuricemia. However, it does not explicitly state that Glibenclarnide should not be used to treat this condition. | 0.99 |
| `E2E-041` | Allopurinol tablets, USP reduces serum and urinary uric acid concentrations. | The context mentions Allopurinol, which has a description stating 'reduces serum and urinary uric acid concentrations.' This implies that Allopurinol has this effect. However, it does not explicitly state that Glibenclarnide reduces serum and urinary uric acid concentrations. | 0.99 |
| `E2E-041` | The use of this medication should be individualized for each patient. | The context mentions Allopurinol, which has a description stating 'Its use should be individualized for each patient.' This implies that the use of Allopurinol should be individualized. However, it does not explicitly state that Glibenclarnide's use should be individualized. | 0.40 |
| `E2E-041` | Understanding its mode of action is required. | The context mentions Allopurinol, which has a description stating 'Its mode of action and pharmacokinetics (see CLINICAL PHARMACOLOGY, CONTRAINDICATIONS, WARNINGS, and PRECAUTIONS) should be understood.' This implies that understanding the mode of action of Allopurinol is required. However, it does not explicitly state that understanding Glibenclarnide's mode of action is required. | 0.34 |
| `E2E-041` | Understanding its pharmacokinetics is also required. | The context mentions Allopurinol, which has a description stating 'Its mode of action and pharmacokinetics (see CLINICAL PHARMACOLOGY, CONTRAINDICATIONS, WARNINGS, and PRECAUTIONS) should be understood.' This implies that understanding the pharmacokinetics of Allopurinol is required. However, it does not explicitly state that understanding Glibenclarnide's pharmacokinetics is required. | 0.36 |
| `E2E-094` | The requested medication information is not verifiable. | The context provides detailed information about various medications, but it does not address the issue of verifiability or lack thereof. Therefore, it cannot be deduced that the requested medication information is not verifiable. | 0.36 |
| `E2E-094` | Available sources do not contain the required information about Xanthroflurane inhalation. | The context does not mention Xanthroflurane inhalation, but it does provide detailed information about other medications. However, upon closer inspection, there is no indication that Xanthroflurane inhalation is mentioned or discussed in the provided text. Therefore, it cannot be deduced that available sources do not contain the required information about Xanthroflurane inhalation. | 0.31 |
| `E2E-021` | No alternative conditions were identified in the available sources. | The context only provides information about specific diseases and their symptoms, but does not provide a comprehensive list of all possible conditions. Therefore, it cannot be inferred that no alternative conditions exist. | 0.35 |
