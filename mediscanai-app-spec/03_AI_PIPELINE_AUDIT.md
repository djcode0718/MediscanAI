# MediScanAI — AI Pipeline, Multimodal Inference & RAG Architecture Audit

**Document:** `mediscanai-app-spec/03_AI_PIPELINE_AUDIT.md`  
**Status:** Complete Technical Audit  
**Scope:** PaddleOCR, Faster-Whisper STT, FAISS Hybrid Retrieval, Cross-Encoder Reranking, Zero-Cost LLM Fallback Chain, and Emergency Triage Guardrails  
**Baseline Code:** `app/core.py`, `app/ocr.py`, `app/whisper.py`, `app/retriever.py`, `app/llm_providers.py`, `app/guardrail.py`

---

## 1. Executive Summary

MediScanAI executes a specialized, multi-stage clinical intelligence pipeline designed to combine visual OCR extraction, spoken voice transcription, hybrid vector/lexical retrieval, and grounded LLM reasoning.

The pipeline is engineered to operate on local CPU hardware (such as an Apple Silicon M4) without requiring paid third-party AI APIs, while supporting an optional 4-tier zero-cost online LLM fallback chain.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Multimodal Client Inputs                              │
│       [ Packaging Photo ]       [ Voice Audio ]       [ Symptom Text ]      │
└──────────────┬─────────────────────────┬──────────────────────┬─────────────┘
               │                         │                      │
               ▼                         ▼                      │
     ┌───────────────────┐     ┌───────────────────┐            │
     │  PaddleOCR Engine │     │  Faster-Whisper   │            │
     │ (Text & Box Poly) │     │ (CPU int8 Speech) │            │
     └─────────┬─────────┘     └─────────┬─────────┘            │
               │                         │                      │
         [ OCR Text ]              [ Voice Text ]               │
               │                         └───────────┬──────────┘
               │                                     ▼
               │                           [ Combined Symptoms ]
               │                                     │
               ▼                                     ▼
     ┌───────────────────┐                 ┌───────────────────┐
     │ Hybrid Search OCR │                 │Hybrid Search Syms │
     │  • drug_dict      │                 │  • diseases       │
     │  • drugs (label)  │                 │  • drugs (symp)   │
     └─────────┬─────────┘                 └─────────┬─────────┘
               │                                     │
               └──────────────────┬──────────────────┘
                                  ▼
               ┌─────────────────────────────────────┐
               │    Reciprocal Rank Fusion (RRF)     │
               │                  +                  │
               │   Cross-Encoder Neural Reranking    │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │  Emergency Triage Guardrail Check   │
               │  (Chest pain / Stroke / Anaphylaxis)│
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │    Context-Grounded Prompt Engine   │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │         LLM Provider Chain          │
               │  1. Gemini 3.6 Flash (Free tier)    │
               │  2. Gemini 3.7 Flash (Free tier)    │
               │  3. Groq OSS 120B (Free tier)       │
               │  4. Groq OSS 20B (Free tier)        │
               │  [or Offline: Ollama / Mistral]     │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │   Summary Card & Verdict Assembly   │
               │   (Danger / Success / Caution)      │
               └─────────────────────────────────────┘
