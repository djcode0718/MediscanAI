# tests/test_whisper.py

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.whisper import WhisperTranscriber

def run_transcription_test():
    print("--- Initializing Whisper Transcriber ---")
    
    try:
        transcriber = WhisperTranscriber(model_size="base")
    except Exception as e:
        print(f"[ERROR] Failed to load the Whisper model: {e}")
        print("Please ensure you have a stable internet connection for the first-time model download.")
        return

    audio_file = os.path.join(os.path.dirname(__file__), "speech1.wav")

    if not os.path.exists(audio_file):
        print(f"\n[ERROR] Test audio file not found at: {audio_file}")
        print("Please record a sample audio file and save it as 'test_audio.wav' in the 'tests/' directory.")
        return

    print(f"\n[TEST] Transcribing audio file: {audio_file}")
    print("--- Awaiting transcription... ---")

    try:
        transcribed_text = transcriber.transcribe_audio_file(audio_file)
        
        print("\n[RESULT] Transcription complete:\n")
        print(f'"{transcribed_text}"')

    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred during transcription: {e}")

if __name__ == "__main__":
    run_transcription_test()