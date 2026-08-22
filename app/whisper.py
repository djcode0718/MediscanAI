from faster_whisper import WhisperModel
import os

class WhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def transcribe_audio_file(self, audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            return "Error: Audio file not found."

        segments, info = self.model.transcribe(audio_file_path, beam_size=5)

        print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

        transcribed_text = "".join(segment.text for segment in segments).strip()
        
        return transcribed_text