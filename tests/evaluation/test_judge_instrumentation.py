"""
Offline tests for P1 judge instrumentation (no Ollama, no network): fake judge LLM objects only.

Fixtures (copied, never moved, from evaluation/e2e/results/A6_1/ saved results) live in tests/fixtures/.
"""
import json
import math
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig

# NOTE: score_candidate imports run_eval which installs a global SQLite LLM cache at import time.
# The autouse fixture below nulls it so no fake response can ever be written to the real cache file.
from evaluation.e2e import score_candidate as sc
from evaluation.e2e.contamination_guard import EVAL_GUARD_VERSION, check_contamination, load_example_strings
from evaluation.e2e.eval_status import CaseResult, EvalStatus, aggregate_results
from evaluation.e2e.judge_io import JudgeIOTracker, classify_step
from evaluation.e2e.strict_scoring import score_case_strict
from evaluation.e2e.traceable_faithfulness import TraceableFaithfulness

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
FAST_CFG = dict(max_workers=1, timeout=60, max_retries=1, max_wait=1)


def load_fixture(case_id: str) -> dict:
    return json.loads((FIXTURES / f"a6_1_{case_id}.json").read_text())


def e2e080_statements() -> List[str]:
    rows = [json.loads(l) for l in (FIXTURES / "a6_1_E2E-080_unsupported.jsonl").read_text().splitlines() if l.strip()]
    return [r["statement"] for r in rows]


@pytest.fixture(autouse=True)
def _no_global_llm_cache(monkeypatch):
    import langchain
    from langchain_core.globals import set_llm_cache

    monkeypatch.setattr(langchain, "llm_cache", None, raising=False)
    set_llm_cache(None)
    yield
    set_llm_cache(None)


