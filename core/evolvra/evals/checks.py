"""Deterministic checks. Free, instant, and never wrong about what they measure."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

MAX_ATTEMPTS = 3
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".jsx",
                 ".html", ".css", ".sql", ".sh", ".ps1", ".csv", ".xml", ".ini", ".cfg", ".env"}
# tool environments agents create while working; never part of the deliverable
JUNK_DIRS = {"venv", "env", "node_modules", "__pycache__", "site-packages", ".venv", ".git", ".tox", ".nox",
             ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints"}


def output_files(output_dir: str | None, *, max_files: int = 20) -> list[Path]:
    if not output_dir:
        return []
    root = Path(output_dir)
    if not root.is_dir():
        return []
    # Prune while walking: junk dirs and venvs of any name (pyvenv.cfg). Other dot-dirs such as .github
    # hold real deliverables; hidden files themselves are still skipped.
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in JUNK_DIRS and not (here / d / "pyvenv.cfg").is_file()]
        files += [here / f for f in filenames if not f.startswith(".")]
    return sorted(files)[:max_files]


BACKUP_MARKERS = (".attempt", ".bak", ".orig", ".old", "~")
PRIMARY_CHARS = 14000   # the main deliverable gets most of the budget
HEAD_SHARE = 0.65       # head + tail excerpt, so section headings late in a document still show


def is_backup(path: Path) -> bool:
    name = path.name.lower()
    return any(m in name for m in BACKUP_MARKERS)


def excerpt(text: str, limit: int) -> str:
    """Head + tail excerpt with an explicit marker. Judges previously saw only the head, which cut the
    'Main questions' section out of a 15 KB interview guide and scored it as missing content."""
    if len(text) <= limit:
        return text
    head = int(limit * HEAD_SHARE)
    tail = limit - head
    omitted = len(text) - head - tail
    return text[:head] + f"\n\n[... {omitted} characters omitted from the middle of this file ...]\n\n" + text[-tail:]


def read_output(output_dir: str | None, *, per_file: int = 4000, total: int = 24000,
                primary_chars: int = PRIMARY_CHARS) -> str:
    """Concatenate text files under output_dir for the judge prompt.

    Order: largest text file first (it is almost always the deliverable), then the rest by size.
    The first file may use `primary_chars`; the others `per_file`; backups (*.attempt*, *.bak) are skipped.
    """
    files = [p for p in output_files(output_dir) if not is_backup(p)]
    texts, binaries = [], []
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix:
            binaries.append(f"--- {path.name} (binary, {path.stat().st_size} bytes) ---")
            continue
        try:
            texts.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    texts.sort(key=lambda pt: -len(pt[1]))
    chunks, used = [], 0
    for i, (path, text) in enumerate(texts):
        limit = primary_chars if i == 0 else per_file
        body = excerpt(text, min(limit, max(0, total - used)))
        if used + len(body) >= total and i > 0:
            chunks.append("--- [more files omitted] ---")
            break
        chunks.append(f"--- {path.name} ({len(text)} chars) ---\n{body}")
        used += len(body)
    return "\n".join(chunks + binaries)


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
