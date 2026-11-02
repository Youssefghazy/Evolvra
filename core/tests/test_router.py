import pytest

from evolvra.router import client, quota
from evolvra.store import db


def fake_transport(reply="pong"):
    calls = []

    def _t(url, body, api_key, timeout):
        calls.append((url, body, api_key))
        return {"choices": [{"message": {"content": reply}}], "usage": {"total_tokens": 7}}

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
