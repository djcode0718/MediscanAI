from faster_whisper import WhisperModel
import os
import time
import threading

class WhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        _t = time.perf_counter()
        self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        print(f"[STARTUP] Whisper model (size={model_size}): {time.perf_counter()-_t:.2f}s")
        self._lock = threading.Lock()

    def transcribe_audio_file(self, audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            return "Error: Audio file not found."

        _t = time.perf_counter()
        with self._lock:
            segments, info = self.model.transcribe(audio_file_path, beam_size=5)

            print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

            transcribed_text = "".join(segment.text for segment in segments).strip()
        _infer_ms = int((time.perf_counter() - _t) * 1000)
        print(f"[STT] Whisper transcription inference: {_infer_ms}ms ({len(transcribed_text)} chars)")

        return transcribed_text