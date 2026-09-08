# app/llm.py
import requests
import subprocess
import json
import shutil
import time
import logging
from typing import Dict, Any, Optional

from backend.core.config import settings

logger = logging.getLogger("mediscanai.llm")

DEFAULT_MODEL = getattr(settings, "OLLAMA_MODEL", "mistral")
CONNECT_TIMEOUT = getattr(settings, "OLLAMA_CONNECT_TIMEOUT_SECONDS", 5.0)
READ_TIMEOUT = getattr(settings, "OLLAMA_READ_TIMEOUT_SECONDS", 60.0)


class OllamaError(Exception):
    """Structured exception for local Ollama LLM failures."""
    def __init__(self, message: str, is_timeout: bool = False, is_unavailable: bool = False):
        super().__init__(message)
        self.message = message
        self.is_timeout = is_timeout
        self.is_unavailable = is_unavailable


def check_ollama_status() -> bool:
    """
    Lightweight probe for Ollama readiness.
    Checks GET /api/tags with a 2-second timeout without generating text.
    """
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        r = requests.get(url, timeout=(2.0, 2.0))
        return r.status_code == 200
    except Exception:
        # Check CLI fallback
        return shutil.which("ollama") is not None


def call_ollama_api_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    options: Optional[Dict] = None
) -> str:
    """
    Call local Ollama REST generate endpoint with explicit connection and read timeouts.
    """
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    if options:
        payload["options"] = options

    try:
        _t_ollama = time.perf_counter()
        r = requests.post(
            url,
            json=payload,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        r.raise_for_status()
        _ollama_ms = int((time.perf_counter() - _t_ollama) * 1000)
        print(f"[LLM] Ollama REST generate ({model}): {_ollama_ms}ms")
    except requests.exceptions.ConnectTimeout:
        logger.warning(f"Ollama connection timed out after {CONNECT_TIMEOUT}s.")
        raise OllamaError("Connection to local Ollama service timed out.", is_timeout=True, is_unavailable=True)
    except requests.exceptions.ReadTimeout:
        logger.warning(f"Ollama inference read timed out after {READ_TIMEOUT}s.")
        raise OllamaError("Inference request timed out during clinical generation.", is_timeout=True)
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Ollama connection failed: {e}")
        raise OllamaError("Local Ollama service is unreachable.", is_unavailable=True)
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Ollama HTTP error response: {e}")
        raise OllamaError(f"Ollama inference error: {r.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error communicating with Ollama: {e}")
        raise OllamaError(f"Ollama call failed: {e}")

    try:
        j = r.json()
    except Exception:
        return r.text

    if isinstance(j, dict):
        if 'response' in j:
            return j['response']
        if 'text' in j:
            return j['text']
        if 'output' in j:
            return j['output']
        if 'results' in j and isinstance(j['results'], list) and len(j['results']) > 0:
            first = j['results'][0]
            if isinstance(first, dict) and 'content' in first:
                return first['content']
        return json.dumps(j)
    return str(j)


def call_ollama_cli_generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Fallback: call 'ollama' CLI if installed.
    """
    if shutil.which("ollama") is None:
        raise OllamaError("ollama CLI not found and REST API failed.", is_unavailable=True)
    try:
        proc = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=int(READ_TIMEOUT + 30),
            encoding='utf-8'
        )
        if proc.returncode != 0:
            raise OllamaError(f"ollama CLI returned non-zero code: {proc.stderr}")
        return proc.stdout.strip()
    except subprocess.TimeoutExpired:
        raise OllamaError("Ollama CLI invocation timed out.", is_timeout=True)
    except Exception as e:
        raise OllamaError(f"ollama CLI invocation failed: {e}")


def generate(prompt: str, model: str = DEFAULT_MODEL, options: Optional[Dict] = None) -> str:
    """
    High-level wrapper. Try REST API first, then CLI fallback.
    """
    try:
        return call_ollama_api_generate(prompt, model=model, options=options)
    except OllamaError as e:
        if e.is_unavailable:
            logger.info("Ollama REST endpoint unavailable, attempting CLI fallback...")
            return call_ollama_cli_generate(prompt, model=model)
        raise


def generate_with_mode(prompt: str, llm_mode: str = "offline") -> str:
    """
    Route LLM generation to the appropriate provider based on llm_mode.

    llm_mode="offline"  -> Ollama/Mistral (existing pipeline, unchanged)
    llm_mode="online"   -> Gemini -> Grok fallback chain

    Raises OllamaError or OnlineProviderError on failure.
    Does NOT cross modes automatically.
    """
    if llm_mode == "online":
        from app.llm_providers import generate_online
        logger.info("LLM mode: online (Gemini -> Grok)")
        return generate_online(prompt)
    else:
        logger.info("LLM mode: offline (Ollama/Mistral)")
        return generate(prompt)