# backend/main.py
import os
import tempfile
import shutil
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core_new import Pipeline
from app.whisper import WhisperTranscriber

app = FastAPI(title="MediScanAI Backend API", version="1.0.0")

# Enable CORS for frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origin (e.g. ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances loaded lazily or on startup
pipeline_instance = None
transcriber_instance = None

def get_pipeline():
    global pipeline_instance
    if pipeline_instance is None:
        try:
            print("🚀 Loading MediScanAI RAG Pipeline (FAISS + SentenceTransformers)...")
            pipeline_instance = Pipeline()
        except Exception as e:
            print(f"❌ Error loading Pipeline: {e}")
            raise HTTPException(status_code=500, detail=f"retrieval pipeline failed to load: {e}")
    return pipeline_instance

def get_transcriber():
    global transcriber_instance
    if transcriber_instance is None:
        try:
            print("🎙️ Loading Faster-Whisper Speech-to-Text Model...")
            transcriber_instance = WhisperTranscriber(model_size="base")
        except Exception as e:
            print(f"❌ Error loading Whisper: {e}")
            raise HTTPException(status_code=500, detail=f"speech transcription model failed to load: {e}")
    return transcriber_instance

@app.on_event("startup")
async def startup_event():
    # Pre-warm models so subsequent requests are fast
    try:
        get_pipeline()
    except Exception:
        pass
    try:
        get_transcriber()
    except Exception:
        pass

@app.get("/")
def read_root():
    return {"status": "running", "message": "MediScanAI FastAPI backend is active."}

@app.post("/api/analyze")
async def analyze(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[List[UploadFile]] = File(None)
):
    pipeline = get_pipeline()
    
    temp_files = []
    combined_symptoms = text or ""
    temp_image_path = None

    try:
        # 1. Process Voice Clips / Audio uploads
        if audio and len(audio) > 0:
            transcriber = get_transcriber()
            transcriptions = []
            
            for index, clip in enumerate(audio):
                # Verify it's actually an uploaded file and not empty
                if not clip.filename:
                    continue
                
                # Write to secure temp file
                suffix = os.path.splitext(clip.filename)[1] or ".wav"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                    shutil.copyfileobj(clip.file, temp_audio)
                    temp_audio_path = temp_audio.name
                    temp_files.append(temp_audio_path)
                
                # Transcribe
                print(f"Transcribing audio clip {index+1}/{len(audio)}: {clip.filename}")
                clip_text = transcriber.transcribe_audio_file(temp_audio_path)
                if clip_text and not clip_text.startswith("Error:"):
                    transcriptions.append(clip_text)
            
            if transcriptions:
                voice_text = " ".join(transcriptions)
                if combined_symptoms:
                    combined_symptoms += f" (Spoken: {voice_text})"
                else:
                    combined_symptoms = voice_text

        # 2. Process Medicine Image
        if image and image.filename:
            suffix = os.path.splitext(image.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_img:
                shutil.copyfileobj(image.file, temp_img)
                temp_image_path = temp_img.name
                temp_files.append(temp_image_path)
            print(f"Received medicine image: {image.filename}, saved to {temp_image_path}")

        # 3. Validation: Ensure we have some text or image context
        if not combined_symptoms and not temp_image_path:
            raise HTTPException(
                status_code=400,
                detail="At least symptom text, recorded audio, or a medicine image must be provided."
            )

        # 4. Execute Pipeline
        print(f"Running pipeline. symptoms: '{combined_symptoms[:100]}...', image: {temp_image_path}")
        result = pipeline.run(user_text=combined_symptoms, image_path=temp_image_path)
        return result

    except Exception as e:
        print(f"❌ Error in analysis pipeline: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up all temp files
        for path in temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Cleaned up temp file: {path}")
                except Exception as ex:
                    print(f"Failed to remove temp file {path}: {ex}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
