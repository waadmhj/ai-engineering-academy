import hashlib

import generate as gen
import pytest
import rag

CHUNKS = [
    {"title": "Cosine", "text": "Cosine similarity compares the angle between two embedding vectors."},
    {"title": "BM25", "text": "BM25 is a keyword ranking function using term frequency and inverse document frequency."},
    {"title": "Chunking", "text": "Chunking splits long documents into overlapping windows before embedding."},
    {"title": "Git", "text": "Git stores snapshots of your project as commits in a directed acyclic graph."},
]


def embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic hashing-trick embedding (same idea the platform uses offline)."""
    v = [0.0] * dim
    for w in text.lower().split():
        h = int(hashlib.md5(w.strip(".,?").encode()).hexdigest(), 16)
        v[h % dim] += 1.0
    return v


def test_rrf_basic():
    assert rag.reciprocal_rank_fusion([[0, 1, 2], [1, 0, 2]]) [:2] in ([0, 1], [1, 0])
    assert rag.reciprocal_rank_fusion([[2, 1], [2, 0]])[0] == 2
    assert set(rag.reciprocal_rank_fusion([[0], [1]])) == {0, 1}


def test_rrf_uses_k():
    # with tiny k the top-ranked item of a single list dominates
    fused = rag.reciprocal_rank_fusion([[0, 1, 2, 3], [3, 2, 1, 0], [3, 0, 1, 2]], k=1)
    assert fused[0] == 3


def test_retrieve_finds_relevant_chunk():
    top = rag.retrieve("How does BM25 keyword ranking work?", CHUNKS, embed, k=2)
    assert top[0] == 1 and len(top) == 2


def test_retrieve_empty():
    assert rag.retrieve("anything", [], embed) == []


def test_answer_extractive_fallback(monkeypatch):
    monkeypatch.setenv("TUTOR_PROVIDER", "none")
    out = rag.answer("What does Git store?", CHUNKS, embed, k=2)
    assert out["sources"][0] == 3
    assert "snapshots" in out["answer"]


def test_answer_uses_generate_and_grounded_prompt(monkeypatch):
    captured = {}

    def fake_generate(system, user):
        captured["user"] = user
        return "Chunks overlap [1]."

    monkeypatch.setattr(gen, "generate", fake_generate)
    out = rag.answer("Why does chunking use overlapping windows?", CHUNKS, embed, k=2)
    assert out["answer"] == "Chunks overlap [1]."
    assert "<source" in captured["user"] and "Why does chunking use overlapping windows?" in captured["user"]
    assert out["sources"][0] == 2


@pytest.mark.parametrize("k", [1, 3])
def test_k_respected(k):
    assert len(rag.retrieve("embedding vectors", CHUNKS, embed, k=k)) == k
