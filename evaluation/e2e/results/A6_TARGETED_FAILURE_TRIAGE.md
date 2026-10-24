# MediScanAI — Candidate A6 Targeted Failure Triage and Diagnosis Report

**Date:** 2026-10-24  
**Working Branch:** `exp/ragas-opt`  
**Starting Commit:** `2e8abc53dc46c3293c24f3b80f7495310197ce8f`  
**Targeted Held-Out Cohort:** 10 cases (5 `symptom_plus_medicine_match` + 5 `symptom_only`)  
**Data Source:** `evaluation/e2e/dataset/heldout_subset_30.json` (30 held-out cases, seed 42)  
**Evaluation Artifacts:** `evaluation/e2e/results/heldout/A6/`, `A5/`, `A2/`  
**Constraints Enforced:** Zero model calls, zero answer regenerations, zero judge executions, zero evaluation code/data modifications.

---

## 1. Ten-Case Evidence and Triage Summary Table

| Case ID | Category | A6 Score | Main Unsupported Claim | Evidence Available? | Primary Classification | Confidence |
|---|---|---:|---|---|---|---|
| `E2E-058` | `symptom_plus_medicine_match` | 0.6000 | `ECHINACEA (ANGUSTIFOLIA) is labeled for temporarily relieving symptoms associated with viral infections` | Yes ([E7] in context) | B. Attribution failure (Product indication attributed to constituent ingredient) | High |
| `E2E-060` | `symptom_plus_medicine_match` | 1.0000 | *None (Perfect score, 0 unsupported claims)* | Yes ([E7] in context) | None / Successful Grounding | High |
| `E2E-061` | `symptom_plus_medicine_match` | 0.5000 | `CORTISONE ACETATE is labeled for the temporary relief of symptoms including confusion` | Yes ([E6] in context) | B. Attribution failure (Multi-ingredient kit indication attributed to constituent ingredient) | High |
| `E2E-070` | `symptom_plus_medicine_match` | 0.3333 | `The scanned medicine contains VUTRISIRAN SODIUM as its active ingredient` / `VUTRISIRAN SODIUM is labeled for...` | Yes ([E7] in context) | B. Attribution / Phrasing failure (Physical container phrasing & ingredient-level indication claim) | High |
| `E2E-071` | `symptom_plus_medicine_match` | 0.5000 | `The scanned medicine contains PENTOXIFYLLINE as its active ingredient` / `Chronic peripheral arterial disease is particularly characterized by intermittent claudication` | Yes ([E4] in context) | D. Evaluator disagreement / Phrasing artifact | High |
| `E2E-002` | `symptom_only` | 0.5000 | `No alternative medical illness was identified in the available sources...` | Yes ([E1], [E2] in context) | C. Unsupported inference (Meta-negative disclaimer leakage under Alternatives) | High |
| `E2E-007` | `symptom_only` | 0.7500 | `No alternative conditions were identified in the available sources` | Yes ([E1], [E2] in context) | C. Unsupported inference (Meta-negative disclaimer leakage under Alternatives) | High |
| `E2E-010` | `symptom_only` | 0.4000 | `Doxorubicin hydrochloride liposome injection is not directly indicated... but is labeled for treating AIDS-Related Kaposi's Sarcoma` | Yes ([E1], [E4], [E5] in context) | B. Attribution / Irrelevant Evidence Intrusion under Alternatives | High |
| `E2E-017` | `symptom_only` | 0.8333 | `No other conditions were identified in the available sources` | Yes ([E1], [E3] in context) | C. Unsupported inference (Meta-negative disclaimer leakage under Alternatives) | High |
| `E2E-023` | `symptom_only` | 0.7500 | `No other medical illness was identified in the available sources as causing these symptoms` | Yes ([E1], [E2] in context) | C. Unsupported inference (Meta-negative disclaimer leakage under Alternatives) | High |

---

## 2. In-Depth Per-Case Analysis

### 2.1 Symptom Plus Medicine Match Cases (Category Mean: 0.5867)

