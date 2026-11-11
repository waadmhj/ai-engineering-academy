"""Reference solution — part 2."""
from __future__ import annotations


def chunk_text(text: str, size: int = 120, overlap: int = 30) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("require size > 0 and 0 <= overlap < size")
    words = text.split()
    chunks: list[str] = []
    step = size - overlap
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return chunks
