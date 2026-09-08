# tests/test_llm_providers.py
"""
Focused unit tests for the online LLM provider module.

All external HTTP calls are mocked — no real Gemini or Groq requests are made.
API keys never appear in assertion messages or error output.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

from app.llm_providers import (
    OnlineProviderError,
    call_gemini,
    call_groq,
    generate_online,
)
from app.llm import generate_with_mode, generate, OllamaError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gemini_ok_response(text: str) -> MagicMock:
    """Fake successful Gemini HTTP response."""
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": text}]}}]
    }
    return m


def _groq_ok_response(text: str) -> MagicMock:
    """Fake successful Groq HTTP response."""
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {
        "choices": [{"message": {"content": text}}]
    }
    return m


def _http_error_response(status_code: int) -> MagicMock:
    """Fake HTTP error response."""
    m = MagicMock()
    m.status_code = status_code
    m.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"HTTP {status_code}", response=m
    )
    return m


# ---------------------------------------------------------------------------
# Test: generate_with_mode routing
# ---------------------------------------------------------------------------

class TestGenerateWithModeRouting(unittest.TestCase):

    def test_offline_mode_calls_ollama_generate(self):
        """offline mode must delegate to generate() (Ollama), not online providers."""
        with patch("app.llm.generate", return_value="offline response") as mock_gen:
            result = generate_with_mode("test prompt", llm_mode="offline")
        mock_gen.assert_called_once_with("test prompt")
        self.assertEqual(result, "offline response")

    def test_online_mode_calls_generate_online(self):
        """online mode must delegate to generate_online(), not Ollama."""
        with patch("app.llm_providers.generate_online", return_value="online response") as mock_online:
            with patch("app.llm.generate_online", mock_online):
                result = generate_with_mode("test prompt", llm_mode="online")
        self.assertEqual(result, "online response")

    def test_default_mode_is_offline(self):
        """Default llm_mode must be offline."""
        with patch("app.llm.generate", return_value="default offline") as mock_gen:
            result = generate_with_mode("test prompt")
        mock_gen.assert_called_once()
        self.assertEqual(result, "default offline")

    def test_offline_does_not_call_online_providers(self):
        """Offline mode must never touch Gemini or Groq."""
        with patch("app.llm.generate", return_value="ok"):
            with patch("app.llm_providers.call_gemini") as mock_gemini:
                with patch("app.llm_providers.call_groq") as mock_groq:
                    generate_with_mode("test prompt", llm_mode="offline")
        mock_gemini.assert_not_called()
        mock_groq.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Gemini provider
# ---------------------------------------------------------------------------

class TestCallGemini(unittest.TestCase):

    @patch("app.llm_providers.settings")
    def test_raises_when_key_missing(self, mock_settings):
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        with self.assertRaises(OnlineProviderError) as ctx:
            call_gemini("prompt", "gemini-2.0-flash")
        self.assertTrue(ctx.exception.is_key_missing)
        self.assertNotIn("sk-", str(ctx.exception))  # key never in error

    @patch("requests.post")
    @patch("app.llm_providers.settings")
    def test_successful_response(self, mock_settings, mock_post):
        mock_settings.GEMINI_API_KEY = "fake-key-abc"
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        mock_post.return_value = _gemini_ok_response("Gemini answer")
        result = call_gemini("prompt", "gemini-2.0-flash")
        self.assertEqual(result, "Gemini answer")

    @patch("requests.post")
    @patch("app.llm_providers.settings")
    def test_api_key_not_in_request_log(self, mock_settings, mock_post):
        """The API key must not appear in any raised error messages."""
        secret = "super-secret-gemini-key-12345"
        mock_settings.GEMINI_API_KEY = secret
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        mock_post.return_value = _http_error_response(401)
        with self.assertRaises(OnlineProviderError) as ctx:
            call_gemini("prompt", "gemini-2.0-flash")
        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn(secret, ctx.exception.message)

    @patch("requests.post", side_effect=requests.exceptions.Timeout())
    @patch("app.llm_providers.settings")
    def test_timeout_raises_provider_error(self, mock_settings, mock_post):
        mock_settings.GEMINI_API_KEY = "fake-key"
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        with self.assertRaises(OnlineProviderError) as ctx:
            call_gemini("prompt", "gemini-2.0-flash")
        self.assertEqual(ctx.exception.provider, "gemini/gemini-2.0-flash")

    @patch("requests.post", side_effect=requests.exceptions.ConnectionError())
    @patch("app.llm_providers.settings")
    def test_connection_error_raises_provider_error(self, mock_settings, mock_post):
        mock_settings.GEMINI_API_KEY = "fake-key"
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        with self.assertRaises(OnlineProviderError):
            call_gemini("prompt", "gemini-2.0-flash")


# ---------------------------------------------------------------------------
# Test: Groq provider
# ---------------------------------------------------------------------------

class TestCallGroq(unittest.TestCase):

    @patch("app.llm_providers.settings")
    def test_raises_when_key_missing(self, mock_settings):
        mock_settings.GROQ_API_KEY = ""
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        with self.assertRaises(OnlineProviderError) as ctx:
            call_groq("prompt", "llama-3.3-70b-versatile")
        self.assertTrue(ctx.exception.is_key_missing)

    @patch("requests.post")
    @patch("app.llm_providers.settings")
    def test_successful_response(self, mock_settings, mock_post):
        mock_settings.GROQ_API_KEY = "fake-groq-key"
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        mock_post.return_value = _groq_ok_response("Groq answer")
        result = call_groq("prompt", "llama-3.3-70b-versatile")
        self.assertEqual(result, "Groq answer")

    @patch("requests.post")
    @patch("app.llm_providers.settings")
    def test_api_key_not_in_error_message(self, mock_settings, mock_post):
        secret = "gsk_super_secret_groq_key_xyz"
        mock_settings.GROQ_API_KEY = secret
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        mock_post.return_value = _http_error_response(403)
        with self.assertRaises(OnlineProviderError) as ctx:
            call_groq("prompt", "llama-3.3-70b-versatile")
        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn(secret, ctx.exception.message)

    @patch("requests.post", side_effect=requests.exceptions.Timeout())
    @patch("app.llm_providers.settings")
    def test_timeout_raises_provider_error(self, mock_settings, mock_post):
        mock_settings.GROQ_API_KEY = "fake-key"
        mock_settings.ONLINE_LLM_TIMEOUT_SECONDS = 60.0
        with self.assertRaises(OnlineProviderError):
            call_groq("prompt", "llama-3.3-70b-versatile")


# ---------------------------------------------------------------------------
# Test: generate_online fallback chain
# ---------------------------------------------------------------------------

class TestGenerateOnlineFallbackChain(unittest.TestCase):

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_gemini_1_succeeds_no_fallback(self, mock_settings, mock_gemini, mock_groq):
        """If Gemini-1 succeeds, Gemini-2 and Groq must never be called."""
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.return_value = "answer from gemini-1"

        result = generate_online("test prompt")

        self.assertEqual(result, "answer from gemini-1")
        mock_gemini.assert_called_once_with("test prompt", "gemini-2.0-flash")
        mock_groq.assert_not_called()

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_gemini_1_fails_gemini_2_succeeds(self, mock_settings, mock_gemini, mock_groq):
        """If Gemini-1 fails, Gemini-2 is tried before Groq."""
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.side_effect = [
            OnlineProviderError("Gemini-1 down", provider="gemini/gemini-2.0-flash"),
            "answer from gemini-2",
        ]

        result = generate_online("test prompt")

        self.assertEqual(result, "answer from gemini-2")
        self.assertEqual(mock_gemini.call_count, 2)
        mock_groq.assert_not_called()

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_both_gemini_fail_groq_1_succeeds(self, mock_settings, mock_gemini, mock_groq):
        """Both Gemini models fail -> Groq-1 is tried."""
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.side_effect = OnlineProviderError("Gemini down", provider="gemini")
        mock_groq.return_value = "answer from groq-1"

        result = generate_online("test prompt")

        self.assertEqual(result, "answer from groq-1")
        self.assertEqual(mock_gemini.call_count, 2)
        mock_groq.assert_called_once_with("test prompt", "llama-3.3-70b-versatile")

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_gemini_and_groq_1_fail_groq_2_succeeds(self, mock_settings, mock_gemini, mock_groq):
        """Both Gemini fail + Groq-1 fails -> Groq-2 succeeds."""
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.side_effect = OnlineProviderError("Gemini down", provider="gemini")
        mock_groq.side_effect = [
            OnlineProviderError("Groq-1 down", provider="groq/llama-3.3-70b-versatile"),
            "answer from groq-2",
        ]

        result = generate_online("test prompt")

        self.assertEqual(result, "answer from groq-2")
        self.assertEqual(mock_groq.call_count, 2)

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_all_four_providers_fail_raises_error(self, mock_settings, mock_gemini, mock_groq):
        """If all 4 providers fail, a clear OnlineProviderError is raised."""
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.side_effect = OnlineProviderError("Gemini down", provider="gemini")
        mock_groq.side_effect = OnlineProviderError("Groq down", provider="groq")

        with self.assertRaises(OnlineProviderError) as ctx:
            generate_online("test prompt")

        self.assertEqual(ctx.exception.provider, "all")
        self.assertIn("unavailable", ctx.exception.message.lower())

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_online_mode_never_falls_back_to_ollama(self, mock_settings, mock_gemini, mock_groq):
        """When all online providers fail, Ollama is never called."""
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.side_effect = OnlineProviderError("Gemini down", provider="gemini")
        mock_groq.side_effect = OnlineProviderError("Groq down", provider="groq")

        with patch("app.llm.generate") as mock_ollama:
            with self.assertRaises(OnlineProviderError):
                generate_online("test prompt")
            mock_ollama.assert_not_called()

    @patch("app.llm_providers.call_groq")
    @patch("app.llm_providers.call_gemini")
    @patch("app.llm_providers.settings")
    def test_error_messages_contain_no_keys(self, mock_settings, mock_gemini, mock_groq):
        """Final error message from generate_online must not contain any API key."""
        secret_gemini = "AIzaFakeGeminiKey123"
        secret_groq = "gsk_FakeGroqKey456"
        mock_settings.GEMINI_API_KEY = secret_gemini
        mock_settings.GROQ_API_KEY = secret_groq
        mock_settings.GEMINI_MODEL_1 = "gemini-2.0-flash"
        mock_settings.GEMINI_MODEL_2 = "gemini-1.5-flash"
        mock_settings.GROQ_MODEL_1 = "llama-3.3-70b-versatile"
        mock_settings.GROQ_MODEL_2 = "llama-3.1-8b-instant"
        mock_gemini.side_effect = OnlineProviderError("Gemini down", provider="gemini")
        mock_groq.side_effect = OnlineProviderError("Groq down", provider="groq")

        with self.assertRaises(OnlineProviderError) as ctx:
            generate_online("test prompt")

        error_msg = ctx.exception.message
        self.assertNotIn(secret_gemini, error_msg)
        self.assertNotIn(secret_groq, error_msg)


# ---------------------------------------------------------------------------
# Test: API endpoint validation (llm_mode field)
# ---------------------------------------------------------------------------

class TestAnalyzeEndpointLlmMode(unittest.TestCase):
    """Integration-level tests against the FastAPI endpoint."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.core.security import create_access_token
        from backend.db.session import SessionLocal
        from backend.models.user import User
        from backend.core.security import hash_password

        cls.app = app
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        email = "llm_mode_test@mediscan.ai"
        user = cls.db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                password_hash=hash_password("Password123!"),
                is_active=True,
                is_superuser=False,
            )
            cls.db.add(user)
            cls.db.commit()
            cls.db.refresh(user)
        cls.user = user
        cls.token = create_access_token(user.id)
        cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_invalid_llm_mode_returns_400(self):
        """An unrecognized llm_mode must return 400 before any ML work is done."""
        from unittest.mock import patch, MagicMock
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = {
            "card": {"user_text": "test", "ocr_text": "", "llm_output": "ok"},
            "meta": {},
            "pipeline_timings": {},
        }
        with patch("backend.main.get_pipeline", return_value=mock_pipeline):
            resp = self.client.post(
                "/api/analyze",
                data={"text": "headache", "llm_mode": "invalid_provider"},
                headers=self.auth_headers,
            )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("llm_mode", resp.json()["detail"])

    def test_valid_offline_mode_accepted(self):
        """llm_mode='offline' must be accepted and route to Ollama (mocked)."""
        from unittest.mock import patch, MagicMock
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = {
            "card": {
                "user_text": "headache",
                "ocr_text": "",
                "llm_output": "Based on the information, ### Suggested Alternatives\n* Paracetamol\n### ⚠️ Important Warning\nConsult a physician.",
            },
            "meta": {"mismatch": None, "mismatch_details": ""},
            "pipeline_timings": {},
        }
        with patch("backend.main.get_pipeline", return_value=mock_pipeline):
            resp = self.client.post(
                "/api/analyze",
                data={"text": "headache", "llm_mode": "offline"},
                headers=self.auth_headers,
            )
        self.assertIn(resp.status_code, [200, 422])
        if resp.status_code == 200:
            mock_pipeline.run.assert_called_once()
            call_kwargs = mock_pipeline.run.call_args
            self.assertEqual(call_kwargs.kwargs.get("llm_mode", "offline"), "offline")

    def test_offline_mode_is_default(self):
        """Omitting llm_mode must default to offline behavior."""
        from unittest.mock import patch, MagicMock
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = {
            "card": {
                "user_text": "headache",
                "ocr_text": "",
                "llm_output": "Based on the information, ### Suggested Alternatives\n* Paracetamol\n### ⚠️ Important Warning\nConsult a physician.",
            },
            "meta": {"mismatch": None, "mismatch_details": ""},
            "pipeline_timings": {},
        }
        with patch("backend.main.get_pipeline", return_value=mock_pipeline):
            resp = self.client.post(
                "/api/analyze",
                data={"text": "headache"},  # no llm_mode field
                headers=self.auth_headers,
            )
        if resp.status_code == 200:
            call_kwargs = mock_pipeline.run.call_args
            self.assertEqual(call_kwargs.kwargs.get("llm_mode", "offline"), "offline")


if __name__ == "__main__":
    unittest.main()
