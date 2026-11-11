"""Workshop: Okapi BM25 (lesson ml-05)."""
from __future__ import annotations

import math  # noqa: F401
from collections import Counter  # noqa: F401


def bm25_scores(query_tokens: list[str], docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """One BM25 score per document in `docs_tokens`."""
    raise NotImplementedError
