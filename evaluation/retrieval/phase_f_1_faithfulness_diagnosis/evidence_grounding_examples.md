# Phase F.1 — Evidence Grounding & Failure Case Studies

## Executive Summary

This document provides concrete clinical and linguistic case studies from the Phase C.4 baseline response cohort, classifying factual statements according to the 6-tier evidence grounding taxonomy and illustrating the primary mechanisms driving low RAGAS Faithfulness scores (0.5835).

> [!NOTE]
> **Provisional Diagnostic Assessment:** All claim dissections and root-cause attributions presented in this report represent provisional engineering analyses based on deterministic pattern matching and LLM-as-a-judge audits. They do not constitute certified clinical trial adjudications.

---

## 1. The 6-Tier Evidence Grounding Taxonomy

Every statement extracted from generated responses was classified into one of six evidence relationships:

| Tier | Category Name | Definition | Example from Benchmark |
| :---: | :--- | :--- | :--- |
| **1** | **Directly Supported** | Verbatim or exact semantic identity with retrieved context chunks. | Context: `Brand: Advil; Generic: IBUPROFEN`<br>Claim: *"Advil is a brand of Ibuprofen."* |
| **2** | **Supported through Inference** | Logically necessitated by context data without injecting external facts. | Context: `[drug_1] Brand: Lipitor; Generic: Atorvastatin`<br>Claim: *"Lipitor contains the same generic agent as other Atorvastatin formulations."* |
| **3** | **Partially Supported / Overgeneralized** | Core entity is in context, but properties are broadened beyond evidence. | Context: `Substances: [ATORVASTATIN CALCIUM TRIHYDRATE]`<br>Claim: *"Atorvastatin is available in multiple unspecified salt forms."* |
| **4** | **Unsupported by Context** | Plausible or true clinical facts injected from model parametric memory, or legal disclaimers. | Context: `Generic: IBUPROFEN`<br>Claim: *"It is a non-steroidal anti-inflammatory drug used to reduce fever."* |
| **5** | **Contradicted by Context** | Directly conflicts with retrieved evidence facts. | Context: `Generic: Cinnarizine`<br>Claim: *"Cinzan contains paracetamol as its active ingredient."* |
| **6** | **Not Assessable** | Malformed evidence, unparseable chunk, or empty retrieval. | Context: Empty or corrupted string. |

---

## 2. In-Depth Case Studies

---

### Case Study 1: Evaluation Judge Artifact — The "Disclaimer Penalty"
**Case ID:** `MED-BENCH-004`  
**Query:** `Advil`  
**Category:** `drug_brand_lookup`  
**Reported RAGAS Faithfulness:** `0.3750` (3 / 8 statements supported)  
**True Core Factual Faithfulness:** `1.0000` (100% of medical claims supported)

#### Retrieved Evidence Context:
```text
* [drug_58277] Rank 1 (score: 5.3003): Brand: Advil; Generic: IBUPROFEN; Substances: [IBUPROFEN]
* [drug_61074] Rank 2 (score: 5.2137): Brand: Advil; Generic: IBUPROFEN SODIUM; Substances: [IBUPROFEN SODIUM]
* [drug_9884] Rank 3 (score: 5.0958): Brand: Advil; Generic: IBUPROFEN TABLETS, COATED; Substances: [IBUPROFEN]
```

#### Generated Baseline Response:
```markdown
**Factual Summary**

The user query is about "Advil". Based on the retrieved evidence context, Advil is a brand name associated with several generic and substance entries. The top-ranked entry ([drug_58277]) indicates that Advil is a brand of Ibuprofen.

### ⚠️ Important Warning
This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition.
```

#### Claim-by-Claim Evidence Decomposition:
| # | Section | Claim Statement | Evidence Status | Verdict |
| :---: | :--- | :--- | :--- | :---: |
| 1 | Body | *"The user query is about Advil."* | Directly Supported | ✅ Supported |
| 2 | Body | *"Advil is a brand name associated with several generic and substance entries."* | Directly Supported | ✅ Supported |
| 3 | Body | *"The top-ranked entry indicates that Advil is a brand of Ibuprofen."* | Directly Supported | ✅ Supported |
| 4 | Disclaimer | *"This analysis is for informational purposes only."* | Unsupported by Context (Zero evidence in drug DB) | ❌ Unsupported |
| 5 | Disclaimer | *"It is generated based on the data you provided."* | Unsupported by Context | ❌ Unsupported |
| 6 | Disclaimer | *"It is not a substitute for professional medical advice."* | Unsupported by Context | ❌ Unsupported |
| 7 | Disclaimer | *"You should always consult a qualified doctor or pharmacist."* | Unsupported by Context | ❌ Unsupported |
| 8 | Disclaimer | *"Consult to determine the best course of treatment for your specific condition."* | Unsupported by Context | ❌ Unsupported |

#### Diagnosis:
The generator was 100% faithful in answering the medical question. However, RAGAS evaluated the entire output text string, including the 47-word mandatory legal disclaimer. Because the retrieved clinical chunks describe drug entities rather than legal disclaimers, the judge penalized all 5 disclaimer sentences as "hallucinations", capping the score at **0.3750**.

---

### Case Study 2: Parametric Model Prior Hallucination
**Case ID:** `MED-BENCH-013`  
**Query:** `Paracetamol`  
**Category:** `active_ingredient_lookup`  
**Reported RAGAS Faithfulness:** `0.2857` (2 / 7 statements supported)

