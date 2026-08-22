import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import faiss

import math
import numpy as np
from typing import Dict, List, Tuple, Any
from app.utils import load_jsonl_to_dict, normalize_text
from app.embeddings import embed_texts

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE, "data")
INDEX_DIR = os.path.join(BASE, "indexes")

INDEX_FILES = {
    "diseases": os.path.join(INDEX_DIR, "diseases_faiss.index"),
    "drugs": os.path.join(INDEX_DIR, "drugs_faiss.index"),
    "drug_dict": os.path.join(INDEX_DIR, "drug_dict_faiss.index"),
}

JSONL_FILES = {
    "diseases": os.path.join(DATA_DIR, "diseases_faiss_data.jsonl"),
    "drugs": os.path.join(DATA_DIR, "drugs_faiss_data.jsonl"),
    "drug_dict": os.path.join(DATA_DIR, "drug_dict_faiss_data.jsonl"),
}


def extract_text_for_bm25(index_name: str, record: dict) -> str:
    """
    Extract searchable text string from dynamic index dictionary objects.
    """
    if index_name == "diseases":
        chunk = record.get('chunk', {})
        disease = chunk.get('disease', '')
        symptoms = " ".join(chunk.get('symptoms', []))
        return f"{disease} {symptoms}"
    elif index_name == "drugs":
        brand = record.get('brand_name', '')
        generic = record.get('generic_name', '')
        substances = " ".join(record.get('substance_name', []))
        usage = record.get('indications_and_usage', '')
        return f"{brand} {generic} {substances} {usage}"
    elif index_name == "drug_dict":
        return record.get('drug_name', '')
    return str(record)


class BM25Index:
    def __init__(self, corpus: List[Dict[str, Any]], text_field_extractor, k1: float = 1.5, b: float = 0.75):
        """
        Pure-Python, self-contained implementation of the BM25 sparse vector scoring algorithm.
        """
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.N = len(corpus)
        
        self.doc_lengths = []
        self.doc_term_freqs = []  # list of Dict[str, int]
        
        self.df = {}
        for doc in corpus:
            text = text_field_extractor(doc) or ""
            tokens = self._tokenize(text)
            self.doc_lengths.append(len(tokens))
            
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)
            
            for t in tf.keys():
                self.df[t] = self.df.get(t, 0) + 1
                
        self.avgdl = sum(self.doc_lengths) / self.N if self.N > 0 else 1.0
        
        # Calculate IDF values
        self.idf = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(1.0 + (self.N - freq + 0.5) / (freq + 0.5))

    def _tokenize(self, text: str) -> List[str]:
        from app.utils import normalize_text
        normalized = normalize_text(text)
        return [w for w in normalized.split() if w]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        query_tokens = self._tokenize(query)
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


def rrf_fuse(faiss_results: List[Tuple[str, float, dict]], bm25_results: List[Tuple[str, float, dict]], k: int = 60) -> List[Tuple[str, float, dict]]:
    """
    Fuses rankings from FAISS (Euclidean/cosine distance) and BM25 using Reciprocal Rank Fusion.
    """
    scores = {}
    
    # Cosine/Euclidean distance from FAISS: lower score is closer (assumed sorted ascending)
    for rank, (key, score, obj) in enumerate(faiss_results, 1):
        if key not in scores:
            scores[key] = {'rrf_score': 0.0, 'obj': obj}
        scores[key]['rrf_score'] += 1.0 / (k + rank)
        
    # BM25 scores: higher score is better (assumed sorted descending)
    for rank, (key, score, obj) in enumerate(bm25_results, 1):
        if key not in scores:
            scores[key] = {'rrf_score': 0.0, 'obj': obj}
        scores[key]['rrf_score'] += 1.0 / (k + rank)
        
    fused_results = []
    for key, val in scores.items():
        fused_results.append((key, val['rrf_score'], val['obj']))
        
    fused_results.sort(key=lambda x: x[1], reverse=True)
    return fused_results


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = None
        self.model_name = model_name

    def load_model(self):
        if self.model is None:
            from sentence_transformers import CrossEncoder
            print(f"🎙️ Loading Cross-Encoder Model '{self.model_name}'...")
            self.model = CrossEncoder(self.model_name, device="cpu")

    def rerank(self, query: str, candidates: List[Tuple[str, float, dict]], index_name: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        if not candidates:
            return []
        
        self.load_model()
        pairs = []
        for key, score, obj in candidates:
            doc_text = extract_text_for_bm25(index_name, obj)
            pairs.append((query, doc_text))
            
        scores = self.model.predict(pairs)
        
        reranked = []
        for idx, (key, score, obj) in enumerate(candidates):
            reranked.append((key, float(scores[idx]), obj))
            
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked[:top_k]


class FaissIndexWrapper:
    def __init__(self, index_path: str, jsonl_path: str, id_key: str = None):
        """
        Loads FAISS index + JSONL mapping.
        """
        self.index_path = index_path
        self.jsonl_path = jsonl_path
        self.id_key = id_key

        if not os.path.exists(index_path):
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not os.path.exists(jsonl_path):
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

        self.id_to_obj = load_jsonl_to_dict(jsonl_path, id_key=id_key)
        self.index = faiss.read_index(index_path)
        self.dim = getattr(self.index, "d", None)

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        Search the index using a single query embedding (1D array).
        Returns list of (obj_key, score, obj_dict)
        """
        if query_embedding.ndim == 1:
            q = query_embedding.reshape(1, -1).astype("float32")
        else:
            q = query_embedding.astype("float32")

        distances, indices = self.index.search(q, top_k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            try:
                keys = list(self.id_to_obj.keys())
                key = keys[idx] if idx < len(keys) else f"line_{idx}"
                obj = self.id_to_obj.get(key, {})
            except Exception:
                key = f"line_{idx}"
                obj = self.id_to_obj.get(key, {})
            results.append((key, float(dist), obj))
        return results


class MultiRetriever:
    def __init__(self, indexes_config: Dict[str, Dict[str, str]] = None):
        """
        Manages indexes for FAISS and BM25, and coordinates Rank Fusion and Reranking.
        """
        self.idx_wrappers = {}

        if indexes_config is None:
            indexes_config = {
                "diseases": {"index_path": INDEX_FILES["diseases"], "jsonl_path": JSONL_FILES["diseases"], "id_key": "id"},
                "drugs": {"index_path": INDEX_FILES["drugs"], "jsonl_path": JSONL_FILES["drugs"], "id_key": "id"},
                "drug_dict": {"index_path": INDEX_FILES["drug_dict"], "jsonl_path": JSONL_FILES["drug_dict"], "id_key": "id"},
            }

        for name, cfg in indexes_config.items():
            self.idx_wrappers[name] = FaissIndexWrapper(cfg["index_path"], cfg["jsonl_path"], cfg.get("id_key"))

        # Build in-memory BM25 indexes
        self.bm25_indexes = {}
        print("🔍 [Retriever] Building in-memory BM25 indexes...")
        for name, wrapper in self.idx_wrappers.items():
            corpus = list(wrapper.id_to_obj.values())
            extractor = lambda rec, idx_name=name: extract_text_for_bm25(idx_name, rec)
            self.bm25_indexes[name] = BM25Index(corpus, extractor)
        print("   ↳ BM25 indexes built successfully.")

        # Warm up CrossEncoder model
        self.reranker = CrossEncoderReranker()
        self.reranker.load_model()

    def search_specific(self, index_name: str, text: str, top_k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        Given text, compute embedding and run search on a single, specific index.
        """
        if index_name not in self.idx_wrappers:
            raise ValueError(f"Index '{index_name}' not found in retriever configuration.")
        
        norm = normalize_text(text)
        emb = embed_texts([norm])[0].astype("float32")
        wrapper = self.idx_wrappers[index_name]
        
        # 1. Retrieve candidates via Dense Vector Search
        candidate_pool_size = max(15, top_k * 3)
        dense_results = wrapper.search(emb, top_k=candidate_pool_size)
        
        # 2. Retrieve candidates via Sparse BM25 Search
        bm25_index = self.bm25_indexes[index_name]
        bm25_raw = bm25_index.search(text, top_k=candidate_pool_size)
        
        bm25_results = []
        keys = list(wrapper.id_to_obj.keys())
        for doc_idx, score in bm25_raw:
            key = keys[doc_idx]
            obj = wrapper.id_to_obj[key]
            bm25_results.append((key, score, obj))
            
        # 3. Fuse Ranks using RRF
        fused_candidates = rrf_fuse(dense_results, bm25_results)
        
        # 4. Rerank using Cross-Encoder
        # Rerank the top fused candidates to return the top_k
        rerank_pool = fused_candidates[:candidate_pool_size]
        final_results = self.reranker.rerank(text, rerank_pool, index_name, top_k=top_k)
        
        return final_results

    def search_all(self, text: str, top_k: int = 3) -> Dict[str, List[Tuple[str, float, dict]]]:
        """
        Given text, compute embedding and run search on all indexes.
        """
        out = {}
        for name in self.idx_wrappers.keys():
            out[name] = self.search_specific(name, text, top_k=top_k)
        return out