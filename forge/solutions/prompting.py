"""Reference solution — part 6."""
from __future__ import annotations

import html

SYSTEM = (
    "You are a tutor for an AI engineering course. Answer the question using ONLY the numbered sources "
    "provided. Cite every claim with the source number in square brackets, like [1]. If the sources do not "
    "contain enough information, say that you don't know based on the course material. Be concise and precise."
)


def build_grounded_prompt(question: str, passages: list[dict]) -> tuple[str, str]:
    parts = []
    for i, p in enumerate(passages, start=1):
        title = html.escape(str(p.get("title", "")), quote=True)
        text = html.escape(str(p.get("text", "")), quote=False)
        parts.append(f'<source id="{i}" title="{title}">\n{text}\n</source>')
    user = "\n\n".join(parts) + f"\n\n<question>{html.escape(question, quote=False)}</question>"
    return SYSTEM, user
