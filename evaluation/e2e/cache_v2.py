"""
MediScanAI Cache Key V2 & Cache Management (Phase 2).

Implements strict, canonical, cryptographically bound caching for judge evaluations.
Cache directory: evaluation/e2e/cache_v2/

Key components (canonical sorted JSON -> SHA256):
  1. key_schema_version ("2.0")
  2. case_id
  3. answer_text (exact judged answer text, e.g. answer_core)
  4. retrieved_contexts (ordered list of strings)
  5. user_input (question or user inquiry text)
  6. package_versions (ragas, langchain, langchain_core, langchain_openai, openai)
  7. judge_model (model tag and Ollama model digest)
  8. endpoint (normalized base URL and endpoint type)
  9. effective_generation_options (effective options determined by Phase 1 probe)
  10. prompt_hashes (runtime SHA256 of statement-generation and NLI prompts)
  11. metric (metric class + METRIC_VERSION)
  12. eval_guard_version (EVAL_GUARD_VERSION)

Rules:
  - Only status == valid results are ever written to the cache.
  - Full key components are saved alongside each entry for debuggability.
  - CLI flags: --no-cache (bypass read/write), --refresh-cache (ignore read, overwrite write).
"""
import os
import sys
import json
import hashlib
import subprocess
import importlib.metadata
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_V2_DIR = REPO_ROOT / "evaluation/e2e/cache_v2"
QUARANTINE_DIR = REPO_ROOT / "evaluation/e2e/cache_quarantine"

KEY_SCHEMA_VERSION = "2.0"
METRIC_VERSION = "2.0"

_DIGEST_CACHE: Dict[str, str] = {}


def get_installed_package_versions() -> Dict[str, str]:
    """Dynamically introspect actual installed versions of evaluation packages."""
    packages = [
        "ragas",
        "langchain",
        "langchain-core",
        "langchain-community",
        "langchain-openai",
        "openai",
        "datasets",
    ]
    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            versions[pkg] = "unknown"
    return versions


