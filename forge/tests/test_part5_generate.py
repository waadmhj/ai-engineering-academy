import pytest
from generate import build_request, generate, parse_response


def test_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    r = build_request("openai", "gpt-x", "sys", "hi", max_tokens=50)
    assert r["url"] == "https://api.openai.com/v1/chat/completions"
    assert r["headers"]["Authorization"] == "Bearer sk-test"
    assert r["json"]["model"] == "gpt-x"
    assert r["json"]["messages"][0] == {"role": "system", "content": "sys"}
    assert r["json"]["messages"][-1] == {"role": "user", "content": "hi"}


def test_anthropic_request(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
    r = build_request("anthropic", "claude-x", "sys", "hi", max_tokens=50)
    assert r["url"] == "https://api.anthropic.com/v1/messages"
    assert r["headers"]["x-api-key"] == "ant-test"
    assert r["headers"]["anthropic-version"] == "2023-06-01"
    assert r["json"]["system"] == "sys"
    assert r["json"]["max_tokens"] == 50
    assert r["json"]["messages"] == [{"role": "user", "content": "hi"}]


def test_ollama_request(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    r = build_request("ollama", "llama3.2", "sys", "hi")
    assert r["url"] == "http://localhost:11434/api/chat"
    assert r["json"]["stream"] is False
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu-box:11434/")
    assert build_request("ollama", "m", "s", "u")["url"] == "http://gpu-box:11434/api/chat"


def test_keys_are_not_hardcoded(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "first")
    a = build_request("openai", "m", "s", "u")["headers"]["Authorization"]
    monkeypatch.setenv("OPENAI_API_KEY", "second")
    b = build_request("openai", "m", "s", "u")["headers"]["Authorization"]
    assert a != b


def test_unknown_provider():
    with pytest.raises(ValueError):
        build_request("nope", "m", "s", "u")


def test_parse_responses():
    assert parse_response("openai", {"choices": [{"message": {"content": "A"}}]}) == "A"
    assert parse_response("anthropic", {"content": [{"type": "text", "text": "B"}, {"type": "text", "text": "C"}]}) == "BC"
    assert parse_response("ollama", {"message": {"content": "D"}}) == "D"


def test_generate_disabled(monkeypatch):
    monkeypatch.delenv("TUTOR_PROVIDER", raising=False)
    assert generate("s", "u") is None
    monkeypatch.setenv("TUTOR_PROVIDER", "none")
    assert generate("s", "u") is None
