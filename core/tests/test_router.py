import pytest

from evolvra.router import client, quota
from evolvra.store import db


def fake_transport(reply="pong"):
    calls = []

    def _t(url, body, api_key, timeout):
        calls.append((url, body, api_key))
        return {"choices": [{"message": {"content": reply}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 7}}

    _t.calls = calls
    return _t


def test_quota_hard_stop(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setenv("EVOLVRA_CAP_GROQ", "2")
    quota.reserve(conn, "groq")
    quota.reserve(conn, "groq")
    assert quota.remaining(conn, "groq") == 0
    with pytest.raises(quota.QuotaExceeded):
        quota.reserve(conn, "groq")


def test_chat_uses_cache_and_counts_requests(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    transport = fake_transport()
    msgs = [{"role": "user", "content": "hi"}]

    first = client.chat(conn, msgs, provider="groq", _transport=transport)
    second = client.chat(conn, msgs, provider="groq", _transport=transport)

    assert first.text == "pong" and not first.cached
    assert second.cached and len(transport.calls) == 1
    assert quota.used_today(conn, "groq") == 1
    assert transport.calls[0][2] == "test-key"
    assert transport.calls[0][0].startswith("https://api.groq.com/openai/v1/")


def test_missing_key_never_hits_network(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    transport = fake_transport()
    with pytest.raises(client.ProviderError):
        client.chat(conn, [{"role": "user", "content": "x"}], provider="gemini", _transport=transport)
    assert transport.calls == [] and quota.used_today(conn, "gemini") == 0


def test_quota_blocks_before_network(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("EVOLVRA_CAP_OPENROUTER", "0")
    transport = fake_transport()
    with pytest.raises(quota.QuotaExceeded):
        client.chat(conn, [{"role": "user", "content": "x"}], provider="openrouter", _transport=transport)
    assert transport.calls == []


def test_default_model_env_override(monkeypatch):
    monkeypatch.delenv("EVOLVRA_MODEL_GROQ", raising=False)
    assert client.default_model("groq") == client.PROVIDERS["groq"]["default_model"]
    monkeypatch.setenv("EVOLVRA_MODEL_GROQ", "some/new-model")
    assert client.default_model("groq") == "some/new-model"


def test_list_models_parses_openai_and_gemini_shapes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    calls = []

    def transport(url, api_key, timeout):
        calls.append(url)
        return {"data": [{"id": "models/gemini-3.8-flash"}, {"id": "b-model"}, {"name": "models/a"}]}

    ids = client.list_models("gemini", _transport=transport)
    assert ids == ["a", "b-model", "gemini-3.8-flash"]
    assert calls[0].endswith("/models")


def test_reasoning_effort_and_token_floor_per_provider(monkeypatch):
    conn = db.connect(":memory:")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    t = fake_transport()
    msgs = [{"role": "user", "content": "x"}]
    r = client.chat(conn, msgs, provider="groq", max_tokens=8, _transport=t)
    body = t.calls[0][1]
    assert body["reasoning_effort"] == "low" and body["max_tokens"] == client.MIN_MAX_TOKENS
    assert r.finish_reason == "stop" and not r.truncated
    client.chat(conn, msgs, provider="openrouter", _transport=t)
    assert t.calls[1][1]["reasoning"] == {"effort": "low"} and "reasoning_effort" not in t.calls[1][1]
    client.chat(conn, msgs, provider="groq", reasoning_effort=None, _transport=t, use_cache=False)
    assert "reasoning_effort" not in t.calls[2][1]