```

---

## 2. Component Audits

### 2.1 Vision & Optical Character Recognition (PaddleOCR)
- **Implementation:** `app/ocr.py`.
- **Engine:** PaddleOCR 3.2.0 (`paddlepaddle` 3.0.0, `paddlex` 3.2.1, `opencv-python` 4.12.0).
- **Configuration:** English model (`lang='en'`) with textline orientation classification enabled (`use_textline_orientation=True`).
- **Startup Pre-Warming (`prewarm_ocr()`):**
  - Mandatory requirement executed during backend startup before Faster-Whisper is initialized.
  - Generates a synthetic in-memory white image (`np.ones((64, 128, 3), dtype=np.uint8) * 255`) and executes inference.
  - *Purpose:* Primes OpenMP C++ thread pools and verifies native inference stability to eliminate native library initialization deadlocks.
- **Thread Safety:** Protected by a dedicated re-entrant threading lock (`_ocr_lock`).
- **Outputs:**
  - `texts`: List of recognized text strings.
  - `boxes`: Coordinate polygons for detected bounding regions.
  - Joined label string (`ocr_text_join()`) passed to downstream retrieval.
- **Failure Resilience:** If OCR fails due to corrupt input or unreadable images, the pipeline catches the error, sets `ocr_status = "FAILED"`, and engages an informational fallback instructing the user to enter text or submit a clearer photo.

### 2.2 Voice Audio Transcription (Faster-Whisper)
- **Implementation:** `app/whisper.py`.
- **Engine:** Faster-Whisper 1.0.0 (CTranslate2-based Whisper implementation).
- **Model Size:** `base` (optimized for fast CPU execution).
- **Execution Parameters:** `device="cpu"`, `compute_type="int8"`, `beam_size=5`.
- **Thread Safety:** Protected by `threading.Lock()` to prevent race conditions during concurrent audio chunk processing.
- **Multimodal Concatenation:** If spoken audio is transcribed alongside manual text input, the spoken text is cleanly appended:
  ```python
  combined_symptoms = f"{text} (Spoken: {voice_text})"
  ```
- **Performance:** Typically completes in **100–250 ms** for voice clips up to 10 seconds on Apple Silicon.

### 2.3 Hybrid Retrieval Engine (FAISS + BM25 + Cross-Encoder)
- **Implementation:** `app/retriever.py`, `app/core.py`.
- **Embedding Model:** `sentence-transformers` running `all-MiniLM-L6-v2` (384-dimensional dense vectors).
- **Lexical Search:** Rank-BM25 over pre-tokenized JSONL corpora.
- **Index Inventory:**
  | Index Name | FAISS File | JSONL Dataset | Key Dimension / Purpose |
  | :--- | :--- | :--- | :--- |
  | `diseases` | `indexes/diseases_faiss.index` | `data/diseases_faiss_data.jsonl` | Disease descriptions, clinical presentations, symptoms. |
  | `drugs` | `indexes/drugs_faiss.index` | `data/drugs_faiss_data.jsonl` | Official FDA drug labeling, indications, warnings, active ingredients. |
  | `drug_dict` | `indexes/drug_dict_faiss.index` | `data/drug_dict_faiss_data.jsonl` | Common commercial brand names and generic active molecule mappings. |
- **Fusion & Reranking:**
  1. Dense FAISS search retrieves top-$k$ nearest neighbors by cosine similarity.
  2. Sparse BM25 retrieves top-$k$ lexical matches.
  3. Reciprocal Rank Fusion (RRF) merges dense and sparse rankings.
  4. Cross-Encoder neural model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) performs pair-wise scoring between user query and retrieved passages to produce a calibrated confidence score ($0.0$ to $1.0$).

### 2.4 Emergency Triage Guardrail
- **Implementation:** `app/guardrail.py`, `app/guardrail_config.json`.
- **Purpose:** Protects patient safety by intercepting acute life-threatening presentations before or after LLM generation.
- **Trigger Categories:**
  - Acute coronary syndromes (chest pain, pressure radiating to left arm/jaw).
  - Cerebrovascular accidents / Stroke (facial drooping, unilateral arm weakness, slurred speech).
  - Anaphylaxis and severe respiratory distress.
  - Severe acute hemorrhage or altered mental status.
- **Fast-Path Mechanism:**
  - Evaluates combined user input and OCR text prior to vector search.
  - If a `CRITICAL_EMERGENCY` pattern matches, it engages the immediate fast-path:
    - Bypasses vector retrieval and external LLM calls.
    - Generates emergency directive instructing the user to call **112** (India) or **911** (US) immediately.
    - Completes response in under **10 ms**, logging an `EMERGENCY_GUARDRAIL_TRIGGERED` audit event.
- **Mandatory Disclaimer Enforcement:**
  - Injects `MANDATORY_HEADER` (`### ⚠️ Important Warning`) and `MANDATORY_TEXT` into every response, establishing that MediScanAI is an educational decision-support tool, not a diagnostic medical authority.