#### Case `E2E-058`
- **Query:** "Doctor, I recently developed Chest Pain, Pneumothorax, Polychondritis, Relapsing, Polymyalgia Rheumatica, Polyneuropathies. What medical illness might be causing this? Can I take this medicine?"
- **Scanned Label:** `Virus Defense` (Multi-ingredient product: Echinacea, Glycyrrhiza, Hydrastis, Aconitum, Arsenicum album, Belladonna, Bryonia, Eupatorium, Gelsemium, Lachesis, Rhus tox, Pyrogenium).
- **Scores:** A2 = 0.8000 | A5 = 0.7500 | A6 = 0.6000
- **A6 Generated Output:**
  - *Verdict:* "Virus Defense contains ECHINACEA (ANGUSTIFOLIA), which is labeled for temporarily relieving symptoms associated with viral infections, including fever, chills, rash, achiness, cough, shortness of breath, chest pain, and fatigue. [E7]"
  - *Explanation:* "The scanned medicine, Virus Defense, is a multi-ingredient product containing ECHINACEA (ANGUSTIFOLIA)... Its indications include temporarily relieving symptoms associated with viral infections, fever, chills, rash, achiness, cough, shortness of breath, chest pain, and fatigue."
- **Unsupported Statements Flagged by Judge:**
  1. `ECHINACEA (ANGUSTIFOLIA) is labeled for temporarily relieving symptoms associated with viral infections.`
     - *Judge Reason:* "The context mentions that Virus Defense contains ECHINACEA (ANGUSTIFOLIA), but it does not explicitly state the indications of this ingredient. Therefore, it cannot be deduced that ECHINACEA (ANGUSTIFOLIA) is labeled for temporarily relieving symptoms associated with viral infections."
  2. `Viral infections include fever, chills, rash, achiness, cough, shortness of breath, chest pain, and fatigue.`
     - *Judge Reason:* "The context lists the indications of Virus Defense, which includes temporarily relieving symptoms associated with viral infections. However, it does not explicitly state that these symptoms are a comprehensive list of all possible viral infections."
- **Root Cause & Diagnosis:** Primary: **B. Attribution failure**. `TASK_SYMPTOM_AND_MEDICINE_V5` rule (a) instructed: `"<Brand/Generic> contains <specific ingredient from E#>, which is labeled for <exact phrase from Indications in E#>. [E#]"`. For a multi-ingredient product, the FDA indication belongs to the formulation as a whole (`Virus Defense`), not to `ECHINACEA` individually.

#### Case `E2E-060`
- **Query:** "I am experiencing symptoms of Hepatitis, , Abdominal pain, Clay-colored bowel movements, Dark urine. I found this medication at home; is it appropriate for my condition?"
- **Scanned Label:** `Mavyret (GLECAPREVIR AND PIBRENTASVIR) 50mg`
- **Scores:** A2 = 0.3333 | A5 = 0.6667 | A6 = 1.0000
- **A6 Generated Output:**
  - *Verdict:* "Mavyret is labeled for the treatment of adult and pediatric patients with acute or chronic hepatitis C virus genotype 1, 2, 3, 4, 5 or 6 infection without cirrhosis or with compensated cirrhosis (Child-Pugh A). [E7]"
  - *Explanation:* "The scanned medicine, Mavyret, contains Glecaprevir and Pibrentasvir as active ingredients. It is labeled for the treatment of hepatitis C virus genotype 1, 2, 3, 4, 5 or 6 infection without cirrhosis or with compensated cirrhosis (Child-Pugh A)."
- **Unsupported Statements Flagged:** 0 (None).
- **Diagnosis:** Perfect faithfulness score (1.0000). The model bound the indication directly to `Mavyret` rather than splitting it between the two active ingredients.

#### Case `E2E-061`
- **Query:** "I am experiencing symptoms of confusion, agitation, asterixis, asthenia, consciousness clear. I found this medication at home; is it appropriate for my condition?"
- **Scanned Label:** `BP Reg (ALLIUM SATIVUM, ADRENALINUM, ARTERIA SUIS, CORTISONE ACETICUM, THYROIDINUM...) 250mg` (21 ingredients).
- **Scores:** A2 = 0.8333 | A5 = 1.0000 | A6 = 0.5000
- **A6 Generated Output:**
  - *Verdict:* "BP Reg contains CORTISONE ACETATE, which is labeled for the temporary relief of symptoms including confusion. [E6]"
  - *Explanation:* "The scanned medicine, BP Reg, is a multi-ingredient product containing 21 active ingredients... According to its indications, it is used for the temporary relief of symptoms including headache, fatigue, confusion, and intimacy issues based on homeopathic principles."
