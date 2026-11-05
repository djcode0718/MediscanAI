"""
TraceableFaithfulness: RAGAS Faithfulness subclass exposing statement-level verdicts.

Lives in its own light module (no Pipeline / langchain-cache side effects) and is re-exported
from evaluation.e2e.run_eval for backward compatibility.

P1 changes (eval-repair):
  * ALL per-case state (statements, verdicts, case ids) is reset at the START of every case
    (begin_case() and again at the start of _ascore), not only on empty statements.
  * Every record carries the case_id it was produced for (last_statements_case_id /
    last_verdicts_case_id); the scorer asserts these equal the case being scored.
"""
from typing import Any, Optional

import numpy as np
from ragas.metrics._faithfulness import Faithfulness


class TraceableFaithfulness(Faithfulness):
    """Subclass of Ragas Faithfulness that exposes statement-level verdicts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_case_id: Optional[str] = None
        self.reset_case_state()

    def reset_case_state(self) -> None:
        """Drop every per-case artefact so nothing can leak from a previous case."""
        self.last_statements_output = None
        self.last_verdicts_output = None
        self.last_statements_case_id = None
        self.last_verdicts_case_id = None

    def begin_case(self, case_id: Optional[str]) -> None:
        """Declare which case is about to be scored and wipe all state from the previous one."""
        self.current_case_id = case_id
        self.reset_case_state()

    async def _ascore(self, row: dict, callbacks: Any) -> float:
        assert self.llm is not None, "LLM is not set"
        cid = self.current_case_id
        # Reset at the START of every scoring call (not only when statements are empty).
        self.reset_case_state()

        statements = await self._create_statements(row, callbacks)
        self.last_statements_output = statements
        self.last_statements_case_id = cid
        stmts = statements.statements
        if not stmts:
            self.last_verdicts_output = None
            self.last_verdicts_case_id = None
            return np.nan

        verdicts = await self._create_verdicts(row, stmts, callbacks)
        self.last_verdicts_output = verdicts
        self.last_verdicts_case_id = cid
        return self._compute_score(verdicts)
