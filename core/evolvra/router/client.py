"""One tiny OpenAI-compatible chat client for every free provider. Standard library only.

Providers (all expose an OpenAI-compatible /chat/completions endpoint):
  gemini     https://generativelanguage.googleapis.com/v1beta/openai   key: GEMINI_API_KEY
  groq       https://api.groq.com/openai/v1                           key: GROQ_API_KEY
  openrouter https://openrouter.ai/api/v1                              key: OPENROUTER_API_KEY

Every call goes through the quota guard first and the response cache second, so a
rerun of the same evaluation costs zero requests.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import quota

# Model catalogs change often (Groq retired Llama 3.3 in Aug 2026; Gemini 2.5 Flash is closed to
# new users). Defaults are best-known as of Nov 2026. Override with EVOLVRA_MODEL_<PROVIDER>, and run
# `evolvra models <provider>` to list what your key can actually use.
PROVIDERS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "default_model": "gemini-3.5-flash-lite",   # 3.8-flash timed out on the free tier (Nov 2026)
        "reasoning_style": "flat",      # {"reasoning_effort": "low"}
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "default_model": "openai/gpt-oss-120b",
        "reasoning_style": "flat",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "default_model": "openai/gpt-oss-120b:free",
        "reasoning_style": "nested",    # {"reasoning": {"effort": "low"}}
    },
}

# Today's free models are mostly reasoning models (gpt-oss, Gemini 3.x). They spend output
# tokens on hidden thinking first, so small max_tokens budgets return empty content.
# Judges want short, deterministic answers: keep effort low and budgets generous.
DEFAULT_REASONING_EFFORT = "low"
MIN_MAX_TOKENS = 256


def default_model(provider: str) -> str:
    return os.environ.get(f"EVOLVRA_MODEL_{provider.upper()}") or PROVIDERS[provider]["default_model"]


class ProviderError(RuntimeError):
    pass


@dataclass
class ChatResult:
    provider: str
    model: str
    text: str
    cached: bool
    raw: dict
    finish_reason: str | None = None

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"


def configured_providers() -> list[str]:
    return [p for p, cfg in PROVIDERS.items() if os.environ.get(cfg["key_env"])]


def cache_key(provider: str, model: str, messages: list[dict], params: dict) -> str:
    blob = json.dumps([provider, model, messages, params], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def chat(
    conn: sqlite3.Connection,
    messages: list[dict],
    *,
    provider: str,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
    use_cache: bool = True,
    timeout: float = 120.0,
    _transport=None,
) -> ChatResult:
    """Send a chat completion. `_transport` lets tests inject a fake HTTP function."""
    if provider not in PROVIDERS:
        raise ProviderError(f"unknown provider '{provider}'")
    cfg = PROVIDERS[provider]
    model = model or default_model(provider)
    params = {"temperature": temperature, "max_tokens": max(max_tokens, MIN_MAX_TOKENS)}
    if reasoning_effort and not _flag(conn, provider, model, "no_reasoning"):
        if cfg["reasoning_style"] == "nested":
            params["reasoning"] = {"effort": reasoning_effort}
        else:
            params["reasoning_effort"] = reasoning_effort
    key = cache_key(provider, model, messages, params)

    if use_cache:
        row = conn.execute("SELECT response_json FROM llm_cache WHERE key = ?", (key,)).fetchone()
        if row:
            raw = json.loads(row["response_json"])
            return ChatResult(provider, model, _extract_text(raw), True, raw, _finish_reason(raw))

    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        raise ProviderError(f"{cfg['key_env']} is not set")

    quota.reserve(conn, provider)  # hard stop before any network call
    body = {"model": model, "messages": messages, **params}
    transport = _transport or _http_post
    url = f"{cfg['base_url']}/chat/completions"
    try:
        raw = transport(url, body, api_key, timeout)
    except ProviderError as e:
        # Non-reasoning models (e.g. Gemma) reject reasoning params with HTTP 400.
        # Remember that for this model and retry once without them.
        if _is_reasoning_rejection(e) and ("reasoning_effort" in body or "reasoning" in body):
            _set_flag(conn, provider, model, "no_reasoning")
            body.pop("reasoning_effort", None)
            body.pop("reasoning", None)
            params.pop("reasoning_effort", None)
            params.pop("reasoning", None)
            key = cache_key(provider, model, messages, params)
            quota.reserve(conn, provider)
            raw = transport(url, body, api_key, timeout)
        else:
            raise

    usage = raw.get("usage") or {}
    total = int(usage.get("total_tokens") or 0)
    if total:
        conn.execute(
            "UPDATE provider_usage SET tokens = tokens + ? WHERE provider = ? AND day = ?",
            (total, provider, quota.today()),
        )
    conn.execute(
        "INSERT OR REPLACE INTO llm_cache (key, provider, model, response_json) VALUES (?,?,?,?)",
        (key, provider, model, json.dumps(raw, ensure_ascii=False)),
    )
    conn.commit()
    return ChatResult(provider, model, _extract_text(raw), False, raw, _finish_reason(raw))


def _is_reasoning_rejection(err: ProviderError) -> bool:
    text = str(err).lower()
    return text.startswith("http 400") and ("thinking" in text or "reasoning" in text)


def _flag(conn: sqlite3.Connection, provider: str, model: str, flag: str) -> bool:
    row = conn.execute("SELECT value FROM ingest_state WHERE key = ?",
                       (f"model.{flag}.{provider}/{model}",)).fetchone()
    return bool(row and row["value"] == "1")


def _set_flag(conn: sqlite3.Connection, provider: str, model: str, flag: str) -> None:
    conn.execute("INSERT OR REPLACE INTO ingest_state (key, value) VALUES (?, '1')",
                 (f"model.{flag}.{provider}/{model}",))
    conn.commit()


def list_models(provider: str, *, timeout: float = 30.0, _transport=None) -> list[str]:
    """Model ids the current key can use (GET /models). Not counted against the daily cap."""
    if provider not in PROVIDERS:
        raise ProviderError(f"unknown provider '{provider}'")
    cfg = PROVIDERS[provider]
    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        raise ProviderError(f"{cfg['key_env']} is not set")
    raw = (_transport or _http_get)(f"{cfg['base_url']}/models", api_key, timeout)
    items = raw.get("data") or raw.get("models") or []
    ids = []
    for item in items:
        mid = item.get("id") or item.get("name") or ""
        ids.append(mid.removeprefix("models/"))
    return sorted(i for i in ids if i)


def _http_get(url: str, api_key: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers=_headers(api_key))
    return _send(req, timeout)


def _headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "evolvra/0.1 (+https://github.com/Youssefghazy/Evolvra)",
    }


def _send(req: urllib.request.Request, timeout: float) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:  # keys never appear in error text
        detail = e.read().decode("utf-8", errors="replace")[:500]
        hint = ""
        if e.code == 404 and "model" in detail.lower():
            hint = " | hint: run `evolvra models <provider>` and set EVOLVRA_MODEL_<PROVIDER> in .env"
        elif e.code == 429:
            hint = " | hint: free-tier rate limit; wait or use another provider"
        raise ProviderError(f"HTTP {e.code} from provider: {detail}{hint}") from None
    except urllib.error.URLError as e:
        raise ProviderError(f"network error: {e.reason}") from None
    except TimeoutError:
        raise ProviderError(f"timed out after {timeout:.0f}s waiting for the provider"
                            " | hint: the model may be overloaded on the free tier; try another model") from None
    except OSError as e:
        raise ProviderError(f"connection error: {e}") from None


def _http_post(url: str, body: dict, api_key: str, timeout: float) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers=_headers(api_key))
    return _send(req, timeout)


def _extract_text(raw: dict) -> str:
    try:
        return raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _finish_reason(raw: dict) -> str | None:
    try:
        return raw["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