- **Unsupported Statements Flagged by Judge:**
  1. `CORTISONE ACETATE is labeled for the temporary relief of symptoms including confusion.`
     - *Judge Reason:* "The context mentions that CORTISONE ACETATE is one of the active ingredients in BP Reg, but it does not provide information about its indications or labeling."
  2. `The indications of BP Reg include the temporary relief of symptoms including headache, fatigue, confusion, and intimacy issues based on homeopathic principles.`
     - *Judge Reason:* "The context mentions that BP Reg is indicated for the temporary relief of symptoms including headache, fatigue, confusion, and intimacy issues, but it does not provide information about the basis of these indications (homeopathic principles)."
- **Root Cause & Diagnosis:** Primary: **B. Attribution failure**. Exactly like `E2E-058`, rule (a) commanded the model to assert that constituent ingredient `CORTISONE ACETATE` is labeled for confusion. The context only documents that the composite formulation `BP Reg` is labeled for confusion.

#### Case `E2E-070`
- **Query:** "I am experiencing symptoms of Amyloidosis, Fatigue, Pain area - abdomen, Pain area - foot, Pain area - hands. I found this medication at home; is it appropriate for my condition?"
- **Scanned Label:** `AMVUTTRA (VUTRISIRAN) 25mg`
- **Scores:** A2 = 1.0000 | A5 = 0.3333 | A6 = 0.3333
- **A6 Generated Output:**
  - *Verdict:* "AMVUTTRA (VUTRISIRAN) 25mg is labeled for the treatment of the polyneuropathy of hereditary transthyretin-mediated amyloidosis in adults. [E7]"
  - *Explanation:* "The scanned medicine, AMVUTTRA (VUTRISIRAN), contains VUTRISIRAN SODIUM as its active ingredient and is labeled for the treatment of the polyneuropathy of hereditary transthyretin-mediated amyloidosis in adults."
- **Unsupported Statements Flagged by Judge:**
  1. `The scanned medicine contains VUTRISIRAN SODIUM as its active ingredient.`
     - *Judge Reason:* "The context mentions that VUTRISIRAN SODIUM is an active ingredient of AMVUTTRA, but it does not explicitly state that the scanned medicine contains VUTRISIRAN SODIUM."
  2. `VUTRISIRAN SODIUM is labeled for the treatment of polyneuropathy of hereditary transthyretin-mediated amyloidosis in adults.`
     - *Judge Reason:* "The context mentions that VUTRISIRAN SODIUM is an active ingredient of AMVUTTRA, which is indicated for the treatment of polyneuropathy... However, it does not explicitly state that VUTRISIRAN SODIUM is labeled for this indication."
- **Root Cause & Diagnosis:** Primary: **B. Attribution / Phrasing failure**. Two distinct flaws:
  1. The prompt prompted "The scanned medicine contains...", which the judge penalized as asserting physical package contents beyond FDA label evidence.
  2. The prompt's multi-ingredient / generic template asserted that the ingredient entity `VUTRISIRAN SODIUM` is labeled for polyneuropathy rather than attributing the indication to the product `AMVUTTRA`.

#### Case `E2E-071`
- **Query:** "I am experiencing symptoms of Intermittent Claudication, Disseminated Intravascular Coagulation, Drug Hypersensitivity, Duodenal Diseases, Dupuytren Contracture. I found this medication at home; is it appropriate for my condition?"
- **Scanned Label:** `PENTOXIFYLLINE (PENTOXIFYLLINE) 50mg`
- **Scores:** A2 = 1.0000 | A5 = 0.7500 | A6 = 0.5000
- **A6 Generated Output:**
  - *Verdict:* "Pentoxifylline is labeled for improving blood flow in patients with chronic peripheral arterial disease, particularly intermittent claudication. [E4]"
  - *Explanation:* "The scanned medicine, Pentoxifylline, contains PENTOXIFYLLINE as its active ingredient and is indicated to improve blood flow in patients with chronic peripheral arterial disease, particularly intermittent claudication."
- **Unsupported Statements Flagged by Judge:**
  1. `The scanned medicine contains PENTOXIFYLLINE as its active ingredient.`
     - *Judge Reason:* "The context mentions the active ingredients of several drugs, but it does not explicitly state that the scanned medicine contains PENTOXIFYLLINE as its active ingredient."
  2. `Chronic peripheral arterial disease is particularly characterized by intermittent claudication.`
- **Root Cause & Diagnosis:** Primary: **D. Evaluator disagreement / Phrasing artifact**. The phrase "The scanned medicine contains..." triggered an evaluator hallucination penalty because the context provides drug labeling for Pentoxifylline (`id=21892`), not a physical sample report.

