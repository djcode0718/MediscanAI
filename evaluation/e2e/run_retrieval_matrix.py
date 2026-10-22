#!/usr/bin/env python3
"""
Experiment 01: deterministic retrieval-depth / top-k / retrieval-mode matrix (NO LLM calls).

Replays the production retrieval (dense FAISS + BM25 -> RRF -> cross-encoder rerank) for the 40
frozen dev cases under many (candidate_pool P, rerank_depth R, top_k) settings. Dense/BM25 lists
and cross-encoder scores are computed once per query and re-sliced, which is exact because
  * dense / BM25 top-P lists are prefixes of the top-Pmax lists (verified by parity check below),
  * the cross-encoder score of a (query, doc) pair is independent of the other candidates.
A parity check compares the replay against the real MultiRetriever.search_specific.

Reference labels are used ONLY to score retrieval; nothing is fed to a generator.
Outputs: evaluation/e2e/results/ragas_opt/exp01_retrieval_matrix/
"""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
import json
import time
import hashlib
import itertools
import subprocess
import statistics as st
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from app.core import DEFAULT_INDEXES, normalize_text, extract_retrieved_ids_per_channel
from app.retriever import MultiRetriever, rrf_fuse, extract_text_for_bm25
from app.embeddings import embed_texts
from app.evidence import CompactEvidenceFormatter

OUT = REPO / "evaluation/e2e/results/ragas_opt/exp01_retrieval_matrix"
DEV = REPO / "evaluation/e2e/dataset/dev_subset_40.json"
DATA = REPO / "evaluation/e2e/dataset/e2e_v1.jsonl"
PMAX = 100
GRID_P = [15, 30, 60]
GRID_R = [5, 10, 15, 30, 60]
GRID_K = [2, 3, 5, 8]
BASE = {"P": 15, "R": 15, "top_k": 5, "cap": 3, "mode": "rrf+rerank"}


def load_cases():
    ids = json.load(open(DEV))["case_ids"]
    allc = {}
    for line in open(DATA):
        if line.strip():
            c = json.loads(line)
            allc[c["case_id"]] = c
    return [allc[i] for i in ids]


def canon_id(channel, key, obj):
    """Canonical id in the dataset's id space (same logic as core.extract_retrieved_ids_per_channel)."""
    return extract_retrieved_ids_per_channel({channel: [(key, 0.0, obj)]})[channel][0]


def queries_for(case):
    """Mirror Pipeline.run: (label, index, text)."""
    q = []
    user_norm = normalize_text(case["user_text"] or "")
    q.append(("diseases", "diseases", user_norm))
    q.append(("drugs", "drugs", user_norm))
    if case.get("ocr_text"):
        q.append(("drug_dict", "drug_dict", case["ocr_text"]))
        q.append(("drugs_from_ocr", "drugs", case["ocr_text"]))
    return q


class Replay:
    def __init__(self, ret):
        self.ret = ret
        self.cache = {}   # (label,text) -> dict
        self.ce = {}      # (index, text, key) -> score

    def prep(self, label, index, text):
        ck = (label, text)
        if ck in self.cache:
            return self.cache[ck]
        w = self.ret.idx_wrappers[index]
        emb = embed_texts([normalize_text(text)])[0].astype("float32")
        dense = w.search(emb, top_k=PMAX)
        keys = list(w.id_to_obj.keys())
        bm = []
        for di, s in self.ret.bm25_indexes[index].search(text, top_k=PMAX):
            k = keys[di]
            bm.append((k, s, w.id_to_obj[k]))
        d = {"index": index, "text": text, "dense": dense, "bm25": bm}
        self.cache[ck] = d
        return d

    def fused(self, d, P):
        return rrf_fuse(d["dense"][:P], d["bm25"][:P])

    def rerank(self, d, P, R, k):
        pool = self.fused(d, P)[:R]
        need = [(key, obj) for key, _, obj in pool if (d["index"], d["text"], key) not in self.ce]
        if need:
            self.ret.reranker.load_model()
            pairs = [(d["text"], extract_text_for_bm25(d["index"], obj)) for _, obj in need]
            scores = self.ret.reranker.model.predict(pairs)
            for (key, _), s in zip(need, scores):
                self.ce[(d["index"], d["text"], key)] = float(s)
        res = [(key, self.ce[(d["index"], d["text"], key)], obj) for key, _, obj in pool]
        res.sort(key=lambda x: x[1], reverse=True)
        return res[:k]

    def retrieve(self, d, mode, P, R, k):
        if mode == "dense":
            return [(a, b, c) for a, b, c in d["dense"][:k]]
        if mode == "bm25":
            return d["bm25"][:k]
        if mode == "rrf":
            return self.fused(d, P)[:k]
        return self.rerank(d, P, R, k)


def dedup_key(obj):
    g = (obj.get("generic_name") or "").upper().strip()
    subs = tuple(sorted(str(s).strip().upper() for s in (obj.get("substance_name") or [])))
    return (g, subs)


