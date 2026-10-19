"""
Unit tests for Step 1: Trace Capture & Generation Hyperparameters.
Tests GenerationParams, metadata reporting, truncation flags, Pipeline.run trace capture,
and strict backwards compatibility.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.llm import (
    GenerationParams,
    call_ollama_api_generate_meta,
    generate_with_mode,
    generate_with_mode_meta,
)
from app.llm_providers import (
    call_gemini_meta,
    call_groq_meta,
    generate_online_meta,
)
from app.core import Pipeline


class TestGenerationParams:
    def test_default_values_none(self):
        params = GenerationParams()
        assert params.temperature is None
        assert params.seed is None
        assert params.num_ctx is None
        assert params.num_predict is None

    def test_frozen_immutability(self):
        params = GenerationParams(temperature=0.0, seed=42)
        with pytest.raises(Exception):
            params.temperature = 0.7  # type: ignore


class TestOllamaMetadataAndTruncationFlags:
    @patch("requests.post")
    def test_options_and_params_merged_correctly(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Clinical answer",
            "done_reason": "stop",
            "prompt_eval_count": 150,
            "eval_count": 50,
        }
        mock_post.return_value = mock_resp

        params = GenerationParams(temperature=0.0, seed=42, num_ctx=4096, num_predict=256)
        text, meta = call_ollama_api_generate_meta(
            "test prompt",
            model="llama3.1:8b",
            params=params
        )

        assert text == "Clinical answer"
        assert meta["provider"] == "ollama"
        assert meta["model"] == "ollama/llama3.1:8b"
        assert meta["finish_reason"] == "stop"
        assert meta["prompt_eval_count"] == 150
        assert meta["eval_count"] == 50
        assert meta["effective_num_ctx"] == 4096
        assert meta["truncated_by_length"] is False
        assert meta["likely_prompt_truncated"] is False

        # Verify payload sent to Ollama
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["options"]["temperature"] == 0.0
        assert payload["options"]["seed"] == 42
        assert payload["options"]["num_ctx"] == 4096
        assert payload["options"]["num_predict"] == 256

    @patch("requests.post")
    def test_truncated_by_length_flag(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Incomplete answer...",
            "done_reason": "length",
            "prompt_eval_count": 200,
            "eval_count": 100,
        }
        mock_post.return_value = mock_resp

        text, meta = call_ollama_api_generate_meta("prompt", model="llama3.1:8b")
        assert meta["truncated_by_length"] is True
        assert meta["likely_prompt_truncated"] is False

    @patch("requests.post")
    def test_likely_prompt_truncated_flag(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Answer",
            "done_reason": "stop",
            "prompt_eval_count": 8192,
            "eval_count": 80,
        }
        mock_post.return_value = mock_resp

        # No params -> effective_num_ctx defaults to 8192
        text, meta = call_ollama_api_generate_meta("prompt", model="llama3.1:8b")
        assert meta["prompt_eval_count"] == 8192
        assert meta["effective_num_ctx"] == 8192
        assert meta["likely_prompt_truncated"] is True


class TestOnlineProvidersMetadata:
    @patch("requests.post")
    def test_groq_meta_and_params(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Groq answer"}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 2048}
        }
        mock_post.return_value = mock_resp

        with patch("app.llm_providers._get_cfg") as mock_cfg:
            cfg = MagicMock()
            cfg.GROQ_API_KEY = "gsk_test"
            cfg.ONLINE_LLM_TIMEOUT_SECONDS = 10.0
            mock_cfg.return_value = cfg

            params = GenerationParams(temperature=0.1, seed=123)
            text, meta = call_groq_meta("prompt", model="openai/gpt-oss-120b", params=params)

            assert text == "Groq answer"
            assert meta["provider"] == "groq"
            assert meta["model"] == "groq/openai/gpt-oss-120b"
            assert meta["truncated_by_length"] is True
            assert meta["prompt_eval_count"] == 500
            assert meta["eval_count"] == 2048

    @patch("requests.post")
    def test_gemini_meta_and_params(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "Gemini response"}]},
                "finishReason": "MAX_TOKENS"
            }],
            "usageMetadata": {"promptTokenCount": 350, "candidatesTokenCount": 2048}
        }
        mock_post.return_value = mock_resp

        with patch("app.llm_providers._get_cfg") as mock_cfg:
            cfg = MagicMock()
            cfg.GEMINI_API_KEY = "gem_test"
            cfg.ONLINE_LLM_TIMEOUT_SECONDS = 10.0
            mock_cfg.return_value = cfg

            text, meta = call_gemini_meta("prompt", model="gemini-3.6-flash")
            assert text == "Gemini response"
            assert meta["provider"] == "gemini"
            assert meta["truncated_by_length"] is True
            assert meta["prompt_eval_count"] == 350


class TestPipelineTraceCapture:
    def _create_mock_pipeline(self):
        pipeline = Pipeline(indexes_config={})
        pipeline.retriever = MagicMock()
        pipeline.retriever.search_specific.return_value = [
            ("key1", 0.95, {"id": 101, "brand_name": "TestDrug"}),
        ]
        return pipeline

    def test_pipeline_run_default_unchanged(self):
        pipeline = self._create_mock_pipeline()
        with patch("app.core.generate_with_mode_meta") as mock_gen:
            mock_gen.return_value = ("Verdict: Appropriate.", {"provider": "ollama", "model": "ollama/llama3.1:8b"})
            res = pipeline.run("Patient headache")

        assert "card" in res
        assert "meta" in res
        assert "pipeline_timings" in res
        assert "trace" not in res

    def test_pipeline_run_with_trace_capture(self):
        pipeline = self._create_mock_pipeline()
        pipeline.retriever.search_specific.side_effect = lambda idx, text, top_k: [
            ("d_1", 0.9, {"id": 1, "chunk": {"id": "chunk_42", "disease": "Asthma"}}),
        ] if idx == "diseases" else [
            ("drug_10", 0.85, {"id": 10, "brand_name": "Albuterol"}),
        ]

        with patch("app.core.generate_with_mode_meta") as mock_gen:
            gen_meta = {
                "provider": "ollama",
                "model": "ollama/llama3.1:8b",
                "latency_ms": 1200,
                "finish_reason": "stop",
                "done_reason": "stop",
                "prompt_eval_count": 650,
                "eval_count": 120,
                "effective_num_ctx": 8192,
                "truncated_by_length": False,
                "likely_prompt_truncated": False,
            }
            mock_gen.return_value = ("### Suggested Alternatives\n* Albuterol", gen_meta)

            params = GenerationParams(temperature=0.0, seed=42)
            res = pipeline.run(
                user_text="Shortness of breath",
                return_trace=True,
                ocr_text_override="Albuterol Inhaler",
                gen_params=params,
            )

        assert "trace" in res
        trace = res["trace"]
        assert "prompt" in trace
        assert trace["prompt_chars"] > 0
        assert trace["prompt_tokens_est"] > 0
        assert "retrievals_per_channel" in trace
        assert "retrieved_ids" in trace
        assert trace["raw_llm_output"] == "### Suggested Alternatives\n* Albuterol"
        assert trace["final_output"] != ""
        assert trace["fast_path_fired"] is False
        assert trace["generation_meta"] == gen_meta
        assert trace["effective_settings"]["params"]["temperature"] == 0.0
        assert trace["effective_settings"]["params"]["seed"] == 42
        assert "disease_chunk_42" in trace["retrieved_ids"].get("diseases", [])
        assert "drug_10" in trace["retrieved_ids"].get("drugs", [])

    def test_pipeline_run_fast_path_trace(self):
        pipeline = self._create_mock_pipeline()
        pipeline.guardrail = MagicMock()
        mock_decision = MagicMock()
        mock_decision.is_emergency = True
        mock_decision.severity = "CRITICAL_EMERGENCY"
        mock_decision.fired_rule_id = "RULE-01-CHEST-PAIN"
        mock_decision.to_dict.return_value = {"rule": "RULE-01-CHEST-PAIN"}
        pipeline.guardrail.detect_emergency.return_value = mock_decision
        pipeline.guardrail.apply_guardrail.return_value = ("### 🚨 Immediate Emergency Medical Guidance", mock_decision)

        res = pipeline.run(
            user_text="Severe crushing chest pain",
            return_trace=True
        )

        assert res["meta"]["fast_path"] is True
        assert "trace" in res
        trace = res["trace"]
        assert trace["fast_path_fired"] is True
        assert trace["raw_llm_output"] == ""
        assert "Immediate Emergency Medical Guidance" in trace["final_output"]
        assert trace["generation_meta"] is None