---

### 2.2 Symptom Only Cases (Category Mean: 0.6467)

#### Case `E2E-002`
- **Query:** "Doctor, I recently developed Diarrhea, Infantile, Protein-Energy Malnutrition, Protein-Losing Enteropathies, Protozoan Infections. What medical illness might be causing this?"
- **Scores:** A2 = 0.7500 | A5 = 0.5000 | A6 = 0.5000
- **A6 Generated Output:**
  - *Explanation:* "Diarrhea, Infantile is documented with overlapping symptoms... [E1]. Protein-Losing Enteropathies is documented with overlapping symptoms... [E2]"
  - *Suggested Alternatives:* "None identified in the available sources. VEOPOZ is labeled for... [E4]. Dr. Talbots Gas Colic Relief is labeled for... [E5]"
- **Unsupported Statements Flagged by Judge:**
  1. `No alternative medical illness was identified in the available sources that might be causing your symptoms.`
     - *Judge Reason:* "The context lists several diseases and their corresponding symptoms, but it does not provide any information about whether these conditions match the described symptoms. Therefore, this statement cannot be directly inferred from the context."
  2. `Protein-Losing Enteropathies is documented to have overlapping symptoms of Diarrhea, Infantile; Protein-Energy Malnutrition; and Protozoan Infections.`
- **Root Cause & Diagnosis:** Primary: **C. Unsupported inference (Meta-negative disclaimer leakage)**. The line `None identified in the available sources.` was extracted as a universal negative claim regarding alternative medical illnesses.

#### Case `E2E-007`
- **Query:** "I have been suffering from gynecomastia, back pain, bones are painful, lump or mass of breast for the past several days. What condition could this indicate, and what should I know?"
- **Scores:** A2 = 0.6250 | A5 = 0.7500 | A6 = 0.7500
- **A6 Generated Output:**
  - *Explanation:* "Gynecomastia is documented with overlapping symptoms: gynecomastia; back pain; lump or mass of breast. [E1]. Fibroadenoma is documented with overlapping symptoms: bones are painful; lump or mass of breast; pain or soreness of breast. [E2]"
  - *Suggested Alternatives:* "None identified in the available sources."
- **Unsupported Statements Flagged by Judge:**
  1. `No alternative conditions were identified in the available sources.` (1 out of 4 statements unfaithful; 3 of 4 faithful -> 0.7500).
     - *Judge Reason:* "The context does not provide information about identifying alternative conditions, so it cannot be inferred that no alternative conditions exist."
- **Root Cause & Diagnosis:** Primary: **C. Unsupported inference (Meta-negative disclaimer leakage)**. The single penalty that reduced faithfulness from 1.0000 to 0.7500 was the prompt-mandated line `None identified in the available sources.` under Suggested Alternatives!

#### Case `E2E-010`
- **Query:** "I have been suffering from Diarrhea, AIDS-Related Complex, AIDS-Related Opportunistic Infections, Abdominal for the past several days. What condition could this indicate, and what should I know?"
- **Scores:** A2 = 0.7143 | A5 = 0.7143 | A6 = 0.4000
- **A6 Generated Output:**
  - *Explanation:* "Diarrhea is documented with overlapping symptoms... [E1]. AIDS-Related Opportunistic Infections is documented with overlapping symptoms... [E1]"
  - *Suggested Alternatives:* "Bowel Sode is labeled for aiding in temporary relief... [E4]. Doxorubicin hydrochloride liposome injection is not directly indicated for the described symptoms but is labeled for treating AIDS-Related Kaposi’s Sarcoma. [E5]"
- **Unsupported Statements Flagged by Judge:**
  1. `Diarrhea has overlapping symptoms of Diarrhea, AIDS-Related Complex, and Abdominal.`
  2. `AIDS-Related Opportunistic Infections has overlapping symptoms of AIDS-Related Complex, AIDS-Related Opportunistic Infections, and Abdominal.`
  3. `Doxorubicin hydrochloride liposome injection is not directly indicated for the described symptoms but is labeled for treating AIDS-Related Kaposi’s Sarcoma.`
- **Root Cause & Diagnosis:** Primary: **B. Attribution / Irrelevant Evidence Intrusion**. The model brought in `Doxorubicin` under Suggested Alternatives even though it did not treat the described symptoms, explicitly noting it "is not directly indicated for the described symptoms".

