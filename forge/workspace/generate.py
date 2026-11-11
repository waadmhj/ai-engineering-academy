"""Workshop: provider-agnostic LLM client (lesson api-08).

Never hard-code API keys — read them from the environment.
"""
from __future__ import annotations

import os  # noqa: F401


def build_request(provider: str, model: str, system: str, user: str, max_tokens: int = 800) -> dict:
    """Return {"url": str, "headers": dict, "json": dict} for openai | anthropic | ollama."""
    raise NotImplementedError


def parse_response(provider: str, data: dict) -> str:
    """Extract the generated text from a provider's JSON response."""
    raise NotImplementedError


def generate(system: str, user: str) -> str | None:
    """Call the provider configured by TUTOR_PROVIDER / TUTOR_MODEL; None if unset or 'none'."""
    raise NotImplementedError
