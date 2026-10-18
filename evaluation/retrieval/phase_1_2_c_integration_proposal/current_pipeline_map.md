# MediScanAI Current Pipeline Flow and Architectural Map

**Document Version:** 1.0.0  
**Phase:** Phase 1.2.c — Integration Proposal & Readiness Design  
**Date:** 2026-10-17  
**Status:** Analytical Map (Zero Production Code Changes)

---

## 1. Executive Pipeline Architecture

The current MediScanAI request lifecycle spans from the FastAPI web tier down to local embedding and inference engines. This document maps every stage of the live pipeline to identify where the emergency guardrail can be safely and reliably integrated.

```
[Client Request: text, image, audio]
       │
       ▼
[FastAPI /api/analyze] (backend/main.py)
       │── 1. Correlation ID Middleware & CORS
       │── 2. Rate Limiting (Redis/In-Memory token bucket)
       │── 3. Input Validation (Length bounds, MIME signatures, temp files)
       │── 4. Concurrency Slot Manager (Capacity check)
       │── 5. Whisper Audio Transcription (Worker thread offload)
       │── 6. Modality Resolution (text / image / audio / multimodal)
       │
       ▼
[app.core.Pipeline.run()] (app/core.py)
       │── 7. Text Normalization (app/utils.py)
       │── 8. OCR Text Extraction (EasyOCR / PaddleOCR via app/ocr.py)
       │── 9. Multi-Index Hybrid Retrieval:
       │      ├── Disease index (FAISS Dense + BM25 Sparse + Cross-Encoder Rerank)
       │      ├── Drug index (Symptoms)
       │      ├── Drug dictionary index (OCR brand/generic names)
       │      └── Optional Neo4j Knowledge Graph neighborhood retrieval
       │── 10. Prompt Assembly (app/prompt.py: ANALYSIS_PROMPT_TEMPLATE)
       │── 11. LLM Generation (app/llm.py: Ollama llama3.1:8b or online provider)
       │── 12. Summary Card Formatting (app/formatter.py: build_summary_card)
       │
       ▼
[FastAPI Return Path] (backend/main.py)
       │── 13. Verdict Headline Extraction
       │── 14. PostgreSQL Database Persistence (Analysis record)
       │── 15. Audit Event Recording (record_audit_event)
       │── 16. JSON Delivery to Client (HTTP 200)
```

---

## 2. Detailed Stage-by-Stage Breakdown

### Stage 1: Request Ingestion & Boundary Checks (`backend/main.py:200-262`)
- **Endpoint:** `POST /api/analyze`
- **Inputs:** `text: Optional[str] = Form(None)`, `image: Optional[UploadFile] = File(None)`, `audio: Optional[List[UploadFile]] = File(None)`.
- **Pre-Execution Guards:**
  - `check_rate_limit()`: Enforces `RATE_LIMIT_ANALYZE_PER_MINUTE` per user.
  - `validate_text_length()`: Validates input string length.
  - `slot_manager.try_acquire()`: Limits maximum simultaneous compute allocations.
  - Temporary files created in secure temporary paths.

### Stage 2: Multimodal Input Ingestion (`backend/main.py:263-331`)
- **Audio Processing:** Clips transcribed via `WhisperTranscriber.transcribe_audio_file` in a worker thread. Result appended to symptoms: `combined_symptoms += f" (Spoken: {voice_text})"`.
- **Image Processing:** Validated via `validate_image_file()`. Suffix preserved, saved to randomized temporary location.
- **Combined Context:** Final user query text represents `combined_symptoms`.

### Stage 3: Core Retrieval Pipeline (`app/core.py:Pipeline.run`)
- **Text Normalization:** Lowercasing, punctuation stripping, and whitespace collapse via `app/utils.py:normalize_text`.
- **OCR Execution:** If image path provided, `extract_text_from_image()` extracts bounding boxes and text lines.
- **Vector & Sparse Retrieval:**
  - `diseases_retrieved`: FAISS dense vector search + BM25 search over `diseases_faiss_data.jsonl`, reranked by `ms-marco-MiniLM-L-6-v2`.
  - `drugs_retrieved`: Searched against user symptom text.
  - `drug_dict_retrieved` & `drugs_from_ocr_retrieved`: Searched against OCR medicine packaging text.
