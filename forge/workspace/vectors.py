"""Workshop: vector similarity in plain Python (lesson ma-02)."""
from __future__ import annotations

from collections.abc import Sequence

Vector = Sequence[float]


def dot(a: Vector, b: Vector) -> float:
    raise NotImplementedError


def norm(a: Vector) -> float:
    raise NotImplementedError


def cosine_similarity(a: Vector, b: Vector) -> float:
    raise NotImplementedError


def top_k(query: Vector, vectors: Sequence[Vector], k: int) -> list[int]:
    """Indices of the k vectors most cosine-similar to `query`, best first (ties: lower index first)."""
    raise NotImplementedError