def evaluate_config(rep, cases, cfg, fmt_cache):
    P, R, top_k, cap, mode = cfg["P"], cfg["R"], cfg["top_k"], cfg["cap"], cfg["mode"]
    formatter = CompactEvidenceFormatter(max_items_per_channel=cap)
    rows = []
    for case in cases:
        retrievals = {}
        for label, index, text in queries_for(case):
            d = rep.prep(label, index, text)
            retrievals[label] = rep.retrieve(d, mode, P, R, top_k)
        ids = extract_retrieved_ids_per_channel(retrievals)

        refs = [str(r) for r in case.get("reference_context_ids", [])]
        eq = {str(e) for e in case.get("equivalent_ids", [])}
        ref_drugs = [r for r in refs if r.startswith("drug_")]
        ref_dis = [r for r in refs if r.startswith("disease_chunk_")]
        ok_drugs = set(ref_drugs) | eq

        # --- retrieved-level metrics (top_k, before dedup/cap)
        row = {"case_id": case["case_id"], "category": case["category"], **cfg}
        if ref_drugs:
            pooled = []
            for ch in ("drugs", "drugs_from_ocr"):
                pooled += ids.get(ch, [])
            row["drug_hit_retrieved"] = int(any(i in ok_drugs for i in pooled))
            row["drug_hit_retrieved_strict"] = int(any(i in set(ref_drugs) for i in pooled))
            lst = ids.get("drugs_from_ocr", [])
            rr = 0.0
            for rank, i in enumerate(lst, 1):
                if i in ok_drugs:
                    rr = 1.0 / rank
                    break
            row["drug_rr_ocr_channel"] = rr
        if ref_dis:
            lst = ids.get("diseases", [])
            row["disease_hit_retrieved"] = int(any(i in set(ref_dis) for i in lst))
            rr = 0.0
            for rank, i in enumerate(lst, 1):
                if i in set(ref_dis):
                    rr = 1.0 / rank
                    break
            row["disease_rr"] = rr

        # --- shown-level metrics via the production compact formatter
        text, tr = formatter.format(retrievals, token_budget=None)
        shown_ids = set()
        n_items = len(tr["evidence_items"])
        n_dis = sum(1 for it in tr["evidence_items"] if it["item_type"] == "DISEASE")
        for it in tr["evidence_items"]:
            if it["item_type"] == "DRUG":
                for c in it["covers_ids"]:
                    shown_ids.add(f"drug_{c}")
        # formatter takes the first `cap` disease results in order -> canonical ids via retrieval ids
        shown_ids.update(ids.get("diseases", [])[:cap])
        shown_ids.update(ids.get("drug_dict", [])[:cap])
        if ref_drugs:
            row["drug_hit_shown"] = int(any(i in ok_drugs for i in shown_ids))
        if ref_dis:
            row["disease_hit_shown"] = int(any(i in set(ref_dis) for i in shown_ids))
        if refs:
            row["id_recall_shown"] = sum(1 for r in refs if r in shown_ids or (r in ref_drugs and r in ok_drugs and any(e in shown_ids for e in ok_drugs))) / len(refs)
        # ID-based precision over shown DRUG items (items whose covers_ids intersect ok_drugs)
        drug_items = [it for it in tr["evidence_items"] if it["item_type"] == "DRUG"]
        if ref_drugs and drug_items:
            good = sum(1 for it in drug_items if any(f"drug_{c}" in ok_drugs for c in it["covers_ids"]))
            row["drug_item_precision_shown"] = good / len(drug_items)
        row["evidence_tokens"] = tr["total_evidence_tokens"]
        row["evidence_items"] = n_items
        row["disease_block_share"] = (n_dis / n_items) if n_items else 0.0

        # duplicate rate within retrieved drug lists (same generic+substances)
        dup_num = dup_den = 0
        for ch in ("drugs", "drugs_from_ocr"):
            seen = set()
            for _, _, obj in retrievals.get(ch, []):
                if isinstance(obj, dict):
                    k = dedup_key(obj)
                    dup_den += 1
                    if k in seen:
                        dup_num += 1
                    seen.add(k)
        row["duplicate_rate"] = (dup_num / dup_den) if dup_den else 0.0
        rows.append(row)
    return rows


def mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def p95(vals):
    return round(float(np.percentile(vals, 95)), 1) if vals else None