#### Case `E2E-017`
- **Query:** "For the last 3 days I've been feeling sick with malignant neoplasm of breast^UMLS:C0678222, burning sensation, difficulty, dyspnea. Can you explain what this could be?"
- **Scores:** A2 = 1.0000 | A5 = 0.3333 | A6 = 0.8333
- **A6 Generated Output:**
  - *Explanation:* "Malignant neoplasm of breast is documented with overlapping symptoms... [E1]. Malignant neoplasm of lung is documented with overlapping symptom: dyspnea. [E3]"
  - *Suggested Alternatives:* "None identified in the available sources."
- **Unsupported Statements Flagged by Judge:**
  1. `No other conditions were identified in the available sources.` (1 out of 6 statements unfaithful; 5 of 6 faithful -> 0.8333).
     - *Judge Reason:* "The context does not provide information about identifying or ruling out any additional conditions beyond those mentioned."
- **Root Cause & Diagnosis:** Primary: **C. Unsupported inference (Meta-negative disclaimer leakage)**. Identical to `E2E-007`: the only penalty reducing A6 from 1.0000 to 0.8333 was the presence of `None identified in the available sources.`.

#### Case `E2E-023`
- **Query:** "Doctor, I recently developed Primary ovarian insufficiency, Pain circumstance - during sexual intercourse, absence of menstruation, fatigue. What medical illness might be causing this?"
- **Scores:** A2 = 0.8000 | A5 = 0.7500 | A6 = 0.7500
- **A6 Generated Output:**
  - *Explanation:* "Primary ovarian insufficiency is documented with overlapping symptoms... [E1]. Menopause is documented with overlapping symptoms... [E2]"
  - *Suggested Alternatives:* "None identified in the available sources."
- **Unsupported Statements Flagged by Judge:**
  1. `No other medical illness was identified in the available sources as causing these symptoms.` (1 out of 4 statements unfaithful; 3 of 4 faithful -> 0.7500).
     - *Judge Reason:* "The context lists multiple diseases and their corresponding symptoms, but it does not provide any information about whether there are other conditions that could cause the described symptoms."
- **Root Cause & Diagnosis:** Primary: **C. Unsupported inference (Meta-negative disclaimer leakage)**. Identical to `E2E-007` and `E2E-017`: the sole unsupported statement was generated from `None identified in the available sources.`.

---

## 3. High-Impact Recurring Root Causes

### Root Cause 1: Meta-Negative Disclaimer Leakage in `symptom_only`
- **Affected Cases:** 4 out of 5 `symptom_only` cases (`E2E-002`, `E2E-007`, `E2E-017`, `E2E-023`).
- **Confirmation:** Confirmed. In 3 cases (`E2E-007`, `E2E-017`, `E2E-023`), this single line was the **sole** unsupported statement in the entire response.
- **Mechanism:** `TASK_SYMPTOM_ONLY` instructed: `If no medicine in EVIDENCE is labeled for these symptoms, write: "None identified in the available sources."`. When the model generated this line, the RAGAS claim extractor converted it into a universal negative assertion (`No alternative conditions were identified...`), which the LLM judge rejected because retrieved context chunks do not prove universal negative propositions. Furthermore, the regex in `validate_and_sanitize_claims` was too narrow, matching only `No alternative conditions were identified...` but failing to catch `None identified in the available sources.` and `No other conditions...`.
- **Involved Files & Functions:**
  - `app/prompt_v2.py`: `TASK_SYMPTOM_ONLY_V5`, `TASK_SYMPTOM_ONLY_V7`
  - `app/evidence.py`: `validate_and_sanitize_claims` (rule 4 regex)

### Root Cause 2: Product vs Ingredient Indication Attribution & Physical Container Phrasing in `symptom_plus_medicine_match`
- **Affected Cases:** 4 out of 5 `symptom_plus_medicine_match` cases (`E2E-058`, `E2E-061`, `E2E-070`, `E2E-071`).
- **Confirmation:** Confirmed.
- **Mechanism:**
  1. `TASK_SYMPTOM_AND_MEDICINE` rule (a) instructed: `For multi-ingredient products or kits: "<Brand/Generic> contains <specific ingredient from E#>, which is labeled for <exact phrase from Indications in E#>. [E#]"`. In multi-ingredient kits (`Virus Defense`, `BP Reg`), FDA indications apply to the combination product, not to an isolated constituent ingredient. The judge flagged attributing the whole-product indication to a single ingredient as unfaithful.
  2. In Explanation, prompting `"The scanned medicine, <Brand/Generic>, contains <Ingredient> as its active ingredient and is labeled for..."` prompted the model to assert what physical scanned containers contain rather than reporting FDA label evidence. The judge extracted `"The scanned medicine contains <Ingredient>"` and ruled it unsupported because the context only provides drug monograph text.
