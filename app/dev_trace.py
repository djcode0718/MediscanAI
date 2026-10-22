# app/dev_trace.py
"""
Opt-in development trace for the RAG pipeline (DEV_TRACE_ENABLED=true).

Records the exact assembled prompt metrics, effective model/context settings, the token
budget, per-stage retrieval candidates (dense / BM25 / fused / reranked), the final evidence
and the reason each retrieved block was not shown.

Privacy: by default no user text, OCR text, prompt or evidence text is stored; only
SHA-256 prefixes, lengths, ids, scores and token counts. Set DEV_TRACE_INCLUDE_TEXT=true to
include prompt text (it contains the user's input, so use only with synthetic data).
Secrets/API keys are never part of the trace.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants mirrored from Pipeline.run's compact budget formula (kept in sync by a unit test).
SAFETY_MARGIN_TOKENS = 256
INSTRUCTION_RESERVE_TOKENS = 500


def count_tokens(text: str) -> int:
    """cl100k_base estimate (diagnostic only; Ollama's prompt_eval_count is authoritative)."""
    if not text:
        return 0
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _redact(text: Optional[str]) -> Dict[str, Any]:
    text = text or ""
    return {
        "sha256_16": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "chars": len(text),
    }


def derive_omission_reasons(
    retrieved_ids_per_channel: Dict[str, List[str]],
    evidence_items: List[Dict[str, Any]],
    trims: List[Dict[str, Any]],
    max_items_per_channel: int,
) -> Dict[str, str]:
    """Explain, for each retrieved id that is not itself a shown block, why it is not shown."""
    shown_primary = {str(i["id"]) for i in evidence_items}
    merged_into: Dict[str, str] = {}
    for it in evidence_items:
        for cid in it.get("covers_ids", []):
            if str(cid) != str(it["id"]):
                merged_into[str(cid)] = str(it["id"])
    dropped_by_budget = {str(t["dropped_id"]) for t in trims if t.get("action") == "drop_item"}

    reasons: Dict[str, str] = {}
    for ch, ids in retrieved_ids_per_channel.items():
        for rid in ids:
            rid = str(rid)
            bare = rid.replace("drug_dict_", "").replace("drug_", "")
            if rid in shown_primary or bare in shown_primary:
                continue
            if rid in dropped_by_budget or bare in dropped_by_budget:
                reasons[rid] = "token_budget_drop"
            elif rid in merged_into or bare in merged_into:
                reasons[rid] = f"merged_duplicate_into:{merged_into.get(rid) or merged_into.get(bare)}"
            else:
                reasons[rid] = f"per_channel_cap(max_items={max_items_per_channel})_or_dedup_rank"
    return reasons


def build_dev_trace(
    *,
    user_text: str,
    ocr_text: str,
    system_prompt: Optional[str],
    full_prompt: str,
    evidence_trace: Optional[Dict[str, Any]],
    retrieval_debug: Dict[str, Dict[str, Any]],
    retrieved_ids: Dict[str, List[str]],
    effective: Dict[str, Any],
    token_budget: Optional[int],
    max_items_per_channel: int,
    case_type: Optional[str],
    generation_meta: Optional[Dict[str, Any]],
    include_text: bool = False,
) -> Dict[str, Any]:
    items = (evidence_trace or {}).get("evidence_items", [])
    trims = (evidence_trace or {}).get("trims", [])

    ev_tokens_by_channel: Dict[str, int] = {}
    for it in items:
        ev_tokens_by_channel[it["channel"]] = ev_tokens_by_channel.get(it["channel"], 0) + int(it.get("tokens", 0))

    sys_tokens = count_tokens(system_prompt or "")
    user_msg_tokens = count_tokens(full_prompt)
    num_ctx = effective.get("num_ctx")
    num_predict = effective.get("num_predict")
    actual_prompt_eval = (generation_meta or {}).get("prompt_eval_count")

    budget = {
        "num_ctx": num_ctx,
        "num_predict_reserved_for_output": num_predict,
        "safety_margin": SAFETY_MARGIN_TOKENS,
        "instruction_reserve": INSTRUCTION_RESERVE_TOKENS,
        "evidence_token_budget": token_budget,
        "evidence_tokens_used": (evidence_trace or {}).get("total_evidence_tokens"),
        "evidence_tokens_by_channel": ev_tokens_by_channel,
        "system_prompt_tokens_est": sys_tokens,
        "user_message_tokens_est": user_msg_tokens,
        "total_input_tokens_est": sys_tokens + user_msg_tokens,
        "ollama_prompt_eval_count": actual_prompt_eval,
        "ollama_eval_count": (generation_meta or {}).get("eval_count"),
        "input_headroom_actual": (
            num_ctx - num_predict - actual_prompt_eval
            if None not in (num_ctx, num_predict, actual_prompt_eval) else None
        ),
        "estimator": "tiktoken cl100k_base (diagnostic; differs from Llama-3 tokenizer + chat template)",
        "evidence_budget_binding": bool(token_budget is not None and trims),
    }

    trace: Dict[str, Any] = {
        "case_type": case_type,
        "effective_settings": effective,
        "token_budget": budget,
        "retrieval_stages": retrieval_debug,
        "final_evidence": [
            {k: it[k] for k in ("tag", "id", "channel", "item_type", "tokens", "covers_ids")} for it in items
        ],
        "omitted": derive_omission_reasons(retrieved_ids, items, trims, max_items_per_channel),
        "evidence_trims": trims,
        "inputs": {
            "user_text": _redact(user_text),
            "ocr_text": _redact(ocr_text),
            "system_prompt": _redact(system_prompt),
            "full_prompt": _redact(full_prompt),
        },
    }
    if include_text:
        trace["prompt_text"] = {"system": system_prompt, "user_message": full_prompt}
    return trace


def write_dev_trace(trace: Dict[str, Any], trace_dir: str, tag: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tag)[:64] or "trace"
    out_dir = Path(trace_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{safe}.json"
    path.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
    return path