- **Graph Enrichment:** If `NEO4J_ENABLED` is true, queries disease neighborhood and symptom overlaps.

### Stage 4: Prompt Assembly & Generation (`app/core.py:440-460`)
- **Prompt Template:** `ANALYSIS_PROMPT_TEMPLATE` from `app/prompt.py`.
- **Formatting:** Injects `<USER_SYMPTOMS_TEXT>`, `<OCR_MEDICINE_TEXT>`, `<CONTEXT_FOR_SYMPTOMS>`, and `<CONTEXT_FOR_MEDICINE>`.
- **LLM Call:** `llm_response_str = generate_with_mode(full_prompt, llm_mode=llm_mode)`.
  - Local mode invokes Ollama API (`/api/generate` with `llama3.1:8b`).
  - Online mode routes to Groq or Google Gemini API.

### Stage 5: Response Formatting & Persistence (`app/core.py:461-502` & `backend/main.py:350-405`)
- **Summary Card:** `build_summary_card()` packages `user_text`, `ocr_text`, `llm_output`, and retrieved previews.
- **Database Persistence:** `Analysis` model saved with `user_id`, `modality`, `status='completed'`, `verdict`, `summary_card`, and `processing_duration_ms`.
- **Audit Logging:** Data-minimized `record_audit_event("ANALYSIS_CREATED", metadata={...})`.
- **Response Structure:** Returns JSON containing `{"card": card, "meta": card_meta, "analysis_id": analysis.id, "timings": stage_timings}`.

---

## 3. Vulnerability and Defect Analysis of Current Flow

1. **No Emergency Triage Layer:**
   - The current production pipeline treats all inputs identically—whether a user asks for paracetamol dosage or describes acute crushing retrosternal chest pain.
   - There is no clinical escalation logic anywhere in `backend/main.py`, `app/core.py`, or `app/prompt.py`.

2. **Prompt-Only Safety Vulnerability (Phase 1.2.a Regression):**
   - The prompt instructs the model: *"You should always consult a qualified doctor or pharmacist for an accurate diagnosis..."*
   - In `MED-BENCH-038`, the LLM synthesized the retrieved evidence (correctly identifying acute coronary syndrome) but concluded: *"It is advisable to schedule an appointment with a primary care physician or cardiologist for a comprehensive diagnostic workup."*
   - For an acute myocardial infarction, scheduling an outpatient clinic appointment introduces a lethal delay.

3. **Latency to Safety Escalation:**
   - Generating an 8B model completion takes 3,000 ms to 8,000 ms.
   - For critical emergencies (e.g. cardiac arrest, active anaphylaxis, massive arterial bleeding), forcing a user in extremis to wait several seconds for a model to generate text before giving emergency dispatch numbers is unacceptable if early detection is possible.

---

## 4. Candidate Integration Points in the Request Lifecycle

We identify three distinct potential insertion boundaries in the current architecture:

```
[Request Input] 
       │
       ├─► [INSERTION POINT 1: Ingestion Pre-Filter] (backend/main.py, before pipeline.run)
       │
[Hybrid Retrieval]
       │
       ├─► [INSERTION POINT 2: Pre-Generation Prompt Injection] (app/core.py, before generate())
       │
[LLM Generation]
       │
       └─► [INSERTION POINT 3: Post-Generation Response Guard] (app/core.py or backend/main.py, before build_summary_card)
```

1. **Point 1 (Ingestion Pre-Filter):** Evaluates `combined_symptoms` immediately after Whisper transcription and input validation.
2. **Point 2 (Pre-Generation Injection):** Evaluates query + retrieved evidence right before `generate_with_mode()`.
3. **Point 3 (Post-Generation Response Guard):** Evaluates generated response and deterministically supersedes or replaces unsafe text before building `summary_card` and persisting to the database.

These insertion points are compared in detail in `integration_architecture.md`.
