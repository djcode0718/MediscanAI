# MediScanAI — Cycle A6 Failure Analysis (A5 Residual Defect Taxonomy)

**Date:** 2026-10-23  
**Evaluator:** `SELF-JUDGED (llama3.1:8b)` TraceableFaithfulness  
**Input:** `evaluation/e2e/results/A5/unsupported_statements.jsonl` (40 unsupported statements across 19 cases)  

---

## 1. Executive Summary & Root Cause Distribution

A5 reduced unsupported statements from 52 to 40 (-23.1%) and achieved 0.7538 mean faithfulness. The remaining 40 unsupported statements group cleanly into 4 distinct architectural and generation failure modes:

| Failure Mode | Statements | % of A5 Defect | Primary Affected Cases | Root Cause Mechanism |
|---|---:|---:|---|---|
| **A. Unanchored Narrative & Word-Choice Leaps** | 12 | 30.0% | `E2E-001`, `E2E-008`, `E2E-009`, `E2E-024`, `E2E-025`, `E2E-069` | Model uses additive narrative connectors ("also includes", "are consistent with") or asserts symptoms from adjacent disease chunks not present in cited record. |
| **B. Negative Entity Assertions & Probing** | 14 | 35.0% | `E2E-091`, `E2E-094`, `E2E-097`, `E2E-099`, `E2E-100`, `E2E-004`, `E2E-021` | Model states negative abstention by echoing probe entity names or declaring "No alternative conditions were found", which the judge scores as unsupported since the entity/rule is absent from context. |
| **C. Inverse Negative Symptom Enumeration** | 4 | 10.0% | `E2E-080`, `E2E-081` | Model lists symptoms the drug *does not* treat ("does not include depression, headache, irritability"). Judge rejects these as context does not mention depression in relation to Neomycin. |
| **D. Cross-Field Entity & Attribute Contamination** | 10 | 25.0% | `E2E-034`, `E2E-041`, `E2E-062`, `E2E-072`, `E2E-082` | Product attributes (prescription status, whole kit vs sub-ingredient purpose, unverified indication phrases) asserted beyond exact evidence text. |

---

## 2. Deep Dive by Selected Representative Failure Cases

### Case 1: `E2E-001` (Symptom Only) — 5 Unsupported Statements
- **Query:** Patient presents with chest pain, dizziness, shortness of breath, palpitations.
- **Generated Claims Flagged:**
  1. `Coronary Atherosclerosis also includes dizziness.` (Judge: context lists dizziness, but "also" implies extraneous unstated info).
  2. `Coronary Atherosclerosis also includes fatigue.`
  3. `Atrial Fibrillation includes Chest pain or discomfort.`
  4. `Atrial Fibrillation also includes dizziness or lightheadedness.`
  5. `Atrial Fibrillation also includes fatigue.`
- **Retrieved Evidence [E1, E2]:**
  - `[E1] Coronary Atherosclerosis: chest pain, dizziness, fatigue, shortness of breath...`
  - `[E2] Atrial Fibrillation: palpitations, chest pain, dizziness, fatigue...`
- **Why Pipeline Allowed It:** The prompt asked the model to explain each condition by listing its documented symptoms. The generator generated repetitive conversational sentences with "also includes".
- **A6 Correction:** Constrain symptom-only explanation to strict, bounded claim structures:
  `"<Condition> is documented with overlapping symptoms: <sym1>, <sym2>. [E#]"`. Prohibit conversational modifiers ("also includes", "further presents with").

### Case 2: `E2E-080` (Mismatch) — 3 Unsupported Statements
- **Query:** Patient with headache, irritability, depression asking about Neomycin/Polymyxin/Bacitracin ointment.
- **Generated Claims Flagged:**
  1. `The indications on the label of the medicine Neomycin and Polymyxin B Sulfates and Bacitracin Zinc do not include treating depression.`
  2. `The indications on the label of the medicine Neomycin and Polymyxin B Sulfates and Bacitracin Zinc do not include treating headache.`
  3. `The indications on the label of the medicine Neomycin and Polymyxin B Sulfates and Bacitracin Zinc do not include treating irritability.`
- **Retrieved Evidence [E1]:**
  - `[E1] Neomycin and Polymyxin B Sulfates: first aid to help prevent infection in minor cuts, scrapes, and burns.`