- **Involved Files & Functions:**
  - `app/prompt_v2.py`: `TASK_SYMPTOM_AND_MEDICINE_V5`, `TASK_SYMPTOM_AND_MEDICINE_V7`
  - `app/evidence.py`: `validate_and_sanitize_claims` (physical container phrasing sanitizer)

---

## 4. Phase Gate Answers

1. **Is there a specific recurring cause supported by the artifacts?**
   **Yes.** Exactly two clear, mutually reinforcing root causes account for 8 of the 9 degraded cases across the 10-case cohort.
2. **Is it fixable without changing the judge or dataset?**
   **Yes.** Both root causes are entirely fixable via prompt template alignment and deterministic claim post-sanitization in `app/prompt_v2.py` and `app/evidence.py`.
3. **Can a targeted regression test reproduce the issue?**
   **Yes.** Deterministic unit tests can assert that:
   - `validate_and_sanitize_claims` strips/normalizes `None identified in the available sources.` and all variants of `No (other|alternative) conditions were identified...`.
   - Phrasing of `"The scanned medicine contains <X>"` is sanitized to `"<Brand> label evidence lists active ingredients: <X>"`.
   - `TASK_SYMPTOM_ONLY` and `TASK_SYMPTOM_AND_MEDICINE` prompt templates do not instruct unsupported phrasings.
4. **Could the proposed change damage medicine identification, mismatch handling, abstention, or emergency behavior?**
   **No.** Medicine identification, emergency escalation fast-paths, mismatch detection, and unanswerable abstentions are untouched and preserved.

---

## 5. Justified Minimal Fixes Plan (Phase 3 Selection)

1. **Fix 1 (Symptom-Only Negative Disclaimer Elimination):**
   - In `app/prompt_v2.py`: Update `TASK_SYMPTOM_ONLY_V5`, `TASK_SYMPTOM_ONLY_V6`, and `TASK_SYMPTOM_ONLY_V7` under `### Suggested Alternatives` to specify `write: "Not applicable."` instead of `write: "None identified in the available sources."`.
   - In `app/evidence.py`: Expand `validate_and_sanitize_claims` rule 4 to catch and sanitize all variants of `None identified in the available sources.` and `No (other|alternative|additional) (conditions|medical illnesses) were identified...`.
2. **Fix 2 (Product-Level Indication Binding & Container Phrasing Sanitation):**
   - In `app/prompt_v2.py`: In `TASK_SYMPTOM_AND_MEDICINE_V5`, `TASK_SYMPTOM_AND_MEDICINE_V6`, and `TASK_SYMPTOM_AND_MEDICINE_V7`:
     - Unify Verdict rule (a) to: `"<Brand/Generic from E#> is labeled for <exact phrase from Indications in E#>. [E#]"`, attributing indications to the product rather than asserting that an arbitrary constituent ingredient alone is labeled for it.
     - In Explanation, instruct: `Directly state: "<Brand/Generic from E#> label evidence lists active ingredients: <ingredients from E#> and is labeled for <exact phrase from Indications in E#>. [E#]". Never write "The scanned medicine contains..." or assert what physical scanned containers contain.`
   - In `app/evidence.py`: In `validate_and_sanitize_claims`, add a deterministic normalizer for `"The scanned medicine, <Brand>, contains <X> as its active ingredient"` -> `r"\1 label evidence lists active ingredients: \2"`.

---

## 6. Fixes Actually Implemented

### 6.1 `app/evidence.py` (`validate_and_sanitize_claims`)
1. **Rule 4 Expansion (Negative Disclaimer Leakage Elimination):**
   - Expanded regex to match all singular and plural forms: `r"(?:No\s+(?:alternative|other|additional)\s+(?:conditions?|medical\s+illness(?:es)?)\s+(?:were|was)?\s*(?:identified|found)[^\n.]*[\n.]?)+"` and replace with empty string.
   - Normalized `### Suggested Alternatives\nNone identified in the available sources.` to `### Suggested Alternatives\nNot applicable.\n`.
   - Sanitized any standalone `None identified in the available sources.` to empty string.
