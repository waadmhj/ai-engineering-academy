"""Workshop: retrieval-augmented answering (lesson rag-04).

Reuse your earlier workshop modules: text, vectors, ranking, prompting, generate.
"""
from __future__ import annotations

from collections.abc import Callable


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[int]:
    raise NotImplementedError


def retrieve(question: str, chunks: list[dict], embed: Callable[[str], list[float]], k: int = 4) -> list[int]:
    raise NotImplementedError


def answer(question: str, chunks: list[dict], embed: Callable[[str], list[float]], k: int = 4) -> dict:
    raise NotImplementedError
