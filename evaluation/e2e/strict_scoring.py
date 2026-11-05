"""
Strict per-case faithfulness scoring (P1 / eval-repair).

Contract: a case NEVER becomes 0, 1 or NaN silently.
  * RAGAS evaluate() is called with raise_exceptions=True, so judge/parse errors surface as exceptions.
  * Every exception is mapped to a status (parse failure / runtime error) and written with its full traceback to
    <run_dir>/errors.jsonl (one console line per problem).
  * Zero generated statements -> invalid_empty_statements; contamination guard -> invalid_contaminated.
  * Invalid results always have score=None. Only `valid` results carry a score.
Judge prompt/response pairs are written by evaluation.e2e.judge_io.JudgeIOTracker (attach it to the judge LLM).
"""
from __future__ import annotations

import json
import math
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from datasets import Dataset
from ragas.evaluation import evaluate
from ragas.run_config import RunConfig

from evaluation.e2e.contamination_guard import EVAL_GUARD_VERSION, check_contamination, load_example_strings
from evaluation.e2e.eval_status import CaseResult, EvalStatus
from evaluation.e2e.statement_diagnostics import compute_best_fuzzy_match, is_boilerplate_statement

DEFAULT_RUN_CONFIG = dict(max_workers=1, timeout=600, max_retries=2)  # identical to the previous production scorer


def _is_parse_failure(exc: BaseException) -> bool:
    """Output-parser style failures (ragas / langchain / json / pydantic), looking through exception chains."""
    from langchain_core.exceptions import OutputParserException
    from pydantic import ValidationError
    from ragas.exceptions import RagasOutputParserException

    kinds = (RagasOutputParserException, OutputParserException, json.JSONDecodeError, ValidationError)
    seen, cur = set(), exc
    while cur is not None and id(cur) not in seen:
        if isinstance(cur, kinds):
            return True
        seen.add(id(cur))
        cur = cur.__cause__ or cur.__context__
    return False