def aggregate(rows):
    g = lambda key: [r[key] for r in rows if key in r]
    return {
        "n_cases": len(rows),
        "n_drug_ref_cases": len(g("drug_hit_shown")),
        "n_disease_ref_cases": len(g("disease_hit_shown")),
        "drug_hit_retrieved": mean(g("drug_hit_retrieved")),
        "drug_hit_retrieved_strict": mean(g("drug_hit_retrieved_strict")),
        "drug_hit_shown": mean(g("drug_hit_shown")),
        "drug_mrr_ocr_channel": mean(g("drug_rr_ocr_channel")),
        "disease_hit_retrieved": mean(g("disease_hit_retrieved")),
        "disease_hit_shown": mean(g("disease_hit_shown")),
        "disease_mrr": mean(g("disease_rr")),
        "id_recall_shown": mean(g("id_recall_shown")),
        "drug_item_precision_shown": mean(g("drug_item_precision_shown")),
        "evidence_tokens_mean": mean(g("evidence_tokens")),
        "evidence_tokens_p95": p95(g("evidence_tokens")),
        "duplicate_rate": mean(g("duplicate_rate")),
        "disease_block_share": mean(g("disease_block_share")),
    }


def cfg_name(c):
    return f"{c['mode']}|P{c['P']}|R{c['R']}|k{c['top_k']}|cap{c['cap']}"


def parity_check(rep, cases):
    """Replay == real search_specific for the baseline and a deeper setting."""
    bad = []
    n = 0
    for case in cases:
        for label, index, text in queries_for(case):
            for (P, R, k) in [(15, 15, 5), (60, 30, 5)]:
                dbg = {}
                real = rep.ret.search_specific(index, text, top_k=k, candidate_pool_size=P, rerank_depth=R, debug=dbg)
                d = rep.prep(label, index, text)
                mine = rep.rerank(d, P, R, k)
                n += 1
                if [str(a) for a, _, _ in real] != [str(a) for a, _, _ in mine]:
                    bad.append((case["case_id"], label, P, R, k))
    return n, bad


def time_subset(rep, cases):
    sub = cases[::4][:10]
    combos = [(15, 15), (30, 15), (30, 30), (60, 15), (60, 30), (60, 60)]
    out = {}
    for P, R in combos:
        per_case = []
        for case in sub:
            t0 = time.perf_counter()
            for label, index, text in queries_for(case):
                rep.ret.search_specific(index, text, top_k=5, candidate_pool_size=P, rerank_depth=R)
            per_case.append((time.perf_counter() - t0) * 1000)
        out[f"P{P}_R{R}"] = {"n_cases": len(sub), "mean_ms": round(st.mean(per_case), 1),
                             "p95_ms": p95(per_case), "median_ms": round(st.median(per_case), 1)}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    ret = MultiRetriever(DEFAULT_INDEXES)
    rep = Replay(ret)
    print(f"index types: " + ", ".join(f"{k}={type(w.index).__name__}" for k, w in ret.idx_wrappers.items()))

    # 0. warm + parity
    t0 = time.time()
    n, bad = parity_check(rep, cases)
    print(f"parity: {n} comparisons, {len(bad)} mismatches ({time.time()-t0:.0f}s)")
    if bad:
        print("PARITY FAILURE examples:", bad[:5])

    configs = []
    # Full grid (rrf+rerank), cap=top_k
    for P, R, k in itertools.product(GRID_P, GRID_R, GRID_K):
        if k <= R <= P:
            configs.append({"P": P, "R": R, "top_k": k, "cap": k, "mode": "rrf+rerank"})
    # Production baseline (top_k=5, cap=3)
    configs.append(dict(BASE))
    # Retrieval-mode ablation at baseline depth
    for mode in ("dense", "bm25", "rrf"):
        configs.append({**BASE, "mode": mode})

    all_rows = []
    summary = {}
    for i, cfg in enumerate(configs, 1):
        rows = evaluate_config(rep, cases, cfg, {})
        all_rows += rows
        summary[cfg_name(cfg)] = {"config": cfg, "overall": aggregate(rows),
                                  "by_category": {c: aggregate([r for r in rows if r["category"] == c])
                                                  for c in sorted({r["category"] for r in rows})}}
        if i % 10 == 0:
            print(f"  evaluated {i}/{len(configs)} configs")

    timing = time_subset(rep, cases)

    with open(OUT / "per_case.jsonl", "w") as f:
        for r in all_rows:
            f.write(json.dumps(r) + "\n")
    json.dump(summary, open(OUT / "summary.json", "w"), indent=2)
    json.dump({
        "git_commit": git,
        "branch": subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
        "dev_subset": str(DEV.relative_to(REPO)),
        "dev_subset_sha256": hashlib.sha256(DEV.read_bytes()).hexdigest()[:16],
        "dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest()[:16],
        "grid": {"P": GRID_P, "R": GRID_R, "top_k": GRID_K},
        "baseline": BASE,
        "embedding_model": "app.embeddings.embed_texts",
        "reranker": ret.reranker.model_name,
        "parity": {"comparisons": n, "mismatches": len(bad)},
        "latency_subset_ms": timing,
        "n_configs": len(configs),
        "llm_calls": 0,
    }, open(OUT / "config.json", "w"), indent=2)
    print("latency subset:", json.dumps(timing, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