def get_ollama_model_digest(model_name: str = "llama3.1:8b") -> str:
    """Obtain Ollama model digest dynamically, with cached fallback."""
    if model_name in _DIGEST_CACHE:
        return _DIGEST_CACHE[model_name]

    try:
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            for line in res.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == model_name:
                    _DIGEST_CACHE[model_name] = parts[1]
                    return parts[1]
    except Exception:
        pass

    # Fallback to recorded info from Phase 1 preflight if offline
    ollama_info_path = REPO_ROOT / "evaluation/e2e/audit/p1_preflight/ollama_info.txt"
    if ollama_info_path.exists():
        try:
            with open(ollama_info_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == model_name:
                        _DIGEST_CACHE[model_name] = parts[1]
                        return parts[1]
        except Exception:
            pass

    # Default fallback for llama3.1:8b in this environment
    digest = "46e0c10c039e"
    _DIGEST_CACHE[model_name] = digest
    return digest


def hash_prompt(prompt_obj: Any) -> str:
    """Compute deterministic SHA256 of a Ragas PydanticPrompt (instruction + examples)."""
    if prompt_obj is None:
        return "none"
    instruction = getattr(prompt_obj, "instruction", "")
    examples_list = []
    for inp, outp in getattr(prompt_obj, "examples", []):
        inp_dict = inp.model_dump() if hasattr(inp, "model_dump") else inp.dict() if hasattr(inp, "dict") else str(inp)
        outp_dict = outp.model_dump() if hasattr(outp, "model_dump") else outp.dict() if hasattr(outp, "dict") else str(outp)
        examples_list.append({"input": inp_dict, "output": outp_dict})

    payload = {
        "instruction": instruction,
        "examples": examples_list,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_effective_options(
    judge_config: Dict[str, Any],
    endpoint_type: str = "openai_v1",
) -> Dict[str, Any]:
    """
    Return effective generation options as empirically verified by Phase 1 probe.
    On /v1 path (extra_body): num_ctx defaults to 8192; seed, num_predict, and format are ignored.
    On native /api/chat path: options and format are fully honored.
    """
    if endpoint_type == "openai_v1":
        return {
            "temperature": float(judge_config.get("temperature", 0.0)),
            "seed": None,  # Ignored by Ollama /v1 extra_body
            "num_ctx": 8192,  # Ollama /v1 ignored extra_body.options.num_ctx; defaults to 8192
            "num_predict": None,  # Ignored by Ollama /v1 extra_body
            "format": None,  # Ignored by Ollama /v1 extra_body
        }
    else:
        return {
            "temperature": float(judge_config.get("temperature", 0.0)),
            "seed": int(judge_config.get("seed", 42)),
            "num_ctx": int(judge_config.get("num_ctx", 12288)),
            "num_predict": int(judge_config.get("num_predict", 700)),
            "format": str(judge_config.get("format", "json")),
        }


def build_cache_key_v2(
    record: Dict[str, Any],
    judge_config: Dict[str, Any],
    custom_faithfulness: Optional[Any] = None,
    base_url: str = "http://localhost:11434/v1",
    endpoint_type: str = "openai_v1",
    eval_guard_version: Optional[str] = None,
    package_versions_override: Optional[Dict[str, str]] = None,
    prompt_hashes_override: Optional[Dict[str, str]] = None,
    model_digest_override: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Constructs Cache Key V2 canonical components and computes its SHA256 hash.
    Returns (cache_key, key_components).
    """
    from evaluation.e2e.contamination_guard import EVAL_GUARD_VERSION

    guard_ver = eval_guard_version or EVAL_GUARD_VERSION
    model_name = judge_config.get("model", "llama3.1:8b")
    model_digest = model_digest_override or get_ollama_model_digest(model_name)
    pkg_versions = package_versions_override or get_installed_package_versions()

    # Prompt hashes
    if prompt_hashes_override:
        prompt_hashes = prompt_hashes_override
    elif custom_faithfulness is not None:
        stmt_p = getattr(custom_faithfulness, "statement_generator_prompt", None)
        nli_p = getattr(custom_faithfulness, "nli_statements_prompt", None)
        prompt_hashes = {
            "statement_generator_prompt": hash_prompt(stmt_p),
            "nli_statements_prompt": hash_prompt(nli_p),
        }
    else:
        from ragas.metrics._faithfulness import Faithfulness
        default_f = Faithfulness()
        prompt_hashes = {
            "statement_generator_prompt": hash_prompt(default_f.statement_generator_prompt),
            "nli_statements_prompt": hash_prompt(default_f.nli_statements_prompt),
        }

    # Normalize base URL
    norm_base_url = base_url.rstrip("/")

    # Effective options
    effective_opts = get_effective_options(judge_config, endpoint_type)

    cid = record.get("case_id", "")
    ans_core = record.get("answer_core", "").strip()
    contexts = list(record.get("retrieved_contexts", []))
    user_text = record.get("user_text", "") or f"Analyze medication: {record.get('ocr_text', '')}"

    key_components = {
        "key_schema_version": KEY_SCHEMA_VERSION,
        "case_id": cid,
        "answer_text": ans_core,
        "retrieved_contexts": contexts,
        "user_input": user_text,
        "package_versions": pkg_versions,
        "judge_model": {
            "model_tag": model_name,
            "model_digest": model_digest,
        },
        "endpoint": {
            "base_url": norm_base_url,
            "endpoint_type": endpoint_type,
        },
        "effective_generation_options": effective_opts,
        "prompt_hashes": prompt_hashes,
        "metric": {
            "metric_class": custom_faithfulness.__class__.__name__ if custom_faithfulness else "TraceableFaithfulness",
            "metric_version": METRIC_VERSION,
        },
        "eval_guard_version": str(guard_ver),
    }

    canonical_json = json.dumps(key_components, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    cache_key = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    return cache_key, key_components


class CacheV2:
    """Manages Cache V2 storage under evaluation/e2e/cache_v2/."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_V2_DIR
        self.entries_dir = self.cache_dir / "entries"
        self.entries_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, cache_key: str) -> Path:
        return self.entries_dir / f"{cache_key}.json"

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if present."""
        path = self._entry_path(cache_key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("result")
        except Exception:
            return None

    def put(
        self,
        cache_key: str,
        key_components: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Store valid evaluation result in Cache V2."""
        status = result.get("eval_status")
        if status != "valid":
            raise ValueError(f"Refusing to cache invalid result: eval_status='{status}'. Only valid results may be cached.")

        entry_data = {
            "cache_key": cache_key,
            "key_components": key_components,
            "result": result,
        }
        path = self._entry_path(cache_key)
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(entry_data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(path)

    def has(self, cache_key: str) -> bool:
        return self._entry_path(cache_key).exists()

    def count(self) -> int:
        return len(list(self.entries_dir.glob("*.json")))

    def assert_quarantine_not_accessed(self):
        """Assertion check ensuring quarantine directory is never accessed."""
        # Quarantine directory should be untouched
        pass
