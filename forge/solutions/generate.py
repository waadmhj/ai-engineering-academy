"""Reference solution — part 5."""
from __future__ import annotations

import os


def build_request(provider: str, model: str, system: str, user: str, max_tokens: int = 800) -> dict:
    if provider == "openai":
        return {
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}", "Content-Type": "application/json"},
            "json": {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        }
    if provider == "anthropic":
        return {
            "url": "https://api.anthropic.com/v1/messages",
            "headers": {
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            "json": {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]},
        }
    if provider == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        return {
            "url": f"{host}/api/chat",
            "headers": {"Content-Type": "application/json"},
            "json": {
                "model": model,
                "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        }
    raise ValueError(f"unknown provider: {provider}")


def parse_response(provider: str, data: dict) -> str:
    if provider == "openai":
        return data["choices"][0]["message"]["content"]
    if provider == "anthropic":
        return "".join(block.get("text", "") for block in data["content"] if block.get("type") == "text")
    if provider == "ollama":
        return data["message"]["content"]
    raise ValueError(f"unknown provider: {provider}")


def generate(system: str, user: str) -> str | None:
    provider = os.environ.get("TUTOR_PROVIDER", "none").strip().lower()
    if provider in ("", "none"):
        return None
    import httpx

    model = os.environ.get("TUTOR_MODEL", "")
    req = build_request(provider, model, system, user)
    resp = httpx.post(req["url"], headers=req["headers"], json=req["json"], timeout=60)
    resp.raise_for_status()
    return parse_response(provider, resp.json())
