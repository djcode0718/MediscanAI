# app/llm_providers.py
"""
Online LLM provider module for MediScanAI.

Fallback chain: Gemini-1 -> Gemini-2 -> Groq-1 -> Groq-2

API keys are read exclusively from backend settings (env vars / .env file).
Keys are NEVER logged, printed, or included in error messages.
"""
import time
import logging
from typing import Optional, List

import requests

from backend.core.config import settings

logger = logging.getLogger("mediscanai.llm_providers")

ONLINE_TIMEOUT = settings.ONLINE_LLM_TIMEOUT_SECONDS


class OnlineProviderError(Exception):
    """Structured exception for online provider failures."""

    def __init__(self, message: str, provider: str, is_key_missing: bool = False):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.is_key_missing = is_key_missing


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, model: str) -> str:
    """
    Call Google Gemini generateContent REST API for a specific model.
    Raises OnlineProviderError on any failure (key missing, network, API error).
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or not api_key.strip():
        raise OnlineProviderError(
            "Gemini API key is not configured.",
            provider=f"gemini/{model}",
            is_key_missing=True,
        )

    # Key goes into URL query param only — never into logs or error messages
    real_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key.strip()}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }

    r = None
    try:
        _t = time.perf_counter()
        r = requests.post(real_url, json=payload, timeout=ONLINE_TIMEOUT)
        _ms = int((time.perf_counter() - _t) * 1000)
        r.raise_for_status()
        print(f"[LLM] Gemini ({model}): {_ms}ms")
    except requests.exceptions.Timeout:
        logger.warning("Gemini/%s timed out after %.1fs.", model, ONLINE_TIMEOUT)
        raise OnlineProviderError(
            f"Gemini ({model}) timed out.", provider=f"gemini/{model}"
        )
    except requests.exceptions.ConnectionError:
        logger.warning("Gemini/%s connection failed.", model)
        raise OnlineProviderError(
            f"Could not connect to Gemini API ({model}).", provider=f"gemini/{model}"
        )
    except requests.exceptions.HTTPError:
        sc = r.status_code if r is not None else "?"
        logger.warning("Gemini/%s HTTP error: status=%s", model, sc)
        raise OnlineProviderError(
            f"Gemini ({model}) returned HTTP {sc}.", provider=f"gemini/{model}"
        )
    except OnlineProviderError:
        raise
    except Exception as exc:
        logger.warning("Gemini/%s unexpected error: %s", model, type(exc).__name__)
        raise OnlineProviderError(
            f"Gemini ({model}) failed unexpectedly.", provider=f"gemini/{model}"
        )

    try:
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("Gemini/%s response parse error: %s", model, type(exc).__name__)
        raise OnlineProviderError(
            f"Failed to parse Gemini ({model}) response.", provider=f"gemini/{model}"
        )


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

def call_groq(prompt: str, model: str) -> str:
    """
    Call Groq chat completions REST API (OpenAI-compatible) for a specific model.
    Raises OnlineProviderError on any failure.
    """
    api_key = settings.GROQ_API_KEY
    if not api_key or not api_key.strip():
        raise OnlineProviderError(
            "Groq API key is not configured.",
            provider=f"groq/{model}",
            is_key_missing=True,
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        # Key goes in Authorization header only — never in logs
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    r = None
    try:
        _t = time.perf_counter()
        r = requests.post(url, json=payload, headers=headers, timeout=ONLINE_TIMEOUT)
        _ms = int((time.perf_counter() - _t) * 1000)
        r.raise_for_status()
        print(f"[LLM] Groq ({model}): {_ms}ms")
    except requests.exceptions.Timeout:
        logger.warning("Groq/%s timed out after %.1fs.", model, ONLINE_TIMEOUT)
        raise OnlineProviderError(
            f"Groq ({model}) timed out.", provider=f"groq/{model}"
        )
    except requests.exceptions.ConnectionError:
        logger.warning("Groq/%s connection failed.", model)
        raise OnlineProviderError(
            f"Could not connect to Groq API ({model}).", provider=f"groq/{model}"
        )
    except requests.exceptions.HTTPError:
        sc = r.status_code if r is not None else "?"
        logger.warning("Groq/%s HTTP error: status=%s", model, sc)
        raise OnlineProviderError(
            f"Groq ({model}) returned HTTP {sc}.", provider=f"groq/{model}"
        )
    except OnlineProviderError:
        raise
    except Exception as exc:
        logger.warning("Groq/%s unexpected error: %s", model, type(exc).__name__)
        raise OnlineProviderError(
            f"Groq ({model}) failed unexpectedly.", provider=f"groq/{model}"
        )

    try:
        j = r.json()
        return j["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("Groq/%s response parse error: %s", model, type(exc).__name__)
        raise OnlineProviderError(
            f"Failed to parse Groq ({model}) response.", provider=f"groq/{model}"
        )


# ---------------------------------------------------------------------------
# Online orchestrator: Gemini-1 -> Gemini-2 -> Groq-1 -> Groq-2
# ---------------------------------------------------------------------------

def generate_online(prompt: str) -> str:
    """
    Execute the 4-step online provider fallback chain:
      1. Gemini (gemini-2.0-flash)
      2. Gemini (gemini-1.5-flash)
      3. Groq   (llama-3.3-70b-versatile)
      4. Groq   (llama-3.1-8b-instant)

    Each step is attempted only after the previous one fails.
    Does NOT fall back to Ollama — online mode stays online.
    Raises OnlineProviderError if all four attempts fail.
    """
    steps: List[tuple] = [
        ("gemini", settings.GEMINI_MODEL_1),
        ("gemini", settings.GEMINI_MODEL_2),
        ("groq",   settings.GROQ_MODEL_1),
        ("groq",   settings.GROQ_MODEL_2),
    ]

    last_error: Optional[OnlineProviderError] = None

    for provider, model in steps:
        try:
            if provider == "gemini":
                logger.info("Online mode: trying Gemini/%s", model)
                return call_gemini(prompt, model)
            else:
                logger.info("Online mode: trying Groq/%s", model)
                return call_groq(prompt, model)
        except OnlineProviderError as exc:
            logger.warning(
                "Online provider %s/%s failed: %s — trying next.",
                provider, model, exc.message,
            )
            last_error = exc

    # All four failed
    logger.error("All online providers failed. Last error: %s", last_error.message if last_error else "unknown")
    raise OnlineProviderError(
        "All online providers (Gemini x2, Groq x2) are currently unavailable. "
        "Please try again later or switch to Offline mode.",
        provider="all",
    )
