#!/usr/bin/env python3
"""
MediScanAI 2.0 — Multi-Tiered Candidate Generation Engine.
Performs index retrieval avoiding unindexed global fuzzy scans.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple


def retrieve_candidates(
    query_parsed,
    index: dict,
    max_token_candidates: int = 300,
    max_ngram_candidates: int = 300,
) -> List[str]:
    """
    Tiered candidate generation:
    1. Exact normalized name
    2. Exact alphanumeric code / identifier
    3. Exact compact form
    4. Discriminative token inverted index (IDF weighted)
    5. Character n-gram index
    """
    candidates: Dict[str, float] = defaultdict(float)

    # Tier 1: Exact Normalized
    exact_names = index["exact_index"].get(query_parsed.normalized, [])
    if exact_names:
        return exact_names

    # Tier 2: Alphanumeric Identifiers
    for ident in query_parsed.identifiers:
        for name in index["identifier_index"].get(ident, []):
            candidates[name] += 100.0

    # Tier 3: Compact Name
    if query_parsed.compact:
        for name in index["compact_index"].get(query_parsed.compact, []):
            candidates[name] += 80.0

    # Tier 4: IDF-weighted Token Blocking
    sorted_tokens = sorted(
        query_parsed.tokens,
        key=lambda t: index["token_idf"].get(t, 1.0),
        reverse=True
    )
    for token in sorted_tokens:
        idf = index["token_idf"].get(token, 1.0)
        # Skip hyper-frequent stopwords with low IDF unless nothing else exists
        if idf < 1.8 and len(candidates) >= 50:
            continue
        for name in index["token_index"].get(token, ()):
            candidates[name] += idf
            if len(candidates) >= max_token_candidates:
                break

    # Tier 5: Character N-grams (if candidate pool remains small)
    if len(candidates) < 100 and query_parsed.compact:
        ngrams = [
            query_parsed.compact[i:i+3]
            for i in range(len(query_parsed.compact) - 2)
        ]
        sorted_ngrams = sorted(
            ngrams,
            key=lambda g: index["ngram_idf"].get(g, 1.0),
            reverse=True
        )
        seen_ngrams = 0
        for gram in sorted_ngrams:
            gidf = index["ngram_idf"].get(gram, 1.0)
            for name in index["ngram_index"].get(gram, ()):
                candidates[name] += 0.2 * gidf
                seen_ngrams += 1
                if seen_ngrams >= max_ngram_candidates:
                    break
            if seen_ngrams >= max_ngram_candidates:
                break

    # Sort and return top candidates
    sorted_candidates = sorted(
        candidates.items(),
        key=lambda x: x[1],
        reverse=True
    )[:max_token_candidates]

    return [name for name, _ in sorted_candidates]