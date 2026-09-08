# backend/main.py
import os
import shutil
import logging
import time
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.errors import global_exception_handler
from backend.core.middleware import CorrelationIdMiddleware
from backend.db.session import check_db_connection, get_db
from backend.models.user import User
from backend.models.analysis import Analysis
from backend.api.auth import router as auth_router
from backend.api.analyses import router as analyses_router
from backend.api.deps import get_current_active_user
from backend.core.upload_validator import (
    validate_image_file,
    validate_audio_file,
    validate_text_length,
    generate_safe_temp_path
)
from backend.core.rate_limiter import check_rate_limit
from backend.core.concurrency import slot_manager
from backend.core.audit import record_audit_event
from app.core import Pipeline
from app.whisper import WhisperTranscriber
from app.llm import check_ollama_status, OllamaError
from app.llm_providers import OnlineProviderError

logger = logging.getLogger("mediscanai.api")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Privacy-First Multimodal AI Health Copilot API"
)

# Register global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Register Correlation / Request ID Middleware
app.add_middleware(CorrelationIdMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(analyses_router)

# Global model instances loaded lazily or on startup
pipeline_instance: Optional[Pipeline] = None
transcriber_instance: Optional[WhisperTranscriber] = None


def get_pipeline() -> Pipeline:
    global pipeline_instance
    if pipeline_instance is None:
        try:
            print("🚀 Loading MediScanAI RAG Pipeline (FAISS + SentenceTransformers)...")
            pipeline_instance = Pipeline()
        except Exception as e:
            logger.error(f"Error loading Pipeline: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"retrieval pipeline failed to load: {e}"
            )
    return pipeline_instance


def get_transcriber() -> WhisperTranscriber:
    global transcriber_instance
    if transcriber_instance is None:
        try:
            print("🎙️ Loading Faster-Whisper Speech-to-Text Model...")
            transcriber_instance = WhisperTranscriber(model_size="base")
        except Exception as e:
            logger.error(f"Error loading Whisper: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"speech transcription model failed to load: {e}"
            )
    return transcriber_instance


@app.on_event("startup")
async def startup_event():
    _t_startup = time.perf_counter()
    print("\n" + "=" * 60)
    print("[STARTUP] MediScanAI initialization beginning...")
    print("=" * 60)

    # 1. Verify PostgreSQL connectivity
    _t_db = time.perf_counter()
    db_healthy = check_db_connection()
    _db_s = time.perf_counter() - _t_db
    if db_healthy:
        print(f"[STARTUP] PostgreSQL connection: {_db_s:.2f}s ✅")
    else:
        print(f"[STARTUP] PostgreSQL connection: {_db_s:.2f}s ⚠️  (failed — will retry on request)")

    # 2. Pre-warm Pipeline (embedding model + FAISS + BM25 + CrossEncoder)
    _t_pipeline = time.perf_counter()
    try:
        get_pipeline()
        print(f"[STARTUP] RAG pipeline total: {time.perf_counter()-_t_pipeline:.2f}s ✅")
    except Exception as e:
        print(f"[STARTUP] RAG pipeline: {time.perf_counter()-_t_pipeline:.2f}s ⚠️  (skipped/failed: {e})")

    # 3. Pre-warm Whisper
    _t_whisper = time.perf_counter()
    try:
        get_transcriber()
        # [STARTUP] Whisper model line already printed inside WhisperTranscriber.__init__
    except Exception as e:
        print(f"[STARTUP] Whisper model: {time.perf_counter()-_t_whisper:.2f}s ⚠️  (skipped/failed: {e})")

    _total_s = time.perf_counter() - _t_startup
    print("[STARTUP] " + "-" * 50)
    print(f"[STARTUP] Total initialization: {_total_s:.2f}s")
    print("=" * 60 + "\n")


@app.get("/")
def read_root():
    """Basic root health ping."""
    return {
        "status": "running",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "message": "MediScanAI FastAPI backend is active."
    }


@app.get("/api/health")
def health_check():
    """
    Liveness probe: answers whether the application process is alive and responsive.
    Always returns fast without executing heavy downstream queries.
    """
    return {
        "status": "alive",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": time.time()
    }


@app.get("/api/ready")
def readiness_check():
    """
    Readiness probe: answers whether this instance is capable of serving analysis requests.
    Checks PostgreSQL connectivity, model load status, and lightweight Ollama availability.
    """
    db_ok = check_db_connection()
    models_ready = pipeline_instance is not None and transcriber_instance is not None
    ollama_ok = check_ollama_status()

    is_ready = db_ok and models_ready and ollama_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    response_payload = {
        "status": "ready" if is_ready else "not_ready",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "components": {
            "database": "connected" if db_ok else "disconnected",
            "models_loaded": "ready" if models_ready else "not_loaded",
            "ollama_service": "available" if ollama_ok else "unavailable"
        },
        "concurrency": {
            "active_slots": slot_manager.active_slots,
            "max_concurrent": slot_manager.max_concurrent
        }
    }

    if not is_ready:
        raise HTTPException(
            status_code=status_code,
            detail=response_payload
        )

    return response_payload


@app.post("/api/analyze")
async def analyze(
    request: Request,
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Protected, Rate-Limited, Concurrency-Controlled Multimodal Analysis Endpoint.
    LLM provider is determined by LLM_MODE in server config (.env), not by the client.
    """
    # Read server-configured LLM mode (set via LLM_MODE in .env)
    llm_mode = settings.LLM_MODE

    # 1. Rate Limiting Check (Request frequency)
    rate_key = f"user:{current_user.id}"
    is_allowed, retry_after = check_rate_limit(rate_key, settings.RATE_LIMIT_ANALYZE_PER_MINUTE, window_seconds=60)
    if not is_allowed:
        record_audit_event(
            event_type="RATE_LIMIT_EXCEEDED",
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"endpoint": "/api/analyze", "limit_per_min": settings.RATE_LIMIT_ANALYZE_PER_MINUTE},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please wait {retry_after} seconds before submitting another analysis.",
            headers={"Retry-After": str(retry_after)}
        )

    # 2. Input Bounds Validation
    validate_text_length(text)

    if audio and len(audio) > settings.MAX_AUDIO_CLIPS_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum allowed audio clips count is {settings.MAX_AUDIO_CLIPS_COUNT}."
        )

    # 3. Concurrency Capacity Check (Simultaneous compute protection)
    if not slot_manager.try_acquire():
        record_audit_event(
            event_type="CONCURRENCY_LIMIT_EXCEEDED",
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"endpoint": "/api/analyze", "max_concurrent": settings.MAX_CONCURRENT_ANALYSES},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MediScanAI is currently processing maximum concurrent clinical analyses. Please try again shortly.",
            headers={"Retry-After": "5"}
        )

    temp_files = []
    combined_symptoms = text or ""
    temp_image_path = None
    start_time = time.perf_counter()
    stage_timings: Dict[str, int] = {}

    try:
        # 4. Process & Validate Voice Audio Clips (Non-blocking transcription)
        if audio and len(audio) > 0:
            t_whisper_start = time.perf_counter()
            transcriber = get_transcriber()
            transcriptions = []
            
            for index, clip in enumerate(audio):
                if not clip.filename:
                    continue
                
                # File signature & size validation
                validate_audio_file(clip)
                
                # Generate safe randomized temporary path
                suffix = os.path.splitext(clip.filename)[1] or ".wav"
                temp_audio_path = generate_safe_temp_path(suffix)
                temp_files.append(temp_audio_path)
                
                with open(temp_audio_path, "wb") as f_out:
                    shutil.copyfileobj(clip.file, f_out)
                
                # Non-blocking transcription offloaded to worker thread
                logger.info(f"Transcribing audio clip {index+1}/{len(audio)} in worker thread...")
                clip_text = await asyncio.to_thread(transcriber.transcribe_audio_file, temp_audio_path)
                if clip_text and not clip_text.startswith("Error:"):
                    transcriptions.append(clip_text)
            
            if transcriptions:
                voice_text = " ".join(transcriptions)
                if combined_symptoms:
                    combined_symptoms += f" (Spoken: {voice_text})"
                else:
                    combined_symptoms = voice_text
            
            stage_timings["whisper_ms"] = int((time.perf_counter() - t_whisper_start) * 1000)

        # 5. Process & Validate Medicine Image
        if image and image.filename:
            validate_image_file(image)
            suffix = os.path.splitext(image.filename)[1] or ".jpg"
            temp_image_path = generate_safe_temp_path(suffix)
            temp_files.append(temp_image_path)
            
            with open(temp_image_path, "wb") as f_out:
                shutil.copyfileobj(image.file, f_out)
            logger.info("Medicine image validated and prepared.")

        # 6. Validation: Ensure we have some text or image context
        if not combined_symptoms and not temp_image_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least symptom text, recorded audio, or a medicine image must be provided."
            )

        # Determine modality
        has_text = bool(text and text.strip())
        has_image = bool(temp_image_path)
        has_audio = bool(audio and len(audio) > 0)
        modality_count = sum([has_text, has_image, has_audio])
        if modality_count > 1:
            modality = "multimodal"
        elif has_image:
            modality = "image"
        elif has_audio:
            modality = "audio"
        else:
            modality = "text"

        # 7. Execute AI/RAG Pipeline Non-Blockingly
        pipeline = get_pipeline()
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Executing clinical pipeline for user ID %d [modality: %s] "
            "[llm_mode: %s] [request_id: %s] in worker thread...",
            current_user.id, modality, llm_mode, request_id
        )

        t_rag_start = time.perf_counter()
        result = await asyncio.to_thread(
            pipeline.run,
            user_text=combined_symptoms,
            image_path=temp_image_path,
            llm_mode=llm_mode
        )
        stage_timings["rag_pipeline_ms"] = int((time.perf_counter() - t_rag_start) * 1000)

        # Merge fine-grained pipeline timings from core.py
        pipeline_inner = result.pop("pipeline_timings", {})
        stage_timings.update(pipeline_inner)

        # Extract structured verdict headline
        llm_out = result.get("card", {}).get("llm_output", "")
        verdict_headline = None
        if llm_out:
            lines = [line.strip() for line in llm_out.split("\n") if line.strip()]
            if lines:
                verdict_headline = lines[0].replace("#", "").replace("*", "").strip()[:500]

        # 8. Persist Analysis Record (Data-Minimized)
        t_persist_start = time.perf_counter()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        stage_timings["total_duration_ms"] = duration_ms

        analysis = Analysis(
            user_id=current_user.id,
            modality=modality,
            status="completed",
            verdict=verdict_headline,
            summary_card=result.get("card", {}),
            processing_duration_ms=duration_ms
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        stage_timings["db_persistence_ms"] = int((time.perf_counter() - t_persist_start) * 1000)

        # Attach persisted analysis_id and stage timings to API response
        result["analysis_id"] = analysis.id
        result["timings"] = stage_timings

        # 9. Record Operational Audit Event
        record_audit_event(
            event_type="ANALYSIS_CREATED",
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "analysis_id": analysis.id,
                "modality": modality,
                "duration_ms": duration_ms,
                "timings": stage_timings
            },
            db=db
        )

        # --- Request-level timing summary ---
        _req_id = getattr(request.state, "request_id", "unknown")
        _provider = "Gemini/Groq" if llm_mode == "online" else "Ollama/Mistral"
        print("\n" + "=" * 60)
        print(f"[TIMING] Request ID: {_req_id}")
        print(f"[TIMING] Analysis ID: {analysis.id}  Modality: {modality}  LLM: {_provider}")
        if "whisper_ms" in stage_timings:
            print(f"[TIMING]   Whisper STT:              {stage_timings['whisper_ms']}ms")
        if "ocr_total_ms" in stage_timings:
            print(f"[TIMING]   OCR total (init+infer):   {stage_timings['ocr_total_ms']}ms")
        print(f"[TIMING]   Retrieval diseases:         {stage_timings.get('retrieval_diseases_ms', 0)}ms")
        print(f"[TIMING]   Retrieval drugs (symptoms): {stage_timings.get('retrieval_drugs_ms', 0)}ms")
        if "retrieval_drug_dict_ms" in stage_timings:
            print(f"[TIMING]   Retrieval drug_dict (OCR):  {stage_timings['retrieval_drug_dict_ms']}ms")
        if "retrieval_drugs_from_ocr_ms" in stage_timings:
            print(f"[TIMING]   Retrieval drugs (OCR):      {stage_timings['retrieval_drugs_from_ocr_ms']}ms")
        print(f"[TIMING]   Prompt assembly:             {stage_timings.get('prompt_assembly_ms', 0)}ms")
        print(f"[TIMING]   LLM (Ollama/Mistral):        {stage_timings.get('llm_total_ms', 0)}ms")
        print(f"[TIMING]   DB persistence:              {stage_timings.get('db_persistence_ms', 0)}ms")
        print(f"[TIMING]   " + "-" * 40)
        print(f"[TIMING]   Total request:              {duration_ms}ms  ({duration_ms/1000:.2f}s)")
        print("=" * 60 + "\n")

        logger.info(
            f"ANALYSIS_COMPLETED: id={analysis.id} modality={modality} "
            f"total_ms={duration_ms} request_id={_req_id} stages={stage_timings}"
        )

        return result

    except HTTPException:
        raise
    except OllamaError as oe:
        logger.error(f"Ollama failure during analysis: {oe.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clinical AI inference service is temporarily unavailable. Please try again shortly."
        )
    except OnlineProviderError as ope:
        logger.error("Online provider failure during analysis: %s", ope.message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Online AI service error: {ope.message}"
        )
    except Exception as e:
        logger.error(f"Error in analysis pipeline execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete clinical analysis. Please try again later."
        )

    finally:
        # Guaranteed release of concurrency slot
        slot_manager.release()

        # Guaranteed cleanup of all temporary files
        for path in temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as ex:
                    logger.warning(f"Failed to remove temp file {path}: {ex}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
