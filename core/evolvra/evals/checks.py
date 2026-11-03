"""Deterministic checks. Free, instant, and never wrong about what they measure."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

MAX_ATTEMPTS = 3
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".jsx",
                 ".html", ".css", ".sql", ".sh", ".ps1", ".csv", ".xml", ".ini", ".cfg", ".env"}
# tool environments agents create while working; never part of the deliverable
JUNK_DIRS = {"venv", "env", "node_modules", "__pycache__", "site-packages"}


def output_files(output_dir: str | None, *, max_files: int = 20) -> list[Path]:
    if not output_dir:
        return []
    root = Path(output_dir)
    if not root.is_dir():
        return []
    files = [p for p in sorted(root.rglob("*")) if p.is_file()
             and not any(part.startswith(".") or part in JUNK_DIRS for part in p.relative_to(root).parts)]
    return files[:max_files]


def read_output(output_dir: str | None, *, per_file: int = 4000, total: int = 12000) -> str:
    """Concatenate text files under output_dir, truncated, for the judge prompt."""
    chunks, used = [], 0
    for path in output_files(output_dir):
        if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix:
            chunks.append(f"--- {path.name} (binary, {path.stat().st_size} bytes) ---")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        text = text[:per_file] + ("\n...[truncated]" if len(text) > per_file else "")
        if used + len(text) > total:
            chunks.append("--- [more files omitted] ---")
            break
        chunks.append(f"--- {path.name} ---\n{text}")
        used += len(text)
    return "\n".join(chunks)


def run_checks(task: sqlite3.Row) -> list[tuple[str, float, dict]]:
    """Return (metric, value 0..1, evidence) tuples for one task row."""
    attempts = json.loads(task["attempts_json"] or "[]")
    last = attempts[-1] if attempts else {}
    # a QA attempt that only exists because the builder had to redo its work is not QA's inefficiency
    builder_retries = sum(1 for a in attempts if a.get("caused_by_builder"))
    files = output_files(task["output_dir"])
    evidence_text = (last.get("evidence") or "").strip()
    results = [
        ("det:output_exists", 1.0 if files else 0.0,
         {"files": [p.name for p in files[:10]], "output_dir": task["output_dir"]}),
        ("det:evidence_present", 1.0 if len(evidence_text) >= 10 else 0.0,
         {"evidence_chars": len(evidence_text)}),
        ("det:efficiency", round(1.0 / max(1, task["attempts"] - builder_retries), 3),
         {"attempts": task["attempts"], "builder_retries": builder_retries, "max": MAX_ATTEMPTS}),
        ("det:verdict", 1.0 if task["verdict"] == "PASS" else 0.0,
         {"verdict": task["verdict"]}),
    ]
    return results


def store_scores(conn: sqlite3.Connection, task_id: int, rows: list[tuple[str, float, dict]],
                 judge_model: str = "deterministic") -> int:
    for metric, value, evidence in rows:
        conn.execute(
            "INSERT INTO scores (task_id, metric, value, evidence_json, judge_model) VALUES (?,?,?,?,?)"
            " ON CONFLICT(task_id, metric, judge_model) DO UPDATE SET value=excluded.value,"
            " evidence_json=excluded.evidence_json, created_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            (task_id, metric, float(value), json.dumps(evidence, ensure_ascii=False), judge_model),
        )
    conn.commit()
    return len(rows)
