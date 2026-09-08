# tests/unit/test_llm_reliability.py
import pytest
import requests
from unittest.mock import patch, MagicMock
from app.llm import (
    OllamaError,
    check_ollama_status,
    call_ollama_api_generate,
    generate
)


class TestLlmReliabilityUnit:
    """Unit tests for Ollama timeouts, failure degradation, and error propagation."""

    def test_check_ollama_status_probe(self):
        # Mock successful status
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            assert check_ollama_status() is True

        # Mock unreachable status
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            with patch("shutil.which", return_value=None):
                assert check_ollama_status() is False

    def test_ollama_api_timeout_handling(self):
        with patch("requests.post", side_effect=requests.exceptions.ReadTimeout):
            with pytest.raises(OllamaError) as exc:
                call_ollama_api_generate("Test prompt", model="mistral")
            assert exc.value.is_timeout is True
            assert "timed out" in exc.value.message

    def test_ollama_api_connection_error_handling(self):
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            with pytest.raises(OllamaError) as exc:
                call_ollama_api_generate("Test prompt", model="mistral")
            assert exc.value.is_unavailable is True
            assert "unreachable" in exc.value.message

    def test_generate_fallback_to_cli_on_unavailable(self):
        with patch("app.llm.call_ollama_api_generate", side_effect=OllamaError("API down", is_unavailable=True)):
            with patch("app.llm.call_ollama_cli_generate", return_value="Clinical response from CLI"):
                resp = generate("Test prompt")
                assert resp == "Clinical response from CLI"
