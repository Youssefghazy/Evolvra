"""Daily request caps per provider. Hard stops, kept below published free-tier limits.

Evolvra never attaches a payment card to any provider, so the worst case of a bug is
a throttled day, never a bill. These counters make even that unlikely.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime

# Published free limits (third-party reports, Nov 2026) are roughly:
# Gemini Flash ~1500 RPD, Groq ~1000 RPD, OpenRouter free 50 RPD.
# Defaults sit comfortably below. Override with EVOLVRA_CAP_<PROVIDER>.
DEFAULT_CAPS = {"gemini": 1000, "groq": 800, "openrouter": 40}


class QuotaExceeded(RuntimeError):
    pass


def today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def cap_for(provider: str) -> int:
    env = os.environ.get(f"EVOLVRA_CAP_{provider.upper()}")
    return int(env) if env else DEFAULT_CAPS.get(provider, 0)


def used_today(conn: sqlite3.Connection, provider: str) -> int:
    row = conn.execute(
        "SELECT requests FROM provider_usage WHERE provider = ? AND day = ?", (provider, today())
    ).fetchone()
    return row["requests"] if row else 0


def remaining(conn: sqlite3.Connection, provider: str) -> int:
    return max(0, cap_for(provider) - used_today(conn, provider))


def reserve(conn: sqlite3.Connection, provider: str, tokens: int = 0) -> None:
    """Count one request *before* sending it. Raises QuotaExceeded at the cap."""
    cap = cap_for(provider)
    if cap <= 0:
        raise QuotaExceeded(f"provider '{provider}' has no quota configured")
    if used_today(conn, provider) >= cap:
        raise QuotaExceeded(f"daily cap reached for {provider} ({cap} requests)")
    conn.execute(
        "INSERT INTO provider_usage (provider, day, requests, tokens) VALUES (?,?,1,?)"
        " ON CONFLICT(provider, day) DO UPDATE SET requests = requests + 1, tokens = tokens + excluded.tokens",
        (provider, today(), tokens),
    )
    conn.commit()


def status(conn: sqlite3.Connection) -> list[dict]:
    return [
        {"provider": p, "cap": cap_for(p), "used": used_today(conn, p), "remaining": remaining(conn, p)}
        for p in DEFAULT_CAPS
    ]