---

## 3. LLM Provider Fallback Chain

MediScanAI supports two operational modes governed by `LLM_MODE` in the backend environment:

### Mode A: `offline` (Local Host Inference)
- Connects to local Ollama daemon at `http://localhost:11434`.
- Default model: `mistral` (or `llama3.1:8b`).
- Zero data egress; 100% offline functionality.

### Mode B: `online` (Zero-Cost Cloud Fallback Chain)
- Activated via `LLM_MODE=online` in `.env`.
- Executes a strict 4-step sequential fallback chain:
  ```
  Step 1: Google Gemini 3.6 Flash (gemini-3.6-flash)
            │ (On timeout, rate limit, or HTTP error)
            ▼
  Step 2: Google Gemini 3.7 Flash (gemini-3.7-flash)
            │ (On failure)
            ▼
  Step 3: Groq OSS 120B (openai/gpt-oss-120b)
            │ (On failure)
            ▼
  Step 4: Groq OSS 20B (openai/gpt-oss-20b)
  ```
- **Zero-Cost Guarantee:** All four models operate within the free developer tiers of Google AI Studio and Groq Cloud.
- **Client Security:** API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) reside exclusively in the server environment. Keys are never transmitted, logged, or exposed to the web or iOS clients.
- **Fail-Closed:** If all four providers fail, the backend raises `OnlineProviderError` returning HTTP 503, preventing corrupted or hallucinated responses.

---

## 4. Pipeline Execution Timings & Resource Footprint

Empirical timings measured on Apple Silicon (M4 / 16 GB):

| Pipeline Stage | Processing Engine | Typical Latency | Notes |
| :--- | :--- | :--- | :--- |
| **STT Audio Transcription** | Faster-Whisper (CPU int8) | 100–250 ms | Per 5–10s audio clip |
| **Vision OCR Extraction** | PaddleOCR (Pre-warmed) | 250–450 ms | Single packaging photo |
| **Vector Index Retrieval** | FAISS + SentenceTransformers | 15–35 ms | Across 3 index corpora |
| **Cross-Encoder Rerank** | MS-MARCO MiniLM | 40–80 ms | Pair-wise candidate scoring |
| **Emergency Guardrail** | Regex / Pattern Trie | 2–5 ms | Pre- and post-generation |
| **LLM Inference (Online)** | Gemini Flash / Groq | 800–1,500 ms | Network RTT + generation |
| **Database Persistence** | PostgreSQL / JSONB | 5–15 ms | Data-minimized record save |
| **Total End-to-End** | Complete Multimodal Pipeline | **1.2 – 2.4 seconds** | Standard user request |

---

## 5. Architectural Implications for Native iOS App

1. **Zero Client-Side AI Execution:** The iOS app will not bundle CoreML models, PaddleOCR bindings, or local LLMs. Doing so would bloat the app binary by gigabytes and drain iPhone battery. All AI computation remains hosted on the Mac backend.
2. **Multipart Request Compatibility:** The iOS app must format packaging photos and voice recordings to match the backend's exact MIME types and magic byte expectations:
   - Photos: JPEG or PNG format.
   - Voice: M4A (`audio/m4a` / `ftyp`) or WAV (`audio/wav` / `RIFF....WAVE`).
3. **Structured Response Rendering:** Rather than treating the result as an unformatted text blob, the iOS UI must decode the structured `card` payload, presenting the verdict, clinical explanation, suggested alternatives, and collapsible supporting evidence in distinct native SwiftUI components.