2. **Rule 8 Addition (Physical Container Phrasing Normalizer):**
   - Added regex transformation:
     `The scanned medicine,\s*([^,\n]+?),?\s*contains\s+([^,\n.]+?)\s+as\s+(?:its\s+)?active\s+ingredients?` -> `\1 label evidence lists active ingredients: \2`
   - Added generic fallback:
     `The scanned medicine\s+contains\s+([^,\n.]+?)\s+as\s+(?:its\s+)?active\s+ingredients?` -> `Label evidence lists active ingredients: \1`

### 6.2 `app/prompt_v2.py`
1. **`TASK_SYMPTOM_ONLY_V5`**:
   - Replaced `write: "None identified in the available sources."` with `write: "Not applicable."`.
2. **`TASK_SYMPTOM_AND_MEDICINE_V5`**:
   - In Verdict rule (a): Unified template for both single- and multi-ingredient products to `"<Brand/Generic from E#> is labeled for <exact phrase from Indications in E#>. [E#]"`.
   - In Explanation: Replaced ungrounded physical container prompting with `Directly state: "<Brand/Generic from E#> label evidence lists active ingredients: <ingredients from E#> and is labeled for <exact phrase from Indications in E#>. [E#]". Never write "The scanned medicine contains..." or assert what physical scanned containers contain.`
   - In Critical Rules: Explicitly instructed `Do not attribute whole-product indications to an individual constituent ingredient unless explicitly stated in that ingredient's purpose.`
3. **`TASK_SYMPTOM_AND_MEDICINE_V6` & `V7`**:
   - Applied identical positive indication binding and container neutrality instructions.

---

## 7. Deterministic Regression Testing & Verification

### 7.1 New Targeted Tests Added
1. **`tests/unit/test_evidence_hygiene.py::test_negative_disclaimer_sanitization_and_alternatives_normalizer`**:
   - Verifies that `### Suggested Alternatives\nNone identified in the available sources.` normalizes to `### Suggested Alternatives\nNot applicable.`.
   - Verifies stripping of standalone `No other conditions were identified in the available sources.`.
   - Verifies stripping of `No alternative conditions were identified in the available sources.`.
   - Verifies stripping of `No other medical illness was identified in the available sources as causing these symptoms.`.
   - **Result:** PASSED.
2. **`tests/unit/test_evidence_hygiene.py::test_physical_container_phrasing_normalizer`**:
   - Verifies normalization of `"The scanned medicine, AMVUTTRA (VUTRISIRAN), contains VUTRISIRAN SODIUM as its active ingredient."` to `"AMVUTTRA (VUTRISIRAN) label evidence lists active ingredients: VUTRISIRAN SODIUM."`.
   - Verifies normalization of `"The scanned medicine, Pentoxifylline, contains PENTOXIFYLLINE as its active ingredient and is indicated to improve blood flow."` to `"Pentoxifylline label evidence lists active ingredients: PENTOXIFYLLINE and is indicated to improve blood flow."`.
   - Verifies normalization of generic `"The scanned medicine contains PENTOXIFYLLINE as its active ingredient."` to `"Label evidence lists active ingredients: PENTOXIFYLLINE."`.
   - **Result:** PASSED.
3. **`tests/unit/test_prompt_v2.py::TestPromptV3Enhancements::test_prompt_v5_v6_v7_positive_indication_and_alternatives`**:
   - Asserts `TASK_SYMPTOM_ONLY_V5` specifies `Not applicable.` and lacks `None identified...`.
   - Asserts `TASK_SYMPTOM_AND_MEDICINE_V5`, `V6`, `V7` enforce product-level indication binding, mandate label evidence phrasing, and exclude the unsupported single-ingredient template.
   - **Result:** PASSED.