- **Why Pipeline Allowed It:** Prompt v4 instructed the model to explain mismatches by contrasting indications with user symptoms. The model generated explicit negative assertions about depression, which the judge penalizes because the string "depression" does not exist in [E1].
- **A6 Correction:** Prohibit listing what a medicine *does not* treat. Require a positive statement of what the medicine *is* indicated for, followed by a bounded mismatch statement:
  `"Verdict: The medicine does not match your symptoms. [E1]\nExplanation: Neomycin and Polymyxin B is labeled for first aid in minor cuts, scrapes, and burns [E1], which does not cover your presented symptoms."`

### Case 3: `E2E-034` (Medicine Only Clean OCR) — 2 Unsupported Statements
- **Query:** Analyze ANTICHOLIUM.
- **Generated Claims Flagged:**
  1. `ANTICHOLIUM is used to treat amantadine and diphenhydramine.`
  2. `ANTICHOLIUM is used to treat baclofen and 4-hydroxybutyric acid (GHB).`
- **Retrieved Evidence [E1]:**
  - ANTICHOLIUM (Physostigmine salicylate) label discusses severe anticholinergic syndrome. In warnings/background, it lists diverse intoxicants, but its actual indication is physostigmine reversal of anticholinergic toxicity.
- **Why Pipeline Allowed It:** The generator extracted toxic agents mentioned in the warning/background text and transformed them into direct indication assertions.
- **A6 Correction:** Ensure indication statements strictly use the text from the `indications:` field and explicitly quote or closely paraphrase the labeled use without inferring off-label efficacy.

### Case 4: `E2E-041` (Medicine Only Noisy OCR) — 3 Unsupported Statements
- **Query:** OCR text `Glibenclarnide` (noisy for Glibenclamide / Glyburide).
- **Generated Claims Flagged:**
  1. `The label text identifies Glibenclarnide.` (Judge: Glibenclarnide is absent from context).
  2. `The active ingredients of Glibenclarnide include ALLOPURINOL is not stated in the available sources.`
  3. `Allopurinol tablets, USP reduces serum and urinary uric acid concentrations.`
- **Why Pipeline Allowed It:** The model echoed the corrupted OCR string `Glibenclarnide` as a verified medical product identity and then generated negative claims about Allopurinol.
- **A6 Correction:** When OCR text does not match any retrieved drug name with exact token overlap, the model must refer to the product by its candidate retrieved brand name or generic name, or state: `"The scanned label text could not be verified against the available medication records."`

### Case 5: `E2E-091`, `E2E-094`, `E2E-100` (Unanswerable Probes) — 7 Unsupported Statements
- **Query:** Probes asking for fictitious medications (`NonexistentDrugZ`, `Xanthroflurane`, `Glycozempra`).
- **Generated Claims Flagged:**
  - `NonexistentDrugZ 500mg tablets were not mentioned in any available sources.`
  - `Available sources do not provide information about official FDA pediatric approval date for Xanthroflurane.`
- **Why Pipeline Allowed It:** The model repeated the fictitious query entity in a negative claim.
- **A6 Correction:** Universal entity-neutral abstention format for unanswerable probes:
  `"Verdict: The requested information cannot be established from the available evidence.\nExplanation: The medication details are not present in the available sources."`

---

## 3. Actionable Code Changes for Cycle A6

1. **Claim-Level Grounding & Verification in `app/prompt_v2.py` (Prompt v5):**
   - Introduce strict atomic claim framing for all 4 intents (`SYMPTOM_ONLY`, `MEDICINE_ONLY`, `SYMPTOM_AND_MEDICINE`, `UNANSWERABLE`).
   - Eliminate repetitive narrative connectors ("also includes", "additionally features").
   - Replace negative symptom enumeration with positive indication framing + bounded mismatch verdict.
   - Prohibit echoing unverified probe entities in negative assertions.
2. **Deterministic Claim & Citation Validator in `app/evidence.py`:**
   - Add `validate_claim_citations(raw_response, available_evidence_tags)` to verify every cited tag `[E#]` matches an existing evidence block.
   - Verify that citations attach directly to factual sentences, preventing orphan citations or trailing tag dumps.
3. **Traceability Extraction in `app/core.py`:**
   - Thread validated claim-level grounding and clean citation checks into the generation result trace.