def _append_jsonl(path: Optional[Path], row: Dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def _report_problem(res: CaseResult, run_dir: Optional[Path], tb: Optional[str]) -> None:
    print(
        f"[eval:{res.status.value}] {res.case_id} | {res.error_class or '-'}: "
        f"{(res.error_message or '').splitlines()[0][:160] if res.error_message else '-'} "
        f"| judge_calls={res.judge_call_count} retries={res.retries}"
    )
    _append_jsonl(
        (Path(run_dir) / "errors.jsonl") if run_dir else None,
        {
            "case_id": res.case_id,
            "status": res.status.value,
            "error_class": res.error_class,
            "error_message": res.error_message,
            "traceback": tb,
            "warnings": res.warnings,
            "judge_call_count": res.judge_call_count,
            "retries": res.retries,
            "guard_version": EVAL_GUARD_VERSION,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    )


def score_case_strict(
    record: Dict[str, Any],
    custom_faithfulness: Any,
    judge_wrapper: Any,
    *,
    tracker: Any = None,
    run_dir: Optional[Path] = None,
    run_config: Optional[RunConfig] = None,
    example_strings: Optional[List[str]] = None,
) -> CaseResult:
    cid = record["case_id"]
    category = record.get("category")
    ans_core = (record.get("answer_core") or "").strip()
    contexts = record.get("retrieved_contexts", [])
    user_text = record.get("user_text", "") or f"Analyze medication: {record.get('ocr_text', '')}"
    response = ans_core if ans_core else "No answer provided."

    # ---- per-case reset (statements, verdicts, raw judge I/O counters) BEFORE any judge call
    custom_faithfulness.begin_case(cid)
    if tracker is not None:
        tracker.begin_case(cid)

    ragas_ds = Dataset.from_dict({
        "question": [user_text],
        "response": [response],
        "retrieved_contexts": [contexts],
    })
    run_cfg = run_config or RunConfig(**DEFAULT_RUN_CONFIG)

    def finish(status: EvalStatus, score=None, warnings=None, err_cls=None, err_msg=None, tb=None, statements=None, unsupported=None, guard=None, statement_details=None):
        res = CaseResult(
            case_id=cid, status=status, score=score, warnings=list(warnings or []),
            error_class=err_cls, error_message=err_msg,
            judge_call_count=(tracker.case_calls if tracker is not None else 0),
            retries=(tracker.case_retries() if tracker is not None else 0),
            statements=list(statements or []), statement_details=list(statement_details or []),
            unsupported=list(unsupported or []),
            category=category, guard_version=EVAL_GUARD_VERSION,
        )
        if status is not EvalStatus.valid:
            _report_problem(res, run_dir, tb)
        return res

    # Warn if a global LangChain LLM cache could answer judge calls without hitting the model.
    pre_warnings: List[str] = []
    try:
        from langchain_core.globals import get_llm_cache
        llm_cache_flag = getattr(getattr(judge_wrapper, "langchain_llm", None), "cache", None)
        if get_llm_cache() is not None and llm_cache_flag is not False:
            pre_warnings.append("langchain_global_llm_cache_active: judge responses may come from the cache")
    except Exception:
        pass

    # ---- run RAGAS with raise_exceptions=True
    try:
        scores_df = evaluate(
            dataset=ragas_ds,
            metrics=[custom_faithfulness],
            llm=judge_wrapper,
            run_config=run_cfg,
            show_progress=False,
            raise_exceptions=True,
        ).to_pandas()
    except Exception as e:  # noqa: BLE001 -- every exception is mapped to a status
        tb = traceback.format_exc()
        status = EvalStatus.invalid_parse_failure if _is_parse_failure(e) else EvalStatus.error_runtime
        return finish(status, warnings=pre_warnings, err_cls=type(e).__name__, err_msg=str(e) or repr(e), tb=tb)

    try:
        # ---- state integrity: every record must belong to THIS case
        st_out = custom_faithfulness.last_statements_output
        stmts: List[str] = list(st_out.statements) if st_out is not None else []
        if custom_faithfulness.last_statements_case_id != cid or (
            custom_faithfulness.last_verdicts_output is not None and custom_faithfulness.last_verdicts_case_id != cid
        ):
            raise AssertionError(
                f"state mismatch for {cid}: statements_case_id={custom_faithfulness.last_statements_case_id!r}, "
                f"verdicts_case_id={custom_faithfulness.last_verdicts_case_id!r}"
            )

        if not stmts:
            return finish(EvalStatus.invalid_empty_statements, warnings=pre_warnings, err_cls="EmptyStatements",
                          err_msg="judge produced zero statements for the answer")

        verdicts = custom_faithfulness.last_verdicts_output
        v_list = list(verdicts.statements) if verdicts is not None else []
        if not v_list:
            return finish(EvalStatus.invalid_parse_failure, warnings=pre_warnings, err_cls="EmptyVerdicts",
                          err_msg="NLI step returned zero verdicts", statements=stmts)

        warnings = list(pre_warnings)
        if len(v_list) != len(stmts):
            warnings.append(f"verdict_count_mismatch: {len(v_list)} verdicts for {len(stmts)} statements")

        statement_details = [
            {"statement": v.statement, "verdict": int(v.verdict), "reason": v.reason}
            for v in v_list
        ]

        # ---- contamination guard
        guard = check_contamination(stmts, response, example_strings if example_strings is not None else load_example_strings(custom_faithfulness))
        warnings.extend(guard.warnings)
        if guard.contaminated:
            return finish(EvalStatus.invalid_contaminated, warnings=warnings, err_cls="Contaminated",
                          err_msg="; ".join(guard.reasons), statements=stmts, statement_details=statement_details)

        # ---- score (recomputed from verdicts and cross-checked against RAGAS' own number)
        computed = custom_faithfulness._compute_score(verdicts)
        df_score = scores_df.iloc[0].get("faithfulness")
        if computed is None or (isinstance(computed, float) and math.isnan(computed)):
            raise ValueError("score is NaN although statements and verdicts exist")
        if df_score is not None and not (isinstance(df_score, float) and math.isnan(df_score)) and abs(float(df_score) - float(computed)) > 1e-9:
            raise ValueError(f"score mismatch between ragas ({df_score}) and recomputed ({computed})")

        unsupported = []
        for v in v_list:
            if int(v.verdict) == 0 and not is_boilerplate_statement(v.statement):
                unsupported.append({
                    "case_id": cid, "statement": v.statement, "reason": v.reason,
                    "fuzzy_score": compute_best_fuzzy_match(v.statement, contexts),
                })
        return finish(EvalStatus.valid, score=round(float(computed), 4), warnings=warnings, statements=stmts, statement_details=statement_details, unsupported=unsupported)
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        return finish(EvalStatus.error_runtime, warnings=pre_warnings, err_cls=type(e).__name__, err_msg=str(e) or repr(e), tb=tb)
