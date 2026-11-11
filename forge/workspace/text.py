"""Workshop: text normaliser & tokenizer (lesson py-04).

Implement the two functions below. Run the checks from the lesson page ("Verify workshop")
or locally with:  python -m pytest forge/tests/test_part1_text.py -q
"""
from __future__ import annotations

import re  # noqa: F401  (you will probably need these)
import unicodedata  # noqa: F401

STOPWORDS = frozenset(
    "a an and are as at be but by for from has have i if in into is it its of on or that the this to was were what when where which who why will with you your".split()
)


def normalize(text: str) -> str:
    """NFKC-normalise, lowercase, collapse whitespace runs to one space, strip the ends."""
    raise NotImplementedError


def tokenize(text: str) -> list[str]:
    """Return alphanumeric word tokens (internal apostrophes kept), stopwords removed."""
    raise NotImplementedError
