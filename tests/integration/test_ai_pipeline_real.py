# tests/integration/test_ai_pipeline_real.py
import os
import pytest
from app.core import Pipeline
from app.whisper import WhisperTranscriber
from app.ocr import extract_text_from_image


@pytest.mark.integration
class TestAIPipelineRealIntegration:
    """
    Genuine AI Integration Tests executing against real local ML models
    (Faster-Whisper, PaddleOCR, SentenceTransformers, FAISS, CrossEncoder, Mistral/Ollama).
    """

    @pytest.fixture(scope="class")
    def real_pipeline(self):
        return Pipeline()

    @pytest.fixture(scope="class")
    def real_transcriber(self):
        return WhisperTranscriber(model_size="base")

    def test_real_audio_transcription(self, real_transcriber):
        audio_path = "tests/speech1.wav"
        if not os.path.exists(audio_path):
            pytest.skip("Test audio file tests/speech1.wav not found.")
        text = real_transcriber.transcribe_audio_file(audio_path)
        assert text is not None
        assert len(text) > 0
        assert not text.startswith("Error:")

    def test_real_ocr_extraction(self):
        img_path = "tests/ocr_preview.jpg"
        if not os.path.exists(img_path):
            pytest.skip("Test image tests/ocr_preview.jpg not found.")
        res = extract_text_from_image(img_path)
        assert "texts" in res
        assert len(res["texts"]) > 0

    def test_real_pipeline_text_only(self, real_pipeline):
        res = real_pipeline.run(
            user_text="I have had a sore throat and mild fever for two days.",
            image_path=None
        )
        assert "card" in res
        card = res["card"]
        assert "llm_output" in card
        assert len(card["llm_output"]) > 0
        assert "⚠️ Important Warning" in card["llm_output"] or "Warning" in card["llm_output"]

    def test_real_pipeline_multimodal(self, real_pipeline):
        img_path = "tests/ocr_preview.jpg"
        if not os.path.exists(img_path):
            pytest.skip("Test image tests/ocr_preview.jpg not found.")
        res = real_pipeline.run(
            user_text="I have a cough and chest congestion.",
            image_path=img_path
        )
        assert "card" in res
        card = res["card"]
        assert "llm_output" in card
        assert len(card["llm_output"]) > 0
