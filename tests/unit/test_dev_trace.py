import inspect
import json

from app.dev_trace import (
    INSTRUCTION_RESERVE_TOKENS,
    SAFETY_MARGIN_TOKENS,
    build_dev_trace,
    derive_omission_reasons,
    write_dev_trace,
)


def _items():
    return [
        {"id": "70114", "covers_ids": ["70114", "33421"], "tag": "[E1]", "channel": "drugs",
         "item_type": "DRUG", "tokens": 100},
        {"id": "disease_chunk_1", "covers_ids": ["disease_chunk_1"], "tag": "[E2]", "channel": "diseases",
         "item_type": "DISEASE", "tokens": 80},
    ]


def test_omission_reasons_cover_dup_cap_and_budget():
    retrieved = {
        "drugs": ["drug_70114", "drug_33421", "drug_555", "drug_777"],
        "diseases": ["disease_chunk_1", "disease_chunk_9"],
    }
    trims = [{"action": "drop_item", "dropped_id": "777", "channel": "drugs"}]
    reasons = derive_omission_reasons(retrieved, _items(), trims, max_items_per_channel=3)
    assert "drug_70114" not in reasons
    assert reasons["drug_33421"].startswith("merged_duplicate_into:")
    assert reasons["drug_777"] == "token_budget_drop"
    assert reasons["drug_555"].startswith("per_channel_cap")
    assert reasons["disease_chunk_9"].startswith("per_channel_cap")
    assert "disease_chunk_1" not in reasons


def _trace(include_text=False):
    return build_dev_trace(
        user_text="my secret symptom text",
        ocr_text="Brandname 10mg",
        system_prompt="SYS",
        full_prompt="USER_TEXT: my secret symptom text",
        evidence_trace={"evidence_items": _items(), "total_evidence_tokens": 180, "trims": []},
        retrieval_debug={"drugs": {"dense": [("1", 0.1)], "reranked": [("1", 2.0)]}},
        retrieved_ids={"drugs": ["drug_70114"], "diseases": ["disease_chunk_1"]},
        effective={"num_ctx": 8192, "num_predict": 700},
        token_budget=6736,
        max_items_per_channel=3,
        case_type="SYMPTOM_ONLY",
        generation_meta={"prompt_eval_count": 1459, "eval_count": 118},
        include_text=include_text,
    )


def test_trace_redacts_text_by_default():
    t = _trace()
    blob = json.dumps(t)
    assert "secret symptom" not in blob
    assert "Brandname" not in blob
    assert t["inputs"]["user_text"]["chars"] == len("my secret symptom text")
    assert "prompt_text" not in t


def test_trace_includes_text_only_when_requested():
    t = _trace(include_text=True)
    assert "secret symptom" in t["prompt_text"]["user_message"]


def test_trace_token_budget_fields():
    b = _trace()["token_budget"]
    assert b["evidence_tokens_by_channel"] == {"drugs": 100, "diseases": 80}
    assert b["ollama_prompt_eval_count"] == 1459
    assert b["input_headroom_actual"] == 8192 - 700 - 1459
    assert b["evidence_budget_binding"] is False


def test_budget_constants_match_pipeline_formula():
    import app.core as core
    src = inspect.getsource(core.Pipeline.run)
    assert f"- {SAFETY_MARGIN_TOKENS} - {INSTRUCTION_RESERVE_TOKENS}" in src


def test_write_dev_trace_sanitizes_name(tmp_path):
    p = write_dev_trace({"a": 1}, str(tmp_path), "../evil/name")
    assert p.parent == tmp_path
    assert json.loads(p.read_text())["a"] == 1


def test_defaults_are_off_and_retriever_defaults_preserved():
    from backend.core.config import Settings
    assert Settings.model_fields["DEV_TRACE_ENABLED"].default is False
    assert Settings.model_fields["DEV_TRACE_INCLUDE_TEXT"].default is False
    from app.retriever import MultiRetriever
    sig = inspect.signature(MultiRetriever.search_specific)
    for name in ("candidate_pool_size", "rerank_depth", "debug"):
        assert sig.parameters[name].default is None
