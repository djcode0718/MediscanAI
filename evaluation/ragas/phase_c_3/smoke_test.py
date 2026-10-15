#!/usr/bin/env python3
"""
MediScanAI — Phase C.3 Ragas Smoke Test
Executes minimal reproducibility verification for:
1. Dataset adapter serialization and validation error handling.
2. Local embedding model loading (all-MiniLM-L6-v2, offline).
3. Local judge LLM connectivity (llama3.1:8b via Ollama).
4. Ragas metric evaluation on a synthetic non-clinical fixture.
5. Structural adapter check on 2 benchmark reference records (strictly without reporting benchmark scores).
Outputs results to smoke_test_results.json.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.ragas.phase_c_3.dataset_adapter import (
    RagasEvaluationRecord,
    RagasDatasetAdapter,
)

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import faithfulness, answer_relevancy
from ragas.evaluation import evaluate


def run_smoke_test():
    test_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": {
            "python_version": sys.version,
            "conda_env": "med-env",
            "host": "Apple Silicon (macOS arm64)"
        },
        "tests": {}
    }

    print("=" * 80)
    print("MediScanAI Phase C.3 — Ragas Infrastructure Smoke Test")
    print("=" * 80)

    # 1. Test Adapter Error Handling
    print("\n[Test 1] Testing Adapter Validation & Error Handling...")
    try:
        invalid_rec = RagasEvaluationRecord(
            case_id="",
            query="",
            retrieved_contexts=[],
            response=""
        )
        errors = invalid_rec.validate()
        assert len(errors) >= 3, f"Expected >= 3 validation errors, got {len(errors)}"
        print(f"PASS: Adapter correctly rejected invalid record with {len(errors)} errors: {errors}")
        test_results["tests"]["adapter_validation_error_handling"] = {
            "status": "PASS",
            "detected_errors_count": len(errors),
            "errors": errors
        }
    except Exception as e:
        print(f"FAIL: Adapter error handling failed: {e}")
        test_results["tests"]["adapter_validation_error_handling"] = {"status": "FAIL", "error": str(e)}

    # 2. Test Embedding Loading
    print("\n[Test 2] Testing Local Embedding Model (all-MiniLM-L6-v2)...")
    try:
        t0 = time.perf_counter()
        raw_emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        emb_wrapper = LangchainEmbeddingsWrapper(raw_emb)
        vec = raw_emb.embed_query("Synthetic test query")
        t_ms = int((time.perf_counter() - t0) * 1000)
        assert len(vec) == 384, f"Expected 384 dimensions, got {len(vec)}"
        print(f"PASS: all-MiniLM-L6-v2 loaded locally in {t_ms}ms (vector dim: {len(vec)})")
        test_results["tests"]["embedding_model_loading"] = {
            "status": "PASS",
            "model_name": "all-MiniLM-L6-v2",
            "dimension": len(vec),
            "load_and_embed_latency_ms": t_ms
        }
    except Exception as e:
        print(f"FAIL: Embedding loading failed: {e}")
        test_results["tests"]["embedding_model_loading"] = {"status": "FAIL", "error": str(e)}
        return test_results

    # 3. Test Judge LLM Connectivity
    print("\n[Test 3] Testing Judge LLM (llama3.1:8b via Ollama)...")
    try:
        t0 = time.perf_counter()
        raw_chat = ChatOllama(model="llama3.1:8b", temperature=0)
        judge_wrapper = LangchainLLMWrapper(raw_chat)
        probe_res = raw_chat.invoke("Respond with: READY")
        t_ms = int((time.perf_counter() - t0) * 1000)
        print(f"PASS: llama3.1:8b responded in {t_ms}ms: '{probe_res.content.strip()}'")
        test_results["tests"]["judge_llm_connectivity"] = {
            "status": "PASS",
            "model_identifier": "llama3.1:8b",
            "latency_ms": t_ms,
            "response": probe_res.content.strip()
        }
    except Exception as e:
        print(f"FAIL: Judge LLM connectivity failed: {e}")
        test_results["tests"]["judge_llm_connectivity"] = {"status": "FAIL", "error": str(e)}
        return test_results

    # 4. Test Ragas Metric Execution on Synthetic Fixture
    print("\n[Test 4] Testing Ragas Metric Invocation on Synthetic Non-Clinical Fixture...")
    try:
        synthetic_record = RagasEvaluationRecord(
            case_id="SYNTHETIC-FIXTURE-001",
            query="Where is the Eiffel Tower located?",
            retrieved_contexts=["The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France."],
            response="The Eiffel Tower is located on the Champ de Mars in Paris, France.",
            reference="The Eiffel Tower is located in Paris, France.",
            track="synthetic_test",
            metadata={"source": "non_clinical_synthetic_fixture"}
        )

        hf_ds = RagasDatasetAdapter.create_hf_dataset([synthetic_record])
        print(f"HuggingFace dataset created with {len(hf_ds)} synthetic sample.")

        t0 = time.perf_counter()
        eval_res = evaluate(
            dataset=hf_ds,
            metrics=[faithfulness, answer_relevancy],
            llm=judge_wrapper,
            embeddings=emb_wrapper,
            show_progress=False
        )
        t_ms = int((time.perf_counter() - t0) * 1000)

        scores = eval_res.scores[0]
        print(f"PASS: Evaluated synthetic fixture in {t_ms}ms:")
        print(f"      faithfulness: {scores.get('faithfulness')}")
        print(f"      answer_relevancy: {scores.get('answer_relevancy')}")

        test_results["tests"]["ragas_metric_invocation"] = {
            "status": "PASS",
            "evaluation_latency_ms": t_ms,
            "fixture_id": "SYNTHETIC-FIXTURE-001",
            "faithfulness": float(scores.get("faithfulness", 0.0)),
            "answer_relevancy": float(scores.get("answer_relevancy", 0.0))
        }
    except Exception as e:
        print(f"FAIL: Ragas metric evaluation failed: {e}")
        test_results["tests"]["ragas_metric_invocation"] = {"status": "FAIL", "error": str(e)}

    # 5. Structural Check on 2 Benchmark Cases (Compatibility Only)
    print("\n[Test 5] Testing Structural Adapter Compatibility on 2 Benchmark Cases...")
    try:
        ref_path = PROJECT_ROOT / "evaluation/benchmark/narrative_references/reference_answers.jsonl"
        with open(ref_path) as f:
            ref_data = [json.loads(f.readline()), json.loads(f.readline())]

        bench_records = []
        for r in ref_data:
            rec = RagasEvaluationRecord(
                case_id=r["case_id"],
                query=r["query"],
                retrieved_contexts=[f"Sample retrieved context for {r['query']}"],
                response=f"Sample mock response for {r['query']}",
                reference=r["reference_answer"],
                track="baseline",
                reference_provenance=r.get("verification_provenance")
            )
            bench_records.append(rec)

        bench_ds = RagasDatasetAdapter.create_hf_dataset(bench_records)
        print(f"PASS: Successfully built compliant Ragas dataset for {len(bench_ds)} benchmark reference records.")
        test_results["tests"]["benchmark_adapter_structural_compatibility"] = {
            "status": "PASS",
            "cases_tested": [r.case_id for r in bench_records],
            "benchmark_scores_computed": False,
            "note": "Structural verification only; zero benchmark answers generated or scored."
        }
    except Exception as e:
        print(f"FAIL: Benchmark structural check failed: {e}")
        test_results["tests"]["benchmark_adapter_structural_compatibility"] = {"status": "FAIL", "error": str(e)}

    # Summary
    all_passed = all(t.get("status") == "PASS" for t in test_results["tests"].values())
    test_results["overall_smoke_test_status"] = "PASSED" if all_passed else "FAILED"

    out_file = Path(__file__).resolve().parent / "smoke_test_results.json"
    with open(out_file, "w") as f:
        json.dump(test_results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Smoke Test Overall Status: {test_results['overall_smoke_test_status']}")
    print(f"Results written to: {out_file}")
    print("=" * 80)
    return test_results


if __name__ == "__main__":
    run_smoke_test()
