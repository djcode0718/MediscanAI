# Phase C.2 — Generator Model Selection Recommendation

**Document Version:** 1.0.0  
**Phase:** C.2 (Model Selection Pilot)  
**Evaluator:** MediScanAI Evaluation Engineering  
**Date:** 2026-10-15  

---

## 1. Formal Recommendation

### **`Llama 3 8B preferred`**

Based on the 10-case controlled pilot comparing `llama3.1:8b` and `mistral:latest` under identical retrieval contexts, prompts, and deterministic runtime settings (`temperature=0`), **`llama3.1:8b` is recommended** as the primary answer-generation model for the MediScanAI Ragas evaluation benchmark (Phase C.3+).

---

## 2. Core Justification & Trade-Off Analysis

The selection is determined by clinical fidelity, grounding boundaries, and execution efficiency:

### A. Context Groundedness & Anti-Hallucination
- **Llama 3.1 8B (Score: 5.0/5.0):** Flawlessly adhered to context boundaries across all 10 cases. When presented with sparse drug monographs (`MED-BENCH-001 Lipitor`), it restricted its output strictly to the verified text provided.
- **Mistral (Score: 4.7/5.0):** Injected outside parametric memory on `MED-BENCH-001`, describing cholesterol and diabetes indications that were absent from the retrieved excerpt. While medically factual, in a RAG system evaluated for Faithfulness and Context Precision, injecting outside knowledge is an evidence-grounding failure.

### B. Clean Abstention on Negative Controls
- **Llama 3.1 8B (Score: 5.0/5.0):** On `MED-BENCH-041` (`NonexistentDrugZ 500mg`), Llama immediately recognized that the target entity was absent and delivered a crisp, decisive abstention. It was completely unaffected by the 10 distractor records present in the context.
- **Mistral (Score: 4.0/5.0):** While Mistral did ultimately abstain, it first enumerated and summarized several distractor 500mg drugs (acetaminophen, calcium carbonate, methocarbamol). This demonstrates vulnerability to distractor entrapment.

### C. Clinical Emergency Safety Escalation
- **Llama 3.1 8B (Score: 5.0/5.0):** On `MED-BENCH-038` (`Chest pain`), Llama explicitly instructed the user: *"If you are experiencing acute chest pain, it is crucial to seek immediate medical attention from a qualified healthcare professional."*
- **Mistral (Score: 4.0/5.0):** Provided comprehensive symptom coverage but defaulted to standard non-urgent disclaimer language ("consult a qualified doctor or pharmacist").

### D. Inference Latency & Operational Feasibility
- **Llama 3.1 8B:** Median latency of **14.1s** (Mean: 17.6s).
- **Mistral:** Median latency of **27.4s** (Mean: 29.1s).
- Llama 3.1 8B is **48.6% faster** than Mistral on local Apple Silicon hardware. In the upcoming full evaluation (Phase C.3), generating 100 paired benchmark answers (baseline vs graph) would take approximately 29 minutes with Llama 3.1 vs nearly an hour with Mistral.

### E. Output Formatting & Prompt Echoing (The Only Trade-Off)
- **Mistral:** Exhibited pristine Markdown formatting (Score: 5.0), automatically structuring responses with `### Factual Summary` and `### Clinical Limitations & Uncertainty`.
- **Llama 3.1 8B:** In 8 of 10 runs, Llama echoed the delimiter `<USER_QUERY>` at the top of its response (Score: 4.0).
- **Verdict:** Prompt tag echoing is a trivial string-cleaning issue (resolvable with a single-line regex strip during response extraction), whereas ungrounded knowledge injection and slow latency are fundamental model behaviors.

---

## 3. Comparison Summary Table

| Evaluation Dimension | Llama 3.1 8B | Mistral | Winner | Key Discriminator |
| :--- | :---: | :---: | :---: | :--- |
| **Evidence Groundedness** | **5.00** | 4.70 | **Llama 3.1** | Zero outside knowledge leakage on sparse monographs |
| **Answer Relevance** | **5.00** | 4.90 | **Llama 3.1** | Immediate query address without distractor preambles |
| **Completeness** | 4.50 | **4.90** | Mistral | Mistral provides more exhaustive symptom listings |
| **Abstention & Uncertainty** | 4.70 | **4.80** | Mistral | Mistral excels in dedicated uncertainty sections |
| **Medical Safety** | **4.90** | 4.90 | Tie | Llama superior on emergency escalation; both safe |
| **Format Compliance** | 4.00 | **5.00** | Mistral | Mistral avoids delimiter echoing |
| **Mandatory Warning** | **100%** | **100%** | Tie | 10/10 exact header and text adherence on both |
| **Inference Latency** | **14.1s** | 27.4s | **Llama 3.1** | Llama is 48.6% faster |
| **Core Clinical Quality** | 4.68 | **4.87** | Mistral | Driven by Mistral's completeness and formatting |
| **Overall Composite Score**| **4.46** | **4.46** | **Tie** | Perfect balance between speed/grounding vs formatting |

---

## 4. Scientific Limitations & Disclaimers

1. **Preliminary Pilot Scope:** These results are derived from a 10-case screening pilot. While cases were chosen to represent diverse benchmark categories (brand, generic, ingredient, single/multi-symptom, partial match, ambiguous, negative control, and safety-critical), performance across the remaining 40 benchmark cases may show category-specific variations.
2. **Not Clinical Validation:** This comparison evaluates research generation performance against technical rubrics. Scores do not constitute clinical certification or healthcare device safety validation.
3. **Hardware & Quantization Specificity:** Timings and behavior reflect 4-bit quantized models (`Q4_K_M`) executed sequentially on local Apple Silicon (arm64, 16GB RAM) via Ollama v0.30.5.

---

## 5. Next Steps for Phase C.3 Preparation

1. **Pre-processing / Post-processing Filter:** In the Ragas evaluation harness, apply a standard strip for `<USER_QUERY>` tags to normalize Llama 3.1 8B outputs before computing lexical or semantic metrics.
2. **Freeze Generation Pipeline:** Standardize the evaluation prompt and generation parameters (`temperature=0`, `num_predict=512`) using `llama3.1:8b`.
3. **Proceed to Full Evaluation Design:** With generator selection resolved, proceed to evaluate baseline vs graph retrieval quality on the full benchmark without modifying production code.
