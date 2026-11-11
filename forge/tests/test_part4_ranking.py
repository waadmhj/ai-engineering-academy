import math

import pytest
from ranking import bm25_scores

DOCS = [
    ["cosine", "similarity", "vectors"],
    ["bm25", "ranking", "keyword", "ranking"],
    ["vectors", "embeddings", "semantic", "search", "vectors"],
]


def reference(q, docs, k1=1.5, b=0.75):
    n = len(docs)
    avgdl = sum(map(len, docs)) / n
    out = []
    for d in docs:
        s = 0.0
        for t in set(q):
            nq = sum(t in x for x in docs)
            idf = math.log((n - nq + 0.5) / (nq + 0.5) + 1)
            f = d.count(t)
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avgdl))
        out.append(s)
    return out


def test_matches_formula():
    q = ["vectors", "ranking"]
    assert bm25_scores(q, DOCS) == pytest.approx(reference(q, DOCS))


def test_repeated_query_tokens_count_once():
    assert bm25_scores(["vectors", "vectors"], DOCS) == pytest.approx(bm25_scores(["vectors"], DOCS))


def test_unmatched_doc_scores_zero():
    assert bm25_scores(["bm25"], DOCS)[0] == 0.0


def test_ranking_order():
    s = bm25_scores(["semantic", "vectors"], DOCS)
    assert s[2] > s[0] > s[1]


def test_custom_parameters():
    q = ["ranking"]
    assert bm25_scores(q, DOCS, k1=1.2, b=0.5) == pytest.approx(reference(q, DOCS, 1.2, 0.5))


def test_empty_inputs():
    assert bm25_scores([], DOCS) == [0.0, 0.0, 0.0]
    assert bm25_scores(["x"], []) == []
