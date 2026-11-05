"""
Judge LLM Factory and Transport Management (Phase 3).

Provides cleanly identifiable, fingerprinted judge configurations:
  1. 'openai_v1' (default / continuity): ChatOpenAI targeting Ollama /v1.
     - Known effective behavior: num_ctx=8192, seed=None, format=None, temp=0.0.
  2. 'native_ollama': NativeChatOllama targeting Ollama native /api/chat.
     - Known effective behavior: num_ctx=12288, seed=42, format='json', num_predict=700, temp=0.0.

Computes a deterministic configuration fingerprint for auditability and Cache V2 binding.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.language_models.chat_models import BaseChatModel

from evaluation.e2e.cache_v2 import get_effective_options, get_ollama_model_digest
from evaluation.e2e.score_phase01b_faithfulness import JUDGE_CONFIG

AUTHORIZED_JUDGE_MODEL = "llama3.1:8b"


class UnauthorizedJudgeError(ValueError):
    """Raised when an unauthorized judge model is requested for authoritative evaluation."""
    pass


class NativeChatOllama:
    """Lazy import wrapper around langchain_community.chat_models.ChatOllama with seed support."""
    _subclass = None

    @classmethod
    def get_class(cls):
        if cls._subclass is None:
            from langchain_community.chat_models import ChatOllama

            class _NativeChatOllama(ChatOllama):
                seed: Optional[int] = 42

                @property
                def _default_params(self) -> Dict[str, Any]:
                    params = super()._default_params
                    if self.seed is not None:
                        params["options"]["seed"] = self.seed
                    return params

            cls._subclass = _NativeChatOllama
        return cls._subclass


def get_judge_fingerprint(
    endpoint_type: str = "openai_v1",
    judge_config: Optional[Dict[str, Any]] = None,
    base_url: Optional[str] = None,
    allow_non_authoritative: bool = False,
) -> Dict[str, Any]:
    """Return complete configuration fingerprint and SHA-256 digest."""
    cfg = judge_config or JUDGE_CONFIG
    model_name = cfg.get("model", AUTHORIZED_JUDGE_MODEL)
    if not allow_non_authoritative and model_name != AUTHORIZED_JUDGE_MODEL:
        raise UnauthorizedJudgeError(
            f"Judge model '{model_name}' is unauthorized. The only authorized judge model "
            f"for authoritative MediScanAI evaluation is '{AUTHORIZED_JUDGE_MODEL}'."
        )

    digest = get_ollama_model_digest(model_name)
    eff_options = get_effective_options(cfg, endpoint_type)

    if endpoint_type == "openai_v1":
        url = base_url or "http://localhost:11434/v1"
    else:
        url = base_url or "http://localhost:11434"

    raw_fingerprint = {
        "endpoint_type": endpoint_type,
        "base_url": url.rstrip("/"),
        "model_name": model_name,
        "model_digest": digest,
        "requested_options": {
            "temperature": float(cfg.get("temperature", 0.0)),
            "seed": int(cfg.get("seed", 42)),
            "num_ctx": int(cfg.get("num_ctx", 12288)),
            "num_predict": int(cfg.get("num_predict", 700)),
            "format": str(cfg.get("format", "json")),
        },
        "effective_options": eff_options,
    }
    canonical = json.dumps(raw_fingerprint, sort_keys=True, separators=(",", ":"))
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    raw_fingerprint["fingerprint_sha256"] = sha
    return raw_fingerprint


def create_judge_llm(
    endpoint_type: str = "openai_v1",
    callbacks: Optional[List[Any]] = None,
    judge_config: Optional[Dict[str, Any]] = None,
    base_url: Optional[str] = None,
    allow_non_authoritative: bool = False,
) -> Tuple[BaseChatModel, Dict[str, Any]]:
    """
    Creates and returns (judge_llm, fingerprint).
    endpoint_type: 'openai_v1' or 'native_ollama'
    """
    cfg = judge_config or JUDGE_CONFIG
    fp = get_judge_fingerprint(endpoint_type, cfg, base_url, allow_non_authoritative=allow_non_authoritative)

    if endpoint_type == "openai_v1":
        from langchain_openai import ChatOpenAI
        url = base_url or "http://localhost:11434/v1"
        llm = ChatOpenAI(
            base_url=url,
            api_key="ollama",
            model=cfg["model"],
            temperature=cfg["temperature"],
            callbacks=callbacks or [],
            cache=False,
            model_kwargs={
                "extra_body": {
                    "options": {
                        "num_ctx": cfg["num_ctx"],
                        "seed": cfg["seed"],
                        "num_predict": 700,
                    },
                    "format": cfg["format"],
                }
            },
        )
    elif endpoint_type == "native_ollama":
        cls = NativeChatOllama.get_class()
        url = base_url or "http://localhost:11434"
        llm = cls(
            base_url=url,
            model=cfg["model"],
            temperature=cfg["temperature"],
            num_ctx=cfg["num_ctx"],
            num_predict=700,
            format=cfg["format"],
            seed=cfg["seed"],
            callbacks=callbacks or [],
        )
    else:
        raise ValueError(f"Unknown endpoint_type: {endpoint_type}. Must be 'openai_v1' or 'native_ollama'.")

    return llm, fp