#### Retrieved Evidence Context:
```text
* [drug_47716] Rank 1 (score: 9.3881): Brand: Paracetamol; Generic: PARACETAMOL; Substances: [PARACETAMOL]
* [drug_26955] Rank 2 (score: 9.3881): Brand: Paracetamol; Generic: PARACETAMOL; Substances: [PARACETAMOL]
```

#### Generated Baseline Response:
```markdown
<USER_QUERY>
Paracetamol
</USER_QUERY>

Based on the retrieved evidence context, Paracetamol is an active ingredient and generic medication. It is commonly used as an analgesic and antipyretic to relieve mild to moderate pain and reduce fever. Multiple brand formulations exist in the database.

### ⚠️ Important Warning
... [Mandatory Warning Text] ...
```

#### Claim-by-Claim Evidence Decomposition:
| # | Claim Statement | Evidence Status | Root Cause |
| :---: | :--- | :--- | :--- |
| 1 | *"Paracetamol is an active ingredient and generic medication."* | Directly Supported | Retrieved Chunk |
| 2 | *"It is commonly used as an analgesic and antipyretic..."* | **Unsupported by Context** | **Model Prior Leakage** (Database has no indication fields) |
| 3 | *"...to relieve mild to moderate pain and reduce fever."* | **Unsupported by Context** | **Model Prior Leakage** |
| 4 | *"Multiple brand formulations exist in the database."* | Supported by Inference | Retrieved Chunk Count |
| 5–7| Disclaimer statements | Unsupported by Context | Disclaimer Penalty |

#### Diagnosis:
While clinically accurate in real-world medicine, the concepts *"analgesic"*, *"antipyretic"*, *"pain relief"*, and *"reduce fever"* are **completely absent** from the database chunk. The model relied on its pre-trained parametric knowledge instead of strictly adhering to the evidence-only constraint.

---

### Case Study 3: The Negative Control / Unanswerable Dilemma
**Case ID:** `MED-BENCH-041`  
**Query:** `NonexistentDrugZ 500mg dosage and administration`  
**Category:** `insufficient_evidence_unanswerable`  
**Reported RAGAS Faithfulness:** `0.1667` (1 / 6 statements supported)

#### Retrieved Evidence Context:
```text
* [drug_39372] Rank 1 (score: -1.1118): Brand: Acetaminophen 500mg ES; Generic: ACETAMINOPHEN 500MG
* [drug_52207] Rank 2 (score: -3.4468): Brand: Methocarb 500-EZS; Generic: METHOCARBAMOL
* [disease_chunk_2396] Rank 6 (score: -11.0037): Disease: Purpura, Thrombocytopenic
```

#### Generated Baseline Response:
```markdown
<USER_QUERY>
NonexistentDrugZ 500mg dosage and administration
</USER_QUERY>

Unfortunately, there is no information in the retrieved evidence context about a drug called "NonexistentDrugZ". The available evidence does not support an answer to this query.

### ⚠️ Important Warning
... [Mandatory Warning Text] ...
```

#### Diagnosis:
The model executed a textbook **pure abstention**, refusing to hallucinate information for a fabricated drug. However:
1. The judge parsed *"there is no information about NonexistentDrugZ"* as 1 supported negative claim.
2. The judge parsed the 5 disclaimer sentences as unsupported claims.
3. RAGAS calculated $1 / 6 = \mathbf{0.1667}$.
This creates a perverse incentive: an optimal clinical abstention is severely penalized as an unfaithful response.

---

### Case Study 4: Hallucinated Bridging in Fabricated Queries
**Case ID:** `MED-BENCH-042`  
**Query:** `Treatment protocol for acute Martian respiratory syndrome`  
**Category:** `insufficient_evidence_unanswerable`  
**Reported RAGAS Faithfulness:** `0.3333`

#### Retrieved Evidence Context:
```text
* [drug_69023] Rank 1 (score: -5.47): Brand: Curosurf; Generic: PORACTANT ALFA
* [drug_23983] Rank 2 (score: -7.97): Brand: MARS WELLNESS MAGNESIUM; Generic: MENTHOL
* [disease_chunk_3150] Rank 6 (score: -3.98): Disease: acute respiratory distress syndrome (ards)
```

#### Generated Baseline Response:
```markdown
The top-ranked substance is PORACTANT ALFA (Curosurf), which is used for treating acute respiratory distress syndrome (ARDS) (disease_chunk_3150). Another relevant treatment is MENTHOL (MARS WELLNESS MAGNESIUM)... However, the available evidence does not provide a specific treatment protocol for "acute Martian respiratory syndrome."
```

#### Diagnosis:
Unlike `MED-BENCH-041`, the model failed to abstain cleanly. Distracted by top-k negative score noise containing keyword overlaps (*"MARS"* and *"respiratory"*), the model hallucinated a clinical relationship between `Curosurf` and `ARDS`, neither of which was asserted in the retrieved chunks.

---

## 3. Required Evidence to Support Failed Claims

To achieve 1.0000 true evidence grounding without relying on model memory, the retrieval system or generator would require:

1. **Structured Drug Metadata Fields:** When users query drug indications or mechanisms, the retriever must supply explicit `Indications: [...]` and `MechanismOfAction: [...]` chunks. If such chunks do not exist in the database, the generator must explicitly state: *"Database records active ingredients only; indication data is not documented in evidence."*
2. **Explicit Disclaimer Decoupling:** General legal disclaimers and safety notices must be decoupled from the factual response payload evaluated by RAGAS.
3. **Strict Negative Abstention Prompts:** When maximum retrieval similarity is below threshold (e.g. negative scores), the model must emit an atomic abstention token without hallucinating connections to distractor chunks.
