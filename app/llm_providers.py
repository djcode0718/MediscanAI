# app/llm_providers.py
"""
Online LLM provider module for MediScanAI.

Fallback chain: Gemini-1 -> Gemini-2 -> Groq-1 -> Groq-2

API keys are read exclusively from backend settings (env vars / .env file).
Keys are NEVER logged, printed, or included in error messages.
"""
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
import requests

from backend.core.config import settings, get_settings
from app.llm import GenerationParams

logger = logging.getLogger("mediscanai.llm_providers")


def _get_cfg():
    return settings if type(settings).__name__ == "MagicMock" else get_settings()


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

def call_gemini_meta(
    prompt: str,
    model: str,
    params: Optional[GenerationParams] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Call Google Gemini generateContent REST API and return (text, meta).
    Raises OnlineProviderError on any failure.
    """
    cfg = _get_cfg()
    api_key = cfg.GEMINI_API_KEY
    timeout = cfg.ONLINE_LLM_TIMEOUT_SECONDS
    if not api_key or not api_key.strip():
        raise OnlineProviderError(
            "Gemini API key is not configured.",
            provider=f"gemini/{model}",
            is_key_missing=True,
        )

    real_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key.strip()}"
    )
    gen_config: Dict[str, Any] = {
        "temperature": 0.3,
        "maxOutputTokens": 2048,
    }
    if params:
        if params.temperature is not None:
            gen_config["temperature"] = params.temperature
        if params.num_predict is not None:
            gen_config["maxOutputTokens"] = params.num_predict

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }

    r = None
    try:
        _t = time.perf_counter()
        r = requests.post(real_url, json=payload, timeout=timeout)
        _ms = int((time.perf_counter() - _t) * 1000)
        r.raise_for_status()
        print(f"[LLM] Gemini ({model}): {_ms}ms")
    except requests.exceptions.Timeout:
        logger.warning("Gemini/%s timed out after %.1fs.", model, timeout)
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
        cand = j["candidates"][0]
        text = cand["content"]["parts"][0]["text"]
        finish_reason = cand.get("finishReason")
        truncated_by_length = (finish_reason in ("MAX_TOKENS", "length"))
        usage = j.get("usageMetadata", {})
        meta = {
            "provider": "gemini",
            "model": f"gemini/{model}",
            "latency_ms": _ms,
            "finish_reason": finish_reason,
            "done_reason": finish_reason,
            "prompt_eval_count": usage.get("promptTokenCount"),
            "eval_count": usage.get("candidatesTokenCount"),
            "truncated_by_length": truncated_by_length,
            "likely_prompt_truncated": False,
        }
        return text, meta
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("Gemini/%s response parse error: %s", model, type(exc).__name__)
        raise OnlineProviderError(
            f"Failed to parse Gemini ({model}) response.", provider=f"gemini/{model}"
        )


def call_gemini(
    prompt: str,
    model: str,
    params: Optional[GenerationParams] = None,
) -> str:
    """
    Call Google Gemini generateContent REST API for a specific model.
    """
    text, _ = call_gemini_meta(prompt, model, params=params)
    return text


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

def call_groq_meta(
    prompt: str,
    model: str,
    params: Optional[GenerationParams] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Call Groq chat completions REST API (OpenAI-compatible) and return (text, meta).
    Raises OnlineProviderError on any failure.
    """
    cfg = _get_cfg()
    api_key = cfg.GROQ_API_KEY
    timeout = cfg.ONLINE_LLM_TIMEOUT_SECONDS
    if not api_key or not api_key.strip():
        raise OnlineProviderError(
            "Groq API key is not configured.",
            provider=f"groq/{model}",
            is_key_missing=True,
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    if params:
        if params.temperature is not None:
            payload["temperature"] = params.temperature
        if params.seed is not None:
            payload["seed"] = params.seed
        if params.num_predict is not None:
            payload["max_tokens"] = params.num_predict

    r = None
    try:
        _t = time.perf_counter()
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        _ms = int((time.perf_counter() - _t) * 1000)
        r.raise_for_status()
        print(f"[LLM] Groq ({model}): {_ms}ms")
    except requests.exceptions.Timeout:
        logger.warning("Groq/%s timed out after %.1fs.", model, timeout)
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
        choice = j["choices"][0]
        text = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
        truncated_by_length = (finish_reason in ("length", "max_tokens"))
        usage = j.get("usage", {})
        meta = {
            "provider": "groq",
            "model": f"groq/{model}",
            "latency_ms": _ms,
            "finish_reason": finish_reason,
            "done_reason": finish_reason,
            "prompt_eval_count": usage.get("prompt_tokens"),
            "eval_count": usage.get("completion_tokens"),
            "truncated_by_length": truncated_by_length,
            "likely_prompt_truncated": False,
        }
        return text, meta
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("Groq/%s response parse error: %s", model, type(exc).__name__)
        raise OnlineProviderError(
            f"Failed to parse Groq ({model}) response.", provider=f"groq/{model}"
        )


def call_groq(
    prompt: str,
    model: str,
    params: Optional[GenerationParams] = None,
) -> str:
    """
    Call Groq chat completions REST API (OpenAI-compatible) for a specific model.
    """
    text, _ = call_groq_meta(prompt, model, params=params)
    return text


# ---------------------------------------------------------------------------
# Online orchestrator: Gemini-1 -> Gemini-2 -> Groq-1 -> Groq-2
# ---------------------------------------------------------------------------

def generate_online_meta(
    prompt: str,
    params: Optional[GenerationParams] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Execute online provider fallback chain returning (text, meta) from the model that answered.
    """
    cfg = _get_cfg()
    steps: List[tuple] = [
        ("gemini", cfg.GEMINI_MODEL_1),
        ("gemini", cfg.GEMINI_MODEL_2),
        ("groq",   cfg.GROQ_MODEL_1),
        ("groq",   cfg.GROQ_MODEL_2),
    ]

    last_error: Optional[OnlineProviderError] = None

    for provider, model in steps:
        try:
            if provider == "gemini":
                logger.info("Online mode: trying Gemini/%s", model)
                return call_gemini_meta(prompt, model, params=params)
            else:
                logger.info("Online mode: trying Groq/%s", model)
                return call_groq_meta(prompt, model, params=params)
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


def generate_online(
    prompt: str,
    params: Optional[GenerationParams] = None,
) -> str:
    """
    Execute the 4-step online provider fallback chain.
    """
    text, _ = generate_online_meta(prompt, params=params)
    return text