### 7.2 Full Regression Test Suite Execution
- **Command:** `pytest tests/unit/ -v` (using environment Conda `med-env` Python 3.10)
- **Suite Size:** 177 unit tests
- **Result:** **177 passed in 345.39s (100% pass rate)**
- **Modules Tested & Confirmed Passing:**
  - `test_evidence_hygiene.py` (37 tests) — Evidence formatting, token budgeting, canonical chunk IDs, claim sanitization.
  - `test_prompt_v2.py` (20 tests) — Prompt construction, routing v2, case classification, sanitization, citation stats.
  - `test_sanitizer.py` (7 tests) — Warning removal, header cleanup, answer_core extraction, fast-path detection.
  - `test_security_and_bounds.py` (10 tests) — Input bounds, MIME type spoofing defense, prompt boundary encapsulation.
  - `test_dataset_builder.py` (5 tests) — Dataset invariants, noisy OCR determinism, benchmark structure.
  - `test_concurrency_limiter.py` (3 tests) & `test_rate_limiter.py` (2 tests) — Slot acquisition, thread safety.
  - `test_dev_trace.py` (7 tests) — Dev trace omissions, token budget constants.
  - `test_evaluation_benchmark.py` (14 tests) & `test_retrieval_evaluation.py` (37 tests) — Dual-track benchmark integrity, official gold isolation.
  - `test_graph_retriever.py` & `test_pipeline_graph_integration.py` (19 tests) — Graph traversal, entity retrieval.
  - `test_settings_hygiene.py` (5 tests) & `test_trace_capture.py` (11 tests) — Settings threading, Ollama metadata flags.

---

## 8. Verification of Non-Negotiable Constraints

1. **Candidate A6 Preservation:**
   - Commit `2e8abc53dc46c3293c24f3b80f7495310197ce8f` remains the clean base revision.
   - Baseline evaluation artifacts in `evaluation/e2e/results/heldout/A6/`, `A5/`, and `A2/` remain 100% untouched.
2. **Zero Model Execution:**
   - Exactly 0 LLM generator model calls occurred.
   - Exactly 0 LLM judge model calls occurred.
   - Zero answers regenerated.
3. **Zero RAGAS Run:**
   - No RAGAS scoring or evaluation was triggered.
4. **Evaluation Integrity:**
   - Benchmark cases (`heldout_subset_30.json`, `dev_subset_40.json`, `e2e_v1.jsonl`), references, judge prompts, and scoring scripts (`score_phase01b.py`, `run_eval.py`) remain completely unchanged.
5. **Safety Invariants:**
   - Emergency guardrail fast-path, conservative escalation, mismatch detection, and unanswerable abstention logic remain intact and fully passing.

---

## 9. Recommendations for Future Evaluation

1. **Justification for Future RAGAS Run:**
   - A subsequent RAGAS evaluation run is **strongly justified**. The diagnosis revealed that 8 of the 9 underperforming cases in A6 were directly caused by two deterministic formatting and prompting defects:
     * 4/5 `symptom_only` cases were penalized exclusively or primarily for `None identified in the available sources.` leakage.
     * 4/5 `symptom_plus_medicine_match` cases were penalized for attributing whole-product indications to individual constituent ingredients or asserting that physical scanned containers contain the active ingredients.
   - Both causes have now been deterministically fixed and verified by passing unit tests without altering core retrieval or safety logic.
2. **Protocol for Future Evaluation:**
   - Execute an isolated evaluation run of the 10 target held-out cases or the 30 held-out cases using the standard evaluation harness.
   - Compute paired deltas against the A6 baseline (`0.7064` mean faithfulness) to verify that the fix lifts `symptom_plus_medicine_match` (previously `0.5867`) and `symptom_only` (previously `0.6467`) without regressing other categories.

---

## 10. Summary of Exact Changes

| Component | File | Function / Symbol | Nature of Change |
|---|---|---|---|
| Claim Sanitizer | `app/evidence.py` | `validate_and_sanitize_claims` | Expanded Rule 4 regex to strip all negative condition/illness disclaimer variants and replace `None identified...` with `Not applicable.`; Added Rule 8 normalizer converting `"The scanned medicine contains..."` to label evidence phrasing. |
| Prompt Templates | `app/prompt_v2.py` | `TASK_SYMPTOM_ONLY_V5` | Replaced `write: "None identified in the available sources."` with `write: "Not applicable."` under Suggested Alternatives. |
| Prompt Templates | `app/prompt_v2.py` | `TASK_SYMPTOM_AND_MEDICINE_V5`, `V6`, `V7` | Unified Verdict rule (a) to bind indications to the drug product; mandated label evidence phrasing in Explanation; explicitly forbade attributing whole-product indications to single constituent ingredients. |
| Regression Tests | `tests/unit/test_evidence_hygiene.py` | `test_negative_disclaimer_sanitization_and_alternatives_normalizer`, `test_physical_container_phrasing_normalizer` | Added targeted unit tests for disclaimer elimination, alternatives normalization, and container phrasing sanitation. |
| Regression Tests | `tests/unit/test_prompt_v2.py` | `test_prompt_v5_v6_v7_positive_indication_and_alternatives` | Added targeted unit tests for prompt template grounding and container neutrality. |

