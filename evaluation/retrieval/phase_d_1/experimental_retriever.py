"""
MediScanAI — Phase D.1: Experimental Hybrid Retriever

Implements:
- Experiment D1-1: Non-destructive medical tokenization (zero SymSpell corruption).
- Experiment D1-2: Multi-channel text retrieval with drug_dict integration.
- Experiment D1-3: Section-aware passage reranking and calibrated relevance thresholding.
- Baseline Preservation: Full backward compatibility to run in pure baseline mode.
"""

import os
import time
import math
from typing import Dict, List, Tuple, Any, Optional

import numpy as np

from app.retriever import (
    INDEX_FILES,
    JSONL_FILES,
    FaissIndexWrapper,
    CrossEncoderReranker,
    rrf_fuse,
)
from app.embeddings import embed_texts
from evaluation.retrieval.phase_d_1.medical_tokenizer import (
    MedicalTokenizer,
    normalize_text_medical,
)


def extract_text_for_bm25_expanded(index_name: str, record: dict) -> str:
    """
    Enhanced text extractor incorporating indications, warnings, dosage, and adverse reactions.
    Preserves all clinical fields within searchable text representation.
    """
    if index_name == "diseases":
        chunk = record.get("chunk", {})
        disease = chunk.get("disease", "")
        symptoms = " ".join(chunk.get("symptoms", []))
        return f"{disease} {symptoms}".strip()
    elif index_name == "drugs":
        brand = record.get("brand_name", "") or ""
        generic = record.get("generic_name", "") or ""
        substances = " ".join(record.get("substance_name", [])) if isinstance(record.get("substance_name"), list) else str(record.get("substance_name") or "")
        usage = record.get("indications_and_usage", "") or ""
        warnings = record.get("warnings_and_cautions", "") or ""
        dosage = record.get("dosage_and_administration", "") or ""
        adverse = record.get("adverse_reactions", "") or ""
        return f"{brand} {generic} {substances} {usage} {warnings} {dosage} {adverse}".strip()
    elif index_name == "drug_dict":
        return str(record.get("drug_name", "") or "").strip()
    return str(record)


def extract_structured_rerank_text(index_name: str, record: dict) -> str:
    """
    Constructs section-labeled text for Cross-Encoder reranking.
    Enables the reranker to distinguish indications from warnings and dosage.
    """
    if index_name == "diseases":
        chunk = record.get("chunk", {})
        disease = chunk.get("disease", "")
        symptoms = ", ".join(chunk.get("symptoms", []))
        return f"Disease Condition: {disease}\nKey Symptoms: {symptoms}"
    elif index_name == "drugs":
        parts = []
        brand = record.get("brand_name")
        if brand:
            parts.append(f"Brand Name: {brand}")
        generic = record.get("generic_name")
        if generic:
            parts.append(f"Generic Name: {generic}")
        substances = record.get("substance_name")
        if substances:
            sub_str = ", ".join(substances) if isinstance(substances, list) else str(substances)
            parts.append(f"Active Substance: {sub_str}")
        usage = record.get("indications_and_usage")
        if usage and usage != "unknown":
            parts.append(f"Indications and Usage: {usage}")
        warnings = record.get("warnings_and_cautions")
        if warnings and warnings != "unknown":
            parts.append(f"Warnings and Cautions: {warnings}")
        dosage = record.get("dosage_and_administration")
        if dosage and dosage != "unknown":
            parts.append(f"Dosage and Administration: {dosage}")
        adverse = record.get("adverse_reactions")
        if adverse and adverse != "unknown":
            parts.append(f"Adverse Reactions: {adverse}")
        return "\n".join(parts) if parts else str(record)
    elif index_name == "drug_dict":
        return f"Drug Name: {record.get('drug_name', '')}"
    return str(record)


