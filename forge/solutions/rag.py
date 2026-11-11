"""Reference solution — part 7."""
from __future__ import annotations

from collections.abc import Callable

import generate as gen
import prompting
import ranking
import text
import vectors


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for ranking_ in rankings:
        for rank, idx in enumerate(ranking_, start=1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda i: (-scores[i], i))


def retrieve(question: str, chunks: list[dict], embed: Callable[[str], list[float]], k: int = 4) -> list[int]:
    if not chunks:
        return []
    bm25 = ranking.bm25_scores(text.tokenize(question), [text.tokenize(c["text"]) for c in chunks])
    lexical = sorted(range(len(chunks)), key=lambda i: (-bm25[i], i))
    dense = vectors.top_k(embed(question), [embed(c["text"]) for c in chunks], len(chunks))
    return reciprocal_rank_fusion([lexical, dense])[:k]


def answer(question: str, chunks: list[dict], embed: Callable[[str], list[float]], k: int = 4) -> dict:
    idx = retrieve(question, chunks, embed, k)
    if not idx:
        return {"answer": "I couldn't find anything about that in the course material.", "sources": []}
    system, user = prompting.build_grounded_prompt(question, [chunks[i] for i in idx])
    out = gen.generate(system, user)
    if out is None:
        out = chunks[idx[0]]["text"]
    return {"answer": out, "sources": idx}
