"""
Judge I/O tracker (P1 / eval-repair).

Superset of run_a6_1_evaluation.JudgeUsageTracker (same counters: total_calls, total_input_tokens,
total_output_tokens, case_calls, case_input_tokens, case_output_tokens, case_latency_ms, reset_case())
that ALSO appends EVERY judge call to <run_dir>/judge_io.jsonl with: case_id, metric step, full prompt
text, full raw response text, latency, token counts, retry index, exception class/message, UTC timestamp.
No redaction and no truncation.

Kept in its own light module (only langchain_core) so offline tests do not import the Pipeline.
"""
from __future__ import annotations

import json
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


def _load_step_markers() -> Dict[str, str]:
    """Instruction strings are read from the INSTALLED ragas at runtime (not hard-copied)."""
    from ragas.metrics._faithfulness import NLIStatementPrompt, StatementGeneratorPrompt
    from ragas.prompt.pydantic_prompt import FixOutputFormat
    return {
        "fix_output_format": FixOutputFormat.instruction,
        "statement_generation": StatementGeneratorPrompt.instruction,
        "NLI": NLIStatementPrompt.instruction,
    }


def classify_step(prompt_text: str, _markers: Optional[Dict[str, str]] = None) -> str:
    """Return statement_generation | NLI | fix_output_format | other.

    fix_output_format is tested first: that prompt embeds the ORIGINAL prompt (and therefore the other
    instructions and few-shot examples) inside itself.
    """
    markers = _markers or _load_step_markers()
    head = prompt_text or ""
    for step in ("fix_output_format", "statement_generation", "NLI"):
        if markers[step] in head:
            return step
    return "other"


def _extract_usage(response: Any) -> Dict[str, Optional[int]]:
    pt = ct = None
    llm_output = getattr(response, "llm_output", None) or {}
    usage = llm_output.get("token_usage") or {}
    if usage:
        pt, ct = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if pt is None and ct is None:
        try:
            msg = response.generations[0][0].message
            um = getattr(msg, "usage_metadata", None) or {}
            pt, ct = um.get("input_tokens"), um.get("output_tokens")
        except Exception:
            pass
    return {"prompt_tokens": pt, "completion_tokens": ct}


class JudgeIOTracker(BaseCallbackHandler):
    raise_error = False  # never let logging break scoring

    def __init__(self, io_path: Optional[Path] = None):
        super().__init__()
        self.io_path = Path(io_path) if io_path else None
        if self.io_path:
            self.io_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._markers = _load_step_markers()
        self._pending: Dict[UUID, Dict[str, Any]] = {}
        self.rows: List[Dict[str, Any]] = []  # in-memory mirror of what is written to judge_io.jsonl

        # JudgeUsageTracker-compatible counters
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.case_calls = 0
        self.case_input_tokens = 0
        self.case_output_tokens = 0
        self.case_start_t: Optional[float] = None
        self.case_latency_ms = 0

        self.current_case_id: Optional[str] = None
        self._step_counts: Counter = Counter()

    # ----- per-case lifecycle
    def reset_case(self):
        self.case_calls = 0
        self.case_input_tokens = 0
        self.case_output_tokens = 0
        self.case_start_t = time.time()
        self.case_latency_ms = 0
        self._step_counts = Counter()

    def begin_case(self, case_id: str):
        self.current_case_id = case_id
        self.reset_case()

    def case_retries(self) -> int:
        """Retries = repeated calls of the same main step + every fix_output_format call."""
        n = 0
        for step, cnt in self._step_counts.items():
            n += cnt if step == "fix_output_format" else max(0, cnt - 1)
        return n

    # ----- callbacks
    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[Any]], *, run_id: UUID, **kwargs: Any) -> None:
        flat = [m for batch in messages for m in batch]
        msg_dicts = [{"role": getattr(m, "type", "unknown"), "content": m.content if isinstance(m.content, str) else json.dumps(m.content)} for m in flat]
        text = "\n".join(d["content"] for d in msg_dicts)
        self._start(run_id, text, msg_dicts, kwargs)

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, **kwargs: Any) -> None:
        self._start(run_id, "\n".join(prompts), [{"role": "prompt", "content": p} for p in prompts], kwargs)

    def _start(self, run_id: UUID, text: str, msgs: List[Dict[str, str]], kwargs: Dict[str, Any]) -> None:
        step = classify_step(text, self._markers)
        self._step_counts[step] += 1
        self.case_calls += 1
        self.total_calls += 1
        self._pending[run_id] = {
            "case_id": self.current_case_id,
            "step": step,
            "prompt_text": text,
            "messages": msgs,
            "retry_index": self._step_counts[step] - 1,
            "t0": time.time(),
            "call_index": self.case_calls,
        }

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        p = self._pending.pop(run_id, None)
        if p is None:
            return
        try:
            raw = response.generations[0][0].text
        except Exception:
            raw = None
        usage = _extract_usage(response)
        in_tok, out_tok = usage["prompt_tokens"] or 0, usage["completion_tokens"] or 0
        self.case_input_tokens += in_tok
        self.case_output_tokens += out_tok
        self.total_input_tokens += in_tok
        self.total_output_tokens += out_tok
        if self.case_start_t:
            self.case_latency_ms = int((time.time() - self.case_start_t) * 1000)
        self._write(p, raw, usage, None)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        p = self._pending.pop(run_id, None)
        if p is None:
            return
        self._write(p, None, {"prompt_tokens": None, "completion_tokens": None}, error)

    def _write(self, p: Dict[str, Any], raw: Optional[str], usage: Dict[str, Optional[int]], err: Optional[BaseException]) -> None:
        row = {
            "case_id": p["case_id"],
            "step": p["step"],
            "call_index": p["call_index"],
            "retry_index": p["retry_index"],
            "prompt_text": p["prompt_text"],
            "messages": p["messages"],
            "response_text": raw,
            "latency_ms": int((time.time() - p["t0"]) * 1000),
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "exception_class": type(err).__name__ if err else None,
            "exception_message": str(err) if err else None,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self.rows.append(row)
            if self.io_path:
                with open(self.io_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
