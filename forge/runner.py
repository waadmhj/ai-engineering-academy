"""Tutor runtime — executed by the platform in a subprocess, using ONLY the learner's workspace code.

stdin:  {"question": str, "documents": [{"id", "title", "text"}], "k": int}
stdout: {"answer": str, "sources": [{"doc_id", "title", "excerpt"}], "used_llm": bool}

The platform provides only `embed` (a deterministic hashing-trick embedding, no model download needed);
chunking, ranking, similarity, prompting, generation and the RAG pipeline are the learner's own.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("FORGE_DIR", Path(__file__).parent / "workspace")).resolve()
sys.path.insert(0, str(WORKSPACE))

import chunking  # noqa: E402
import rag  # noqa: E402
import text  # noqa: E402

DIM = 512


def embed(s: str) -> list[float]:
    v = [0.0] * DIM
    for tok in text.tokenize(s):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 9) & 1 else -1.0  # signed hashing reduces collision bias
    return v


def main() -> None:
    req = json.load(sys.stdin)
    chunks, owner = [], []
    for doc in req["documents"]:
        for piece in chunking.chunk_text(doc["text"], size=110, overlap=25):
            chunks.append({"title": doc["title"], "text": piece})
            owner.append(doc)
    used_llm = os.environ.get("TUTOR_PROVIDER", "none").strip().lower() not in ("", "none")
    out = rag.answer(req["question"], chunks, embed, k=int(req.get("k", 4)))
    sources = [{"doc_id": owner[i]["id"], "title": owner[i]["title"], "excerpt": chunks[i]["text"][:400]} for i in out.get("sources", [])]
    json.dump({"answer": out.get("answer", ""), "sources": sources, "used_llm": used_llm}, sys.stdout)


if __name__ == "__main__":
    main()
