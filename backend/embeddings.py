# backend/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Iterable, List

# Use an efficient CPU model for embeddings (adjust if you want a different one)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model

def embed_texts(texts: Iterable[str]) -> List[np.ndarray]:
    """
    Returns list of numpy arrays embeddings for the given texts.
    """
    model = get_embedding_model()
    embs = model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
    return embs