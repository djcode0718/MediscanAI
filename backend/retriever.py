# # backend/retriever.py
# import faiss
# import os
# import numpy as np
# from typing import Dict, List, Tuple
# from backend.utils import load_jsonl_to_dict, normalize_text
# from backend.embeddings import embed_texts

# # ----------------------------
# # Path setup
# # ----------------------------
# BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# DATA_DIR = os.path.join(BASE, "data")
# INDEX_DIR = os.path.join(BASE, "indexes")

# INDEX_FILES = {
#     "diseases": os.path.join(INDEX_DIR, "diseases_faiss.index"),
#     "drugs": os.path.join(INDEX_DIR, "drugs_faiss.index"),
#     "drug_dict": os.path.join(INDEX_DIR, "drug_dict_faiss.index"),
# }

# JSONL_FILES = {
#     "diseases": os.path.join(DATA_DIR, "diseases_faiss_data.jsonl"),
#     "drugs": os.path.join(DATA_DIR, "drugs_faiss_data.jsonl"),
#     "drug_dict": os.path.join(DATA_DIR, "drug_dict_faiss_data.jsonl"),
# }


# class FaissIndexWrapper:
#     def __init__(self, index_path: str, jsonl_path: str, id_key: str = None):
#         """
#         Loads FAISS index + JSONL mapping.
#         """
#         self.index_path = index_path
#         self.jsonl_path = jsonl_path
#         self.id_key = id_key

#         if not os.path.exists(index_path):
#             raise FileNotFoundError(f"FAISS index not found: {index_path}")
#         if not os.path.exists(jsonl_path):
#             raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

#         # Load mapping from jsonl
#         self.id_to_obj = load_jsonl_to_dict(jsonl_path, id_key=id_key)

#         # Load faiss index
#         self.index = faiss.read_index(index_path)

#         # Determine dimensionality
#         self.dim = getattr(self.index, "d", None)

#     def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Tuple[str, float, dict]]:
#         """
#         Search the index using a single query embedding (1D array).
#         Returns list of (obj_key, score, obj_dict)
#         """
#         if query_embedding.ndim == 1:
#             q = query_embedding.reshape(1, -1).astype("float32")
#         else:
#             q = query_embedding.astype("float32")

#         distances, indices = self.index.search(q, top_k)
#         results = []
#         for dist, idx in zip(distances[0], indices[0]):
#             if idx < 0:  # not found
#                 continue
#             try:
#                 keys = list(self.id_to_obj.keys())
#                 key = keys[idx] if idx < len(keys) else f"line_{idx}"
#                 obj = self.id_to_obj.get(key, {})
#             except Exception:
#                 key = f"line_{idx}"
#                 obj = self.id_to_obj.get(key, {})
#             results.append((key, float(dist), obj))
#         return results


# class MultiRetriever:
#     def __init__(self, indexes_config: Dict[str, Dict[str, str]] = None):
#         """
#         indexes_config: dict with names mapping to { "index_path": ..., "jsonl_path": ..., "id_key": ... }
#         If None, will use default INDEX_FILES + JSONL_FILES
#         """
#         self.idx_wrappers = {}

#         if indexes_config is None:
#             indexes_config = {
#                 "diseases": {"index_path": INDEX_FILES["diseases"], "jsonl_path": JSONL_FILES["diseases"], "id_key": "id"},
#                 "drugs": {"index_path": INDEX_FILES["drugs"], "jsonl_path": JSONL_FILES["drugs"], "id_key": "id"},
#                 "drug_dict": {"index_path": INDEX_FILES["drug_dict"], "jsonl_path": JSONL_FILES["drug_dict"], "id_key": "id"},
#             }

#         for name, cfg in indexes_config.items():
#             self.idx_wrappers[name] = FaissIndexWrapper(cfg["index_path"], cfg["jsonl_path"], cfg.get("id_key"))

#     def search_all(self, text: str, top_k: int = 3) -> Dict[str, List[Tuple[str, float, dict]]]:
#         """
#         Given text, compute embedding and run search on all indexes.
#         Returns mapping index_name -> list of results
#         """
#         norm = normalize_text(text)
#         # print()
#         emb = embed_texts([norm])[0].astype("float32")
#         out = {}
#         for name, wrapper in self.idx_wrappers.items():
#             out[name] = wrapper.search(emb, top_k=top_k)
#         return out

#     def search_with_custom_embedding(self, embedding: np.ndarray, top_k: int = 3) -> Dict[str, List[Tuple[str, float, dict]]]:
#         """
#         If you already have an embedding (e.g., combined OCR+text embedding), use it directly.
#         """
#         out = {}
#         for name, wrapper in self.idx_wrappers.items():
#             out[name] = wrapper.search(embedding.astype("float32"), top_k=top_k)
#         return out


import faiss
import os
import numpy as np
from typing import Dict, List, Tuple
from backend.utils import load_jsonl_to_dict, normalize_text
from backend.embeddings import embed_texts

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
        indexes_config: dict with names mapping to { "index_path": ..., "jsonl_path": ..., "id_key": ... }
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

    def search_specific(self, index_name: str, text: str, top_k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        Given text, compute embedding and run search on a single, specific index.
        """
        if index_name not in self.idx_wrappers:
            raise ValueError(f"Index '{index_name}' not found in retriever configuration.")
        
        norm = normalize_text(text)
        emb = embed_texts([norm])[0].astype("float32")
        wrapper = self.idx_wrappers[index_name]
        return wrapper.search(emb, top_k=top_k)

    def search_all(self, text: str, top_k: int = 3) -> Dict[str, List[Tuple[str, float, dict]]]:
        """
        Given text, compute embedding and run search on all indexes.
        """
        norm = normalize_text(text)
        emb = embed_texts([norm])[0].astype("float32")
        out = {}
        for name, wrapper in self.idx_wrappers.items():
            out[name] = wrapper.search(emb, top_k=top_k)
        return out