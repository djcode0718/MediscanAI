"""
MediScanAI — Phase D.2.c: OCR Recovery Experiments

Evaluates 5 controlled alternatives for recovering partially cropped
and noisy OCR text without lowering global thresholds or compromising safety:
1. ALT-1-FIXED-THRESHOLD: Rigid global threshold tau = -0.5 across all queries.
2. ALT-2-OCR-ADAPTIVE-THRESHOLD: Confidence-scaled OCR threshold tau_ocr = -3.0.
3. ALT-3-CATALOG-PREFIX-VERIFICATION: Catalog-constrained prefix matching for truncated packaging text.
4. ALT-4-LEXICAL-BM25-GATE: Lexical BM25 match gate with cross-encoder rank ordering.
5. ALT-5-CLARIFICATION-POLICY: Clarification prompt when identity cannot be established.

Outputs:
- evaluation/retrieval/phase_d_2_c/ocr_recovery_experiments.csv
"""

import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

ROOT_DIR = Path("/Users/sj/Documents/mediscanai")
sys.path.insert(0, str(ROOT_DIR))

from evaluation.retrieval.phase_d_2_a.intent_router import IntentRouter
from evaluation.retrieval.phase_d_1.experimental_retriever import (
    ExperimentalHybridRetriever,
    extract_structured_rerank_text,
)

D2C_DIR = ROOT_DIR / "evaluation/retrieval/phase_d_2_c"


def evaluate_ocr_policy(
    retriever: ExperimentalHybridRetriever,
    router: IntentRouter,
    scenarios: List[Dict[str, Any]],
    policy_name: str,
) -> List[Dict[str, Any]]:
    """Evaluates an OCR recovery policy across all test scenarios."""
    results = []

    for sc in scenarios:
        ocr_text = sc["ocr_text"]
        conf = sc["confidence"]
        expected_act = sc["expected_action"]

        t0 = time.perf_counter()
        dec = router.route(ocr_text, is_ocr=True, ocr_confidence=conf)

        if dec.routing_action in ["CLARIFICATION_REQUIRED", "CLEAN_ABSTAIN", "TRIAGE_ESCALATE"]:
            lat = int((time.perf_counter() - t0) * 1000)
            passed = (dec.routing_action == expected_act)
            results.append({
                "policy": policy_name,
                "test_id": sc["test_id"],
                "ocr_text": ocr_text,
                "confidence": conf,
                "routing_action": dec.routing_action,
                "retrieved_count": 0,
                "top_candidate": "None (Abstain/Clarify)",
                "passed": passed,
                "latency_ms": lat,
                "explanation": dec.reasoning,
            })
            continue

        # Execute retrieval on drugs index
        pool_size = 30
        from evaluation.retrieval.phase_d_1.medical_tokenizer import normalize_text_medical
        from app.embeddings import embed_texts
        from app.retriever import rrf_fuse

        # If policy 3 (Catalog Prefix Verification), check for prefix expansion
        search_query = ocr_text
        prefix_expanded = False
        if policy_name == "ALT-3-CATALOG-PREFIX-VERIFICATION":
            tokens = [t.strip(".,;:?!").lower() for t in ocr_text.split() if len(t) >= 5]
            for t in tokens:
                matching_subs = [s for s in router.drug_names if s.startswith(t)]
                if len(matching_subs) == 1:
                    search_query = f"{matching_subs[0]} {ocr_text}"
                    prefix_expanded = True
                    break

        norm_text = normalize_text_medical(search_query)
        emb = embed_texts([norm_text])[0].astype("float32")

        wrapper = retriever.idx_wrappers["drugs"]
        bm25_idx = retriever.bm25_indexes["drugs"]

        dense_raw = wrapper.search(emb, top_k=pool_size)
        bm25_raw = bm25_idx.search(search_query, top_k=pool_size)
        idx_keys = list(wrapper.id_to_obj.keys())
        bm25_tuples = [(idx_keys[d_idx], sc, wrapper.id_to_obj[idx_keys[d_idx]]) for d_idx, sc in bm25_raw]

        fused = rrf_fuse(dense_raw, bm25_tuples, k=60)[:pool_size]

        # Rerank with Cross-Encoder
        pairs = []
        for key, base_score, obj in fused:
            doc_text = extract_structured_rerank_text("drugs", obj)
            pairs.append((ocr_text, doc_text))

        with retriever.reranker._lock:
            scores = retriever.reranker.model.predict(pairs)

        ranked = [(key, float(scores[i]), obj) for i, (key, sc, obj) in enumerate(fused)]
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Apply Policy Filter
        if policy_name == "ALT-1-FIXED-THRESHOLD":
            # Global tau = -0.5
            filtered = [r for r in ranked if r[1] >= -0.5]
        elif policy_name == "ALT-2-OCR-ADAPTIVE-THRESHOLD":
            # Confidence scaled threshold: tau_ocr = -3.0 when conf >= 0.70
            tau_ocr = -3.0 if conf >= 0.70 else -0.5
            filtered = [r for r in ranked if r[1] >= tau_ocr]
        elif policy_name == "ALT-3-CATALOG-PREFIX-VERIFICATION":
            # If prefix expanded or score >= -0.5
            tau = -3.0 if prefix_expanded else -0.5
            filtered = [r for r in ranked if r[1] >= tau]
        elif policy_name == "ALT-4-LEXICAL-BM25-GATE":
            # Retain if BM25 score > 0 or score >= -0.5
            bm25_matching_keys = {t[0] for t in bm25_tuples if t[1] > 0}
            filtered = [r for r in ranked if (r[1] >= -0.5 or r[0] in bm25_matching_keys)]
        elif policy_name == "ALT-5-CLARIFICATION-POLICY":
            # If highest score < -0.5 and no prefix match -> prompt clarification
            if ranked and ranked[0][1] < -0.5:
                filtered = []
            else:
                filtered = [r for r in ranked if r[1] >= -0.5]
        else:
            filtered = ranked

        lat = int((time.perf_counter() - t0) * 1000)
        passed = (len(filtered) > 0) if expected_act == "RETRIEVE_DRUG_CATALOG" else (len(filtered) == 0)

        top_cand = f"drug_{filtered[0][2].get('id')} ({filtered[0][2].get('brand_name')})" if filtered else "None"

        results.append({
            "policy": policy_name,
            "test_id": sc["test_id"],
            "ocr_text": ocr_text,
            "confidence": conf,
            "routing_action": dec.routing_action,
            "retrieved_count": len(filtered),
            "top_candidate": top_cand,
            "passed": passed,
            "latency_ms": lat,
            "explanation": f"PrefixExpanded: {prefix_expanded}, TopScore: {ranked[0][1]:.3f}" if ranked else "NoCandidates",
        })

    return results


def main():
    print("=== STARTING OCR RECOVERY EXPERIMENTS ===")
    router = IntentRouter()
    retriever = ExperimentalHybridRetriever(candidate_pool_size=30)

    ocr_scenarios = [
        {"test_id": "OCR-01-CLEAR-BRAND", "ocr_text": "Lipitor 20mg Pfizer atorvastatin calcium", "confidence": 0.95, "expected_action": "RETRIEVE_DRUG_CATALOG"},
        {"test_id": "OCR-02-GENERIC-ONLY", "ocr_text": "Amoxicillin 500mg USP capsules", "confidence": 0.92, "expected_action": "RETRIEVE_DRUG_CATALOG"},
        {"test_id": "OCR-03-PARTIALLY-CROPPED", "ocr_text": "Cinnariz 25mg tab", "confidence": 0.81, "expected_action": "RETRIEVE_DRUG_CATALOG"},
        {"test_id": "OCR-04-SPELLING-ERRORS", "ocr_text": "Liptor 10mg atorvastatn", "confidence": 0.76, "expected_action": "RETRIEVE_DRUG_CATALOG"},
        {"test_id": "OCR-05-MULTIPLE-FORMULATIONS", "ocr_text": "Metformin HCl 500mg ER extended release", "confidence": 0.89, "expected_action": "RETRIEVE_DRUG_CATALOG"},
        {"test_id": "OCR-06-MULTIPLE-MEDICINES", "ocr_text": "Augmentin amoxicillin clavulanate potassium 875 125mg", "confidence": 0.88, "expected_action": "RETRIEVE_DRUG_CATALOG"},
        {"test_id": "OCR-07-UNREADABLE-LABEL", "ocr_text": "Unreadable blurry packaging noise ###???", "confidence": 0.18, "expected_action": "CLARIFICATION_REQUIRED"},
    ]

    policies = [
        "ALT-1-FIXED-THRESHOLD",
        "ALT-2-OCR-ADAPTIVE-THRESHOLD",
        "ALT-3-CATALOG-PREFIX-VERIFICATION",
        "ALT-4-LEXICAL-BM25-GATE",
        "ALT-5-CLARIFICATION-POLICY",
    ]

    all_rows = []
    for pol in policies:
        print(f"\nEvaluating Policy: {pol}...")
        rows = evaluate_ocr_policy(retriever, router, ocr_scenarios, pol)
        all_rows.extend(rows)
        passed = sum(1 for r in rows if r["passed"])
        print(f"  Result: {passed}/{len(ocr_scenarios)} PASSED ({passed/len(ocr_scenarios)*100:.1f}%)")

    # Save to ocr_recovery_experiments.csv
    csv_path = D2C_DIR / "ocr_recovery_experiments.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "policy", "test_id", "ocr_text", "confidence", "routing_action",
            "retrieved_count", "top_candidate", "passed", "latency_ms", "explanation"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)
    print(f"\nSaved {csv_path}")


if __name__ == "__main__":
    main()
