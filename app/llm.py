# app/llm.py
import requests
import subprocess
import json
import shutil
import time
import logging
from typing import Dict, Any, Optional, Tuple

from backend.core.config import settings

from dataclasses import dataclass, asdict

logger = logging.getLogger("mediscanai.llm")

DEFAULT_MODEL = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")
CONNECT_TIMEOUT = getattr(settings, "OLLAMA_CONNECT_TIMEOUT_SECONDS", 5.0)
READ_TIMEOUT = getattr(settings, "OLLAMA_READ_TIMEOUT_SECONDS", 60.0)


@dataclass(frozen=True)
class GenerationParams:
    """Optional generation hyperparameters; None indicates do not override."""
    temperature: Optional[float] = None
    seed: Optional[int] = None
    num_ctx: Optional[int] = None
    num_predict: Optional[int] = None


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


def call_ollama_api_generate_meta(
    prompt: str,
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    options: Optional[Dict] = None,
    params: Optional[GenerationParams] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Call local Ollama REST generate endpoint with explicit timeouts and return (text, meta).
    """
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    merged_options = dict(options) if options else {}
    if params:
        if params.temperature is not None:
            merged_options["temperature"] = params.temperature
        if params.seed is not None:
            merged_options["seed"] = params.seed
        if params.num_ctx is not None:
            merged_options["num_ctx"] = params.num_ctx
        if params.num_predict is not None:
            merged_options["num_predict"] = params.num_predict

    if merged_options:
        payload["options"] = merged_options

    # Effective context limit determination
    if params and params.num_ctx is not None:
        effective_num_ctx = params.num_ctx
    elif "num_ctx" in merged_options:
        effective_num_ctx = merged_options["num_ctx"]
    else:
        # Observed default context window for Ollama 0.30.5 on llama3.1:8b
        effective_num_ctx = 8192

    r = None
    try:
        _t_ollama = time.perf_counter()
        conn_to = getattr(settings, "OLLAMA_CONNECT_TIMEOUT_SECONDS", 5.0)
        read_to = getattr(settings, "OLLAMA_READ_TIMEOUT_SECONDS", 180.0)
        r = requests.post(
            url,
            json=payload,
            timeout=(conn_to, read_to)
        )
        r.raise_for_status()
        _ollama_ms = int((time.perf_counter() - _t_ollama) * 1000)
        print(f"[LLM] Ollama REST generate ({model}): {_ollama_ms}ms")
    except requests.exceptions.ConnectTimeout:
        logger.warning(f"Ollama connection timed out after {conn_to}s.")
        raise OllamaError("Connection to local Ollama service timed out.", is_timeout=True, is_unavailable=True)
    except requests.exceptions.ReadTimeout:
        logger.warning(f"Ollama inference read timed out after {read_to}s.")
        raise OllamaError("Inference request timed out during clinical generation.", is_timeout=True)
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Ollama connection failed: {e}")
        raise OllamaError("Local Ollama service is unreachable.", is_unavailable=True)
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Ollama HTTP error response: {e}")
        status_code = r.status_code if r is not None else "unknown"
        raise OllamaError(f"Ollama inference error: {status_code}")
    except Exception as e:
        logger.error(f"Unexpected error communicating with Ollama: {e}")
        raise OllamaError(f"Ollama call failed: {e}")

    try:
        j = r.json()
    except Exception:
        j = {"response": r.text}

    response_text = ""
    if isinstance(j, dict):
        if 'response' in j:
            response_text = str(j['response'])
        elif 'text' in j:
            response_text = str(j['text'])
        elif 'output' in j:
            response_text = str(j['output'])
        elif 'results' in j and isinstance(j['results'], list) and len(j['results']) > 0:
            first = j['results'][0]
            if isinstance(first, dict) and 'content' in first:
                response_text = str(first['content'])
        else:
            response_text = json.dumps(j)
    else:
        response_text = str(j)

    done_reason = j.get("done_reason") or j.get("finish_reason") if isinstance(j, dict) else None
    prompt_eval_count = j.get("prompt_eval_count") if isinstance(j, dict) else None
    eval_count = j.get("eval_count") if isinstance(j, dict) else None

    # Flag truncation semantics
    truncated_by_length = False
    if done_reason and str(done_reason).lower() in ("length", "max_tokens"):
        truncated_by_length = True
    elif params and params.num_predict is not None and eval_count is not None and eval_count >= params.num_predict:
        truncated_by_length = True

    likely_prompt_truncated = False
    if prompt_eval_count is not None and prompt_eval_count >= effective_num_ctx:
        likely_prompt_truncated = True

    meta = {
        "provider": "ollama",
        "model": f"ollama/{model}",
        "latency_ms": _ollama_ms,
        "finish_reason": done_reason,
        "done_reason": done_reason,
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
        "effective_num_ctx": effective_num_ctx,
        "truncated_by_length": truncated_by_length,
        "likely_prompt_truncated": likely_prompt_truncated,
    }
    return response_text, meta


def call_ollama_api_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    options: Optional[Dict] = None,
    params: Optional[GenerationParams] = None,
) -> str:
    """
    Call local Ollama REST generate endpoint with explicit connection and read timeouts.
    """
    text, _ = call_ollama_api_generate_meta(prompt, model=model, stream=stream, options=options, params=params)
    return text


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


def generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    options: Optional[Dict] = None,
    params: Optional[GenerationParams] = None,
) -> str:
    """
    High-level wrapper. Try REST API first, then CLI fallback.
    """
    try:
        return call_ollama_api_generate(prompt, model=model, options=options, params=params)
    except OllamaError as e:
        if e.is_unavailable:
            logger.info("Ollama REST endpoint unavailable, attempting CLI fallback...")
            return call_ollama_cli_generate(prompt, model=model)
        raise


def generate_meta(
    prompt: str,
    model: str = DEFAULT_MODEL,
    options: Optional[Dict] = None,
    params: Optional[GenerationParams] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    High-level wrapper returning (text, meta). Try REST API first, then CLI fallback.
    """
    try:
        return call_ollama_api_generate_meta(prompt, model=model, options=options, params=params)
    except OllamaError as e:
        if e.is_unavailable:
            logger.info("Ollama REST endpoint unavailable, attempting CLI fallback...")
            _t0 = time.perf_counter()
            cli_text = call_ollama_cli_generate(prompt, model=model)
            _latency = int((time.perf_counter() - _t0) * 1000)
            meta = {
                "provider": "ollama_cli",
                "model": f"ollama/{model}",
                "latency_ms": _latency,
                "finish_reason": "stop",
                "done_reason": "stop",
                "prompt_eval_count": None,
                "eval_count": None,
                "effective_num_ctx": params.num_ctx if params and params.num_ctx else 8192,
                "truncated_by_length": False,
                "likely_prompt_truncated": False,
            }
            return cli_text, meta
        raise


def generate_with_mode(
    prompt: str,
    llm_mode: str = "offline",
    params: Optional[GenerationParams] = None,
) -> str:
    """
    Route LLM generation to the appropriate provider based on llm_mode.

    llm_mode="offline"  -> Ollama/<model tag> (existing pipeline, unchanged)
    llm_mode="online"   -> Gemini -> Grok fallback chain

    Raises OllamaError or OnlineProviderError on failure.
    Does NOT cross modes automatically.
    """
    if llm_mode == "online":
        from app.llm_providers import generate_online
        logger.info("LLM mode: online (Gemini -> Grok)")
        return generate_online(prompt, params=params)
    else:
        configured_model = getattr(settings, "OLLAMA_MODEL", DEFAULT_MODEL)
        logger.info(f"LLM mode: offline (Ollama/{configured_model})")
        return generate(prompt, model=configured_model, params=params)


def generate_with_mode_meta(
    prompt: str,
    llm_mode: str = "offline",
    params: Optional[GenerationParams] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Route LLM generation to the appropriate provider based on llm_mode and return (text, meta).
    """
    if llm_mode == "online":
        from app.llm_providers import generate_online_meta
        logger.info("LLM mode: online (Gemini -> Grok)")
        return generate_online_meta(prompt, params=params)
    else:
        configured_model = getattr(settings, "OLLAMA_MODEL", DEFAULT_MODEL)
        logger.info(f"LLM mode: offline (Ollama/{configured_model})")
        return generate_meta(prompt, model=configured_model, params=params)