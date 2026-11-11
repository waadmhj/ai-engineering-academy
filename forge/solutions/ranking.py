"""Reference solution — part 4."""
from __future__ import annotations

import math
from collections import Counter


def bm25_scores(query_tokens: list[str], docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs_tokens)
    if n == 0 or not query_tokens:
        return [0.0] * n
    avgdl = sum(len(d) for d in docs_tokens) / n or 1.0
    df = Counter(t for d in docs_tokens for t in set(d))
    terms = set(query_tokens)
    idf = {q: math.log((n - df[q] + 0.5) / (df[q] + 0.5) + 1) for q in terms}
    scores = []
    for doc in docs_tokens:
        tf = Counter(doc)
        s = 0.0
        for q in terms:
            f = tf[q]
            if f:
                s += idf[q] * f * (k1 + 1) / (f + k1 * (1 - b + b * len(doc) / avgdl))
        scores.append(s)
    return scores
