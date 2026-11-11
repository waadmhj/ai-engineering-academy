"""Reference solution — part 1."""
from __future__ import annotations

import re
import unicodedata

STOPWORDS = frozenset(
    "a an and are as at be but by for from has have i if in into is it its of on or that the this to was were what when where which who why will with you your".split()
)
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return " ".join(text.split())


def tokenize(text: str) -> list[str]:
    return [t for t in _WORD.findall(normalize(text)) if t not in STOPWORDS]
