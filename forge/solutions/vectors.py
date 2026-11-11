"""Reference solution — part 3."""
from __future__ import annotations

import math
from collections.abc import Sequence

Vector = Sequence[float]


def dot(a: Vector, b: Vector) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    return sum(x * y for x, y in zip(a, b))


def norm(a: Vector) -> float:
    return math.sqrt(dot(a, a))


def cosine_similarity(a: Vector, b: Vector) -> float:
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)


def top_k(query: Vector, vectors: Sequence[Vector], k: int) -> list[int]:
    scores = [cosine_similarity(query, v) for v in vectors]
    return sorted(range(len(vectors)), key=lambda i: (-scores[i], i))[: max(k, 0)]
