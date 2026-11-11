"""Workshop: grounded prompt builder (lesson pe-03)."""
from __future__ import annotations


def build_grounded_prompt(question: str, passages: list[dict]) -> tuple[str, str]:
    """Return (system, user) prompts that ground the answer in numbered <source> passages."""
    raise NotImplementedError
