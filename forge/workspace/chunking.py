"""Workshop: overlapping text chunker (lesson da-04)."""
from __future__ import annotations


def chunk_text(text: str, size: int = 120, overlap: int = 30) -> list[str]:
    """Split text into windows of at most `size` words; consecutive windows share `overlap` words."""
    raise NotImplementedError
