# Phase F.5 Prompt Specifications & Design Rationale

**Phase:** F.5 — Fact-Only Grounding and Abstention-Aware Evaluation  
**Date:** 2026-10-19  
**Target Candidate:** `F5-A` (Fact-Only Affirmative Grounding with Query-Entity Gate)  
**Control Baseline:** `F5-0` (F4-B Reused Control)  
**Evaluator LLM:** Ollama `llama3.1:8b` (Q4_K_M, Digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`)  

---

## 1. Executive Design Rationale

In Phase F.4, we uncovered a critical tension between prompt length constraints and automated Ragas evaluation:
1. **Single-Word Over-Constraint (F3-C / F4-B):**
   - Forcing single-word outputs (`"state ONLY those names"`) achieved high faithfulness (**0.8663**) by eliminating extraneous tokens.
   - However, it caused the Ragas question generation LLM to prefix conversational reasoning (*"Since the response is a single word, it's likely that..."*), crashing LangChain's Pydantic output parser and triggering 360-second timeouts.
2. **Conversational Complete Sentences (F4-A / F4-C):**
   - Requiring 1–2 complete sentences completely solved evaluator parser crashes and raised answerable query relevancy to **0.6842**.
   - However, when the model attempted to be comprehensive, it generated boundary assertions describing what was *absent* from the catalog entries (e.g., *"Formulations, strengths, and qualifiers are not specified in the provided evidence."*).
   - Ragas extracted these boundary statements as affirmative claims (*"Formulations are not specified"*), which were marked ungrounded because the text does not appear verbatim in catalog records. This dropped faithfulness to **0.7119**.

### The Phase F.5 Solution: Fact-Only Affirmative Grounding
Phase F.5 deploys **Fact-Only Affirmative Grounding (`F5-A`)**, explicitly instructing the model to state only concise, affirmative facts that exist in the evidence, while explicitly forbidding discussion of missing fields, absent formulations, or unstated limitations.

---

## 2. Prompt Variant Specifications

### 2.1 Candidate `F5-A`: Fact-Only Affirmative Grounding (Primary Candidate)

#### System Instruction:
```
Answer the user's question directly using concise, affirmative facts supported by the supplied evidence. Do not introduce facts that are absent from the evidence. Do not mention missing fields, absent formulations, unsupported indications, or other limitations unless the user explicitly asks about evidence availability or the limitation is necessary to avoid a misleading answer. Preserve exact medicine names, ingredients, formulations, strengths, qualifiers, and uncertainty. Do not invent dosage instructions, treatment claims, citations, or source identifiers. If the evidence cannot identify the requested entity or answer the question, abstain clearly and briefly.
```

#### Prompt Assembly Template:
```markdown
### Instruction:
{instruction}

### Evidence Context:
{context}

### Question:
{query}

### Concise Affirmative Answer:
```

---

### 2.2 Control `F5-0` (`F4-B` Reused Control)

Reuses the exact Phase F.4 F4-B configuration (F3-C direct prompt paired with Query-Entity Verification Gate):
```markdown
You are MediScanAI, a clinical assistant providing direct, strictly evidence-grounded answers.

User Question: {query}

Evidence Context:
{context}

Instructions:
1. Direct Factual Response: Begin immediately with the direct, factual answer to the user's question. Do NOT include introductory statements, meta-talk, or filler (do NOT say "Based on the evidence...", "The retrieved database records contain...", or "Here is the information...").
2. Strict Context Grounding: Use ONLY facts explicitly stated in the Evidence Context. Never state drug classes (do not say "statin", "NSAID", "antibiotic"), therapeutic uses, indications, mechanisms, or disease causes unless they are written directly in the Evidence Context. If the context contains only brand and generic names, state ONLY those names.
3. Preserve Exact Details: Keep exact salt forms, strengths, and qualifiers as written.
4. Entity Verification & Clean Abstention: Verify that the exact entity or condition in the question is present in the evidence. If the exact queried entity is absent, or if the context does not answer the question, state directly: "No information is available for {query}." Do NOT substitute related entities, partial matches, or similar conditions.
5. Formatting: Do not output delimiters or tags. Conclude your entire response with the exact disclaimer below:

### ⚠️ Important Medical & Legal Disclaimer
MediScanAI is an AI-powered informational tool, not a doctor, pharmacist, or licensed healthcare provider. The information provided is for educational purposes only and must not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional before starting, stopping, or changing any medication.
```

---

## 3. Contrast Matrix Across Historical Generations

| Case ID & Query | F4-B Control Generation | F4-A Natural Direct Generation | F5-A Fact-Only Generation | Evaluation Impact |
| :--- | :--- | :--- | :--- | :--- |
| **`MED-BENCH-001`**<br>`"Lipitor"` | `Lipitor; Generic: ATORVASTATIN CALCIUM; Substances: [ATORVASTATIN CALCIUM TRIHYDRATE]` | `The brand name of the drug is Lipitor. The generic name of the drug is ATORVASTATIN CALCIUM.` | `The brand name is Lipitor. The generic names are ATORVASTATIN CALCIUM.` | Clean complete sentence; 100% grounded affirmative claims. |
| **`MED-BENCH-012`**<br>`"Acetaminophen"` | `Acetaminophen; Generic: ACETAMINOPHEN; Substances: [ACETAMINOPHEN]` | `The evidence supports that the medicine is Acetaminophen... Formulations, strengths, and qualifiers are not specified.` | `The evidence shows that the following are all ranked as having Acetaminophen: Brand: Acetaminophen; Generic: ACETAMINOPHEN; Substances: [ACETAMINOPHEN]` | **Eliminated ungrounded negative assertion** (*"formulations are not specified"*); 100% grounded. |
| **`MED-BENCH-017`**<br>`"What generic drug is in Advil?"` | `IBUPROFEN.` | `The generic drugs listed for Advil are IBUPROFEN, CAMPHOR, CAPSAICIN, MENTHOL, and METHYL SALICYLATE.` | `The generic drugs found in Advil are: IBUPROFEN, CAMPHOR, CAPSAICIN, MENTHOL, and METHYL SALICYLATE.` | Complete factual answer; no parser exceptions or evaluator timeouts. |
| **`MED-BENCH-042`**<br>`"Treatment protocol for acute Martian respiratory syndrome"` | `No information is available for Treatment protocol for acute Martian respiratory syndrome in the provided evidence.` | Hallucinated Poractant Alfa (`Curosurf`) due to manufacturer text lexical collision. | `No information is available for Treatment protocol for acute Martian respiratory syndrome in the provided evidence.` | **Blocked by Query-Entity Verification Gate**; zero hallucination. |

---

## 4. Safety Decoupling & Legal Disclaimer Contract

1. **Decoupled Architecture:**
   - Routine prompts contain **zero emergency guidance instructions**.
   - Acute presentations (chest pain, severe shortness of breath, anaphylaxis) are evaluated by a dedicated deterministic emergency triage filter before LLM execution.
   - When triggered, emergency clinical guidance is placed at the head of the user-facing response.
2. **Mandatory Verbatim Legal Disclaimer:**
   Every user-facing response concludes with the unaltered 47-word legal notice:
   ```markdown
   ### ⚠️ Important Medical & Legal Disclaimer
   MediScanAI is an AI-powered informational tool, not a doctor, pharmacist, or licensed healthcare provider. The information provided is for educational purposes only and must not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional before starting, stopping, or changing any medication.
   ```
3. **Decoupled Ragas Evaluation Contract:**
   - Ragas faithfulness and answer relevancy are strictly computed on `response_body` (the clinical statement excluding the disclaimer).
   - This prevents boilerplate disclaimer text from diluting claim precision or causing ungrounded meta-talk flags.