class ScriptedChatModel(BaseChatModel):
    """Fake judge: handler(step, prompt_text, call_idx) -> response text (or raises)."""

    handler: Any = None
    calls: List[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def _respond(self, messages) -> ChatResult:
        text = "\n".join(m.content for m in messages)
        step = classify_step(text)
        self.calls.append(step)
        out = self.handler(step, text, len(self.calls) - 1)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=out), generation_info={"finish_reason": "stop"})],
                          llm_output={"token_usage": {"prompt_tokens": len(text) // 4, "completion_tokens": len(out) // 4}})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._respond(messages)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._respond(messages)


def stmt_json(statements: List[str]) -> str:
    return json.dumps({"statements": statements})


def nli_json(statements: List[str], verdicts: List[int]) -> str:
    return json.dumps({"statements": [{"statement": s, "reason": "scripted", "verdict": v} for s, v in zip(statements, verdicts)]})


def make_env(tmp_path: Path, handler: Callable, faith_cls=TraceableFaithfulness):
    tracker = JudgeIOTracker(tmp_path / "judge_io.jsonl")
    fake = ScriptedChatModel(handler=handler, callbacks=[tracker], cache=False)
    wrapper = LangchainLLMWrapper(fake)
    faith = faith_cls(llm=wrapper)
    return tracker, fake, wrapper, faith


def io_rows(tmp_path: Path) -> List[dict]:
    p = tmp_path / "judge_io.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def err_rows(tmp_path: Path) -> List[dict]:
    p = tmp_path / "errors.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def score(tmp_path, record, handler, faith_cls=TraceableFaithfulness):
    tracker, fake, wrapper, faith = make_env(tmp_path, handler, faith_cls)
    res = score_case_strict(record, faith, wrapper, tracker=tracker, run_dir=tmp_path, run_config=RunConfig(**FAST_CFG))
    return res, tracker, faith, wrapper


def good_handler_for(record: dict, verdicts: Optional[List[int]] = None):
    sents = [s.strip() + "." for s in record["answer_core"].split(". ") if s.strip()][:3]
    sents = [s.rstrip(".") + "." for s in sents]
    verdicts = verdicts or [1] * len(sents)

    def h(step, text, idx):
        if step == "statement_generation":
            return stmt_json(sents)
        if step == "NLI":
            return nli_json(sents, verdicts)
        return "{}"
    return h, sents, verdicts


# ---------------------------------------------------------------------------
# E2E-080: statements == the RAGAS few-shot example -> contaminated
# ---------------------------------------------------------------------------

def test_e2e080_example_statements_are_contaminated_and_never_cached(tmp_path, monkeypatch):
    rec = load_fixture("E2E-080")
    einstein = e2e080_statements()
    assert len(einstein) == 4 and "Einstein" in einstein[0]

    def h(step, text, idx):
        if step == "statement_generation":
            return stmt_json(einstein)
        if step == "NLI":
            return nli_json(einstein, [0, 0, 0, 0])
        return "{}"

    saved = []
    monkeypatch.setattr(sc, "save_cache", lambda c: saved.append(dict(c)))
    tracker, fake, wrapper, faith = make_env(tmp_path, h)
    cache: dict = {}
    res = sc.score_faithfulness_strict_candidate(rec, faith, wrapper, cache, tracker=tracker, run_dir=tmp_path,
                                                 run_config=RunConfig(**FAST_CFG))
    assert res.status is EvalStatus.invalid_contaminated
    assert res.score is None
    assert "example_statement_reproduced" in (res.error_message or "")
    assert cache == {} and saved == []  # nothing cached
    rows = io_rows(tmp_path)
    assert {r["step"] for r in rows} >= {"statement_generation", "NLI"}
    assert any("Einstein" in (r["response_text"] or "") for r in rows)  # raw IO persisted
    assert all(r["case_id"] == "E2E-080" for r in rows)
    errs = err_rows(tmp_path)
    assert errs and errs[0]["status"] == "invalid_contaminated"


# ---------------------------------------------------------------------------
# E2E-062: malformed outputs -> invalid_parse_failure, raw text saved, score null
# ---------------------------------------------------------------------------

MALFORMED = {
    "fenced_truncated_json": "```json\n{\"statements\": [\"Joette Calabrese Survivalist Kit is labeled for confusion\", \n```",
    "truncated_json": "{\"statements\": [\"Joette Calabrese Survivalist Kit is labeled for conf",
    "bad_escape": "{\"statements\": [\"label says \\q invalid escape\"]}",
    "prose_not_json": "Sure! Here are the statements you asked for, in plain prose without any JSON.",
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_e2e062_malformed_outputs_are_parse_failures(tmp_path, name):
    rec = load_fixture("E2E-062")
    bad = MALFORMED[name]
    res, tracker, faith, _ = score(tmp_path, rec, lambda step, text, idx: bad)  # fix_output_format retries also garbage
    assert res.status is EvalStatus.invalid_parse_failure, (name, res.status, res.error_class, res.error_message)
    assert res.score is None
    assert res.error_class and res.error_message is not None
    rows = io_rows(tmp_path)
    assert rows and all(r["response_text"] is not None for r in rows)
    assert any(r["response_text"] == bad for r in rows)  # raw text stored verbatim
    assert any(r["step"] == "fix_output_format" for r in rows)  # retries visible
    assert res.retries >= 1 and res.judge_call_count == len(rows)
    errs = err_rows(tmp_path)
    assert errs and errs[0]["status"] == "invalid_parse_failure" and errs[0]["traceback"]


def test_fenced_but_valid_json_is_accepted_by_ragas_parser(tmp_path):
    """Documents real parser behaviour: a fenced block with VALID JSON parses fine (not a parse failure)."""
    rec = load_fixture("E2E-035")
    h, sents, _ = good_handler_for(rec)
    fenced = lambda s: "```json\n" + s + "\n```"

    def h2(step, text, idx):
        return fenced(h(step, text, idx))

    res, *_ = score(tmp_path, rec, h2)
    assert res.status is EvalStatus.valid, (res.status, res.error_class, res.error_message)


# ---------------------------------------------------------------------------
# Empty statements
# ---------------------------------------------------------------------------

def test_empty_statements_invalid(tmp_path):
    rec = load_fixture("E2E-035")
    res, tracker, faith, _ = score(tmp_path, rec, lambda step, text, idx: stmt_json([]))
    assert res.status is EvalStatus.invalid_empty_statements
    assert res.score is None
    assert faith.last_verdicts_output is None
    assert err_rows(tmp_path)[0]["status"] == "invalid_empty_statements"


# ---------------------------------------------------------------------------
# Stale state
# ---------------------------------------------------------------------------

def test_stale_state_is_reset_between_cases(tmp_path):
    a = load_fixture("E2E-035")
    b = dict(load_fixture("E2E-062"))
    h_a, sents, _ = good_handler_for(a)

    def handler(step, text, idx):
        if "Joette" in text:  # case B -> judge blows up
            raise RuntimeError("judge exploded for case B")
        return h_a(step, text, idx)

    tracker, fake, wrapper, faith = make_env(tmp_path, handler)
    cfg = RunConfig(**FAST_CFG)
    res_a = score_case_strict(a, faith, wrapper, tracker=tracker, run_dir=tmp_path, run_config=cfg)
    assert res_a.status is EvalStatus.valid and faith.last_verdicts_case_id == "E2E-035"
    res_b = score_case_strict(b, faith, wrapper, tracker=tracker, run_dir=tmp_path, run_config=cfg)
    assert res_b.status is EvalStatus.error_runtime
    assert res_b.score is None
    assert faith.last_verdicts_output is None and faith.last_verdicts_case_id is None  # nothing inherited from A
    assert faith.last_statements_output is None
    assert "exploded" in (res_b.error_message or "")


def test_case_id_mismatch_is_error_runtime(tmp_path):
    class StaleFaith(TraceableFaithfulness):
        async def _ascore(self, row, callbacks):
            r = await super()._ascore(row, callbacks)
            self.last_verdicts_case_id = "SOME-OTHER-CASE"  # simulate inherited verdicts
            return r

    rec = load_fixture("E2E-035")
    h, *_ = good_handler_for(rec)
    res, *_ = score(tmp_path, rec, h, faith_cls=StaleFaith)
    assert res.status is EvalStatus.error_runtime
    assert res.error_class == "AssertionError" and "state mismatch" in res.error_message


# ---------------------------------------------------------------------------
# Valid case
# ---------------------------------------------------------------------------

def test_valid_case_scored_and_judge_io_rows_present(tmp_path):
    rec = load_fixture("E2E-035")
    h, sents, verdicts = good_handler_for(rec, verdicts=[1, 1, 0][: len(good_handler_for(rec)[1])])
    res, tracker, faith, _ = score(tmp_path, rec, h)
    assert res.status is EvalStatus.valid
    n = len(sents)
    assert res.score == pytest.approx(round(sum(verdicts) / n, 4))
    assert res.judge_call_count == 2 and res.retries == 0
    rows = io_rows(tmp_path)
    assert [r["step"] for r in rows] == ["statement_generation", "NLI"]
    for r in rows:
        assert r["case_id"] == "E2E-035"
        assert r["prompt_text"] and r["response_text"]
        assert r["latency_ms"] >= 0 and r["retry_index"] == 0
        assert r["exception_class"] is None and r["timestamp_utc"].endswith("+00:00")
        assert r["prompt_tokens"] is not None and r["completion_tokens"] is not None
    assert faith.last_verdicts_case_id == "E2E-035"
    assert not err_rows(tmp_path)  # valid -> no error row
    assert res.guard_version == EVAL_GUARD_VERSION == "1"


def test_valid_result_is_cached_and_cache_written_once(tmp_path, monkeypatch):
    rec = load_fixture("E2E-035")
    h, *_ = good_handler_for(rec)
    saved = []
    monkeypatch.setattr(sc, "save_cache", lambda c: saved.append(dict(c)))
    tracker, fake, wrapper, faith = make_env(tmp_path, h)
    cache: dict = {}
    res = sc.score_faithfulness_strict_candidate(rec, faith, wrapper, cache, tracker=tracker, run_dir=tmp_path, run_config=RunConfig(**FAST_CFG))
    assert res.status is EvalStatus.valid and len(cache) == 1 and len(saved) == 1
    # bypass: no read, no write
    cache2: dict = {}
    res2 = sc.score_faithfulness_strict_candidate(rec, faith, wrapper, cache2, tracker=tracker, run_dir=tmp_path, bypass_cache=True, run_config=RunConfig(**FAST_CFG))
    assert res2.status is EvalStatus.valid and cache2 == {} and len(saved) == 1


@pytest.mark.parametrize("kind", ["parse", "empty", "runtime"])
def test_invalid_results_never_written_to_cache(tmp_path, monkeypatch, kind):
    rec = load_fixture("E2E-035")

    def handler(step, text, idx):
        if kind == "parse":
            return "not json at all"
        if kind == "empty":
            return stmt_json([])
        raise RuntimeError("boom")

    saved = []
    monkeypatch.setattr(sc, "save_cache", lambda c: saved.append(1))
    tracker, fake, wrapper, faith = make_env(tmp_path, handler)
    cache: dict = {}
    res = sc.score_faithfulness_strict_candidate(rec, faith, wrapper, cache, tracker=tracker, run_dir=tmp_path, run_config=RunConfig(**FAST_CFG))
    assert not res.is_valid and res.score is None
    assert cache == {} and saved == []
    # legacy tuple API: NaN only as placeholder, with status + cause recorded, still uncached
    score_val, unsupp, reasons = sc.score_faithfulness_single_candidate(rec, faith, wrapper, cache, tracker=tracker, run_dir=tmp_path)
    assert math.isnan(score_val) and reasons["eval_status"] == res.status.value and cache == {} and saved == []


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def test_aggregator_excludes_invalid_and_reports_counts():
    rs = [
        CaseResult("A", EvalStatus.valid, 1.0, category="x"),
        CaseResult("B", EvalStatus.valid, 0.5, category="x"),
        CaseResult("C", EvalStatus.invalid_contaminated, None, category="y", error_class="Contaminated"),
        CaseResult("D", EvalStatus.invalid_parse_failure, None, category="y"),
        CaseResult("E", EvalStatus.invalid_empty_statements, None, category="y"),
        CaseResult("F", EvalStatus.error_runtime, None, category="y"),
    ]
    agg = aggregate_results(rs)
    assert agg["n_total"] == 6 and agg["n_valid"] == 2 and agg["n_invalid"] == 4
    assert agg["mean_valid"] == 0.75
    assert agg["n_invalid_by_status"] == {"invalid_parse_failure": 1, "invalid_empty_statements": 1, "invalid_contaminated": 1, "error_runtime": 1}
    assert agg["per_category"]["y"]["n_valid"] == 0 and agg["per_category"]["y"]["mean_valid"] is None
    assert aggregate_results([])["mean_valid"] is None


def test_invalid_case_cannot_carry_a_score_and_valid_needs_one():
    with pytest.raises(ValueError):
        CaseResult("X", EvalStatus.invalid_parse_failure, 0.0)
    with pytest.raises(ValueError):
        CaseResult("X", EvalStatus.valid, None)
    with pytest.raises(ValueError):
        CaseResult("X", EvalStatus.valid, float("nan"))


# ---------------------------------------------------------------------------
# Contamination guard
# ---------------------------------------------------------------------------

def test_example_strings_are_loaded_from_installed_ragas():
    ex = load_example_strings()
    assert "Albert Einstein was a German-born theoretical physicist." in ex  # statement-generation example
    assert "John is a dedicated student." in ex  # NLI example
    import inspect, evaluation.e2e.contamination_guard as g
    assert "Albert Einstein" not in inspect.getsource(g)  # never hard-copied into the guard


def test_single_zero_overlap_statement_is_warning_only():
    answer = "Deriphyllin is labeled for bronchospasm relief. Deriphyllin contains etofylline and theophylline."
    stmts = ["Deriphyllin is labeled for bronchospasm relief.", "Deriphyllin contains etofylline.", "Zorblax quuxes frimble."]
    out = check_contamination(stmts, answer)
    assert not out.contaminated
    assert any(w.startswith("low_overlap_statement") for w in out.warnings)


def test_majority_zero_overlap_is_contaminated():
    answer = "Deriphyllin is labeled for bronchospasm relief."
    stmts = ["Zorblax quuxes frimble.", "Plugh xyzzy wibble.", "Deriphyllin is labeled for bronchospasm relief."]
    out = check_contamination(stmts, answer)
    assert out.contaminated and any("zero_overlap_majority" in r for r in out.reasons)


def test_example_match_exempt_when_answer_genuinely_contains_it():
    ex = "John is a dedicated student."
    out = check_contamination([ex], f"Note that {ex} Also other facts.", example_strings=[ex])
    assert not out.contaminated


def test_low_overlap_warning_keeps_case_valid_end_to_end(tmp_path):
    rec = load_fixture("E2E-035")
    sents = [s.rstrip(".") + "." for s in rec["answer_core"].split(". ") if s.strip()][:3]
    while len(sents) < 3:  # guarantee >= 3 overlapping statements so 1 zero-overlap is a minority (< 50%)
        sents.append(sents[-1])
    sents = sents + ["Zorblax quuxes frimble."]
    # 1 zero-overlap statement out of >=4 -> warning only

    def h(step, text, idx):
        return stmt_json(sents) if step == "statement_generation" else nli_json(sents, [1] * len(sents))

    res, *_ = score(tmp_path, rec, h)
    assert res.status is EvalStatus.valid
    assert any(w.startswith("low_overlap_statement") for w in res.warnings)


def test_classify_step_distinguishes_fix_prompt_that_embeds_other_prompts():
    from ragas.metrics._faithfulness import NLIStatementInput, NLIStatementPrompt
    from ragas.prompt.pydantic_prompt import FixOutputFormat, OutputStringAndPrompt
    nli = NLIStatementPrompt().to_string(NLIStatementInput(context="c", statements=["s"]))
    fix = FixOutputFormat().to_string(OutputStringAndPrompt(output_string="garbage", prompt_value=nli))
    assert classify_step(nli) == "NLI" and classify_step(fix) == "fix_output_format"