class MedicalBM25Index:
    """
    BM25 implementation using non-destructive medical tokenization.
    Eliminates SymSpell English dictionary mangling.
    """

    def __init__(self, corpus: List[Dict[str, Any]], text_extractor, k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.N = len(corpus)

        self.doc_lengths = []
        self.doc_term_freqs = []
        self.df = {}

        for doc in corpus:
            text = text_extractor(doc) or ""
            tokens = MedicalTokenizer.tokenize(text)
            self.doc_lengths.append(len(tokens))

            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)

            for t in tf.keys():
                self.df[t] = self.df.get(t, 0) + 1

        self.avgdl = sum(self.doc_lengths) / self.N if self.N > 0 else 1.0

        self.idf = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(1.0 + (self.N - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 15) -> List[Tuple[int, float]]:
        query_tokens = MedicalTokenizer.tokenize(query)
        if not query_tokens:
            return []

        scores = []
        for idx in range(self.N):
            score = 0.0
            tf_dict = self.doc_term_freqs[idx]
            doc_len = self.doc_lengths[idx]

            for token in query_tokens:
                if token not in tf_dict:
                    continue
                tf = tf_dict[token]
                idf = self.idf.get(token, 0.0)

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avgdl))
                score += idf * (numerator / denominator)

            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class ExperimentalHybridRetriever:
    """
    Configurable hybrid retriever supporting baseline reproduction and Phase D.1 experiments:
    - enable_medical_tokenizer (Exp D1-1)
    - enable_drug_dict_text_channel (Exp D1-2)
    - enable_structured_reranking & relevance_threshold (Exp D1-3)
    """

    def __init__(
        self,
        enable_medical_tokenizer: bool = True,
        enable_drug_dict_text_channel: bool = True,
        enable_structured_reranking: bool = True,
        enable_expanded_bm25_fields: bool = True,
        relevance_threshold: Optional[float] = None,  # Calibrated threshold (e.g. -0.5 or 0.0)
        candidate_pool_size: int = 15,
        indexes_config: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        self.enable_medical_tokenizer = enable_medical_tokenizer
        self.enable_drug_dict_text_channel = enable_drug_dict_text_channel
        self.enable_structured_reranking = enable_structured_reranking
        self.enable_expanded_bm25_fields = enable_expanded_bm25_fields
        self.relevance_threshold = relevance_threshold
        self.candidate_pool_size = candidate_pool_size

        if indexes_config is None:
            indexes_config = {
                "diseases": {"index_path": INDEX_FILES["diseases"], "jsonl_path": JSONL_FILES["diseases"], "id_key": "id"},
                "drugs": {"index_path": INDEX_FILES["drugs"], "jsonl_path": JSONL_FILES["drugs"], "id_key": "id"},
                "drug_dict": {"index_path": INDEX_FILES["drug_dict"], "jsonl_path": JSONL_FILES["drug_dict"], "id_key": "id"},
            }

        # 1. Load FAISS wrappers
        self.idx_wrappers = {}
        for name, cfg in indexes_config.items():
            self.idx_wrappers[name] = FaissIndexWrapper(cfg["index_path"], cfg["jsonl_path"], cfg.get("id_key"))

        # 2. Build BM25 indexes
        self.bm25_indexes = {}
        for name, wrapper in self.idx_wrappers.items():
            corpus = list(wrapper.id_to_obj.values())
            if self.enable_expanded_bm25_fields:
                extractor = lambda rec, idx_name=name: extract_text_for_bm25_expanded(idx_name, rec)
            else:
                from app.retriever import extract_text_for_bm25
                extractor = lambda rec, idx_name=name: extract_text_for_bm25(idx_name, rec)

            if self.enable_medical_tokenizer:
                self.bm25_indexes[name] = MedicalBM25Index(corpus, extractor)
            else:
                from app.retriever import BM25Index
                self.bm25_indexes[name] = BM25Index(corpus, extractor)

        # 3. Load Cross-Encoder reranker
        self.reranker = CrossEncoderReranker()
        self.reranker.load_model()

    def search_specific(
        self,
        index_name: str,
        text: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[Tuple[str, float, dict]]:
        """Searches a specific index with hybrid retrieval."""
        if index_name not in self.idx_wrappers:
            raise ValueError(f"Index '{index_name}' not configured.")

        # Normalization
        if self.enable_medical_tokenizer:
            norm = normalize_text_medical(text)
        else:
            from app.utils import normalize_text
            norm = normalize_text(text)

        wrapper = self.idx_wrappers[index_name]
        candidate_pool = max(self.candidate_pool_size, top_k * 3)

        # 1. Dense retrieval
        emb = embed_texts([norm])[0].astype("float32")
        dense_results = wrapper.search(emb, top_k=candidate_pool)

        # 2. Sparse BM25 retrieval
        bm25_index = self.bm25_indexes[index_name]
        bm25_raw = bm25_index.search(text, top_k=candidate_pool)

        bm25_results = []
        keys = list(wrapper.id_to_obj.keys())
        for doc_idx, score in bm25_raw:
            key = keys[doc_idx]
            obj = wrapper.id_to_obj[key]
            bm25_results.append((key, score, obj))

        # 3. Rank fusion (RRF)
        fused_candidates = rrf_fuse(dense_results, bm25_results, k=60)
        rerank_pool = fused_candidates[:candidate_pool]

        # 4. Cross-Encoder reranking
        if not rerank_pool:
            return []

        pairs = []
        for key, score, obj in rerank_pool:
            if self.enable_structured_reranking:
                doc_text = extract_structured_rerank_text(index_name, obj)
            else:
                from app.retriever import extract_text_for_bm25
                doc_text = extract_text_for_bm25(index_name, obj)
            pairs.append((text, doc_text))

        with self.reranker._lock:
            scores = self.reranker.model.predict(pairs)

        reranked = []
        for idx, (key, score, obj) in enumerate(rerank_pool):
            reranked.append((key, float(scores[idx]), obj))

        reranked.sort(key=lambda x: x[1], reverse=True)

        # 5. Relevance Gating / Score Thresholding
        active_threshold = threshold if threshold is not None else self.relevance_threshold
        if active_threshold is not None:
            filtered = [item for item in reranked if item[1] >= active_threshold]
            return filtered[:top_k]

        return reranked[:top_k]

    def search_hybrid_unified(
        self,
        query: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
        query_type: str = "general",
    ) -> Dict[str, List[Tuple[str, float, dict]]]:
        """
        Unified multi-channel search executing diseases, drugs, and conditionally drug_dict.
        """
        results: Dict[str, List[Tuple[str, float, dict]]] = {}

        # 1. Search diseases index
        results["diseases"] = self.search_specific("diseases", query, top_k=top_k, threshold=threshold)

        # 2. Search drugs index
        results["drugs"] = self.search_specific("drugs", query, top_k=top_k, threshold=threshold)

        # 3. Search drug_dict index (Exp D1-2)
        if self.enable_drug_dict_text_channel:
            results["drug_dict"] = self.search_specific("drug_dict", query, top_k=top_k, threshold=threshold)

        return results
