"""Deterministic checks. Free, instant, and never wrong about what they measure."""
from __future__ import annotations

import json
import os
import re
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
PRIMARY_CHARS = 10000   # the main deliverable gets most of the budget (~2.5k tokens)
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
    return (text[:head] + f"\n\n[... {omitted} characters omitted from the middle of this file to fit the prompt. They exist"
            " but are not shown: do not report this part as missing; if a criterion depends on it, say it could not be"
            " verified from the excerpt ...]\n\n" + text[-tail:])


LOW_PRIORITY_DIRS = {"scratch", "tmp", "temp", "fixture", "fixtures", "work", "build", "dist", "copy", "copies"}
EVIDENCE_DIRS = {"evidence", "proof", "proofs", "results", "logs", "captures", "outputs"}


def read_output(output_dir: str | None, *, per_file: int = 3000, total: int = 16000,
                primary_chars: int = PRIMARY_CHARS, mentions: str = "") -> str:
    """Concatenate text files under output_dir for the judge prompt, each labelled with its path in the folder.

    Order (each group largest first):
      1. the main deliverable: the largest non-scratch file the evidence statement or criteria mention (else the
         largest non-scratch file); it may use `primary_chars`;
      2. proof files: anything under an evidence/proof/results/logs folder, or mentioned by its relative path;
      3. other files the agent mentions by name; 4. everything else; 5. scratch/work/fixture folders last.
    Empty files and backups (*.attempt*, *.bak) are skipped.
    2026-11-08: QA agents keep their proof in evidence/*.txt beside a copy of the builder's code in work/ and a
    large check script. Largest-first (then name matching, which picked the work/ copy) pushed the proof out of
    the prompt, and listing three empty capture files made a judge report "all evidence files are empty".
    """
    if not output_dir:
        return ""
    root = Path(output_dir)
    m = mentions.lower().replace("\\", "/")
    entries, binaries = [], []
    for path in output_files(output_dir, max_files=400):
        if is_backup(path):
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix:
            binaries.append(f"--- {rel} (binary, {path.stat().st_size} bytes) ---")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        dirs = rel.lower().split("/")[:-1]
        low = any(d in LOW_PRIORITY_DIRS for d in dirs)
        by_path = "/" in rel and rel.lower() in m
        by_name = bool(m) and path.name.lower() in m
        proof = by_path or any(d in EVIDENCE_DIRS for d in dirs)
        entries.append({"rel": rel, "text": text, "low": low, "proof": proof, "named": by_name or by_path})
    if not entries:
        return "\n".join(binaries[:20])
    pool = [e for e in entries if not e["low"] and not e["proof"]] or [e for e in entries if not e["low"]] or entries
    primary = max(pool, key=lambda e: (e["named"], len(e["text"])))

    def group(e) -> int:
        if e is primary:
            return 0
        if e["low"]:
            return 4
        return 1 if e["proof"] else 2 if e["named"] else 3

    ordered = sorted(entries, key=lambda e: (group(e), -len(e["text"])))
    chunks, used = [], 0
    for i, e in enumerate(ordered):
        limit = primary_chars if i == 0 else per_file
        body = excerpt(e["text"], min(limit, max(0, total - used)))
        if used + len(body) >= total and i > 0:
            chunks.append(f"--- [{len(ordered) - i} more file(s) omitted to fit the prompt] ---")
            break
        chunks.append(f"--- {e['rel']} ({len(e['text'])} chars) ---\n{body}")
        used += len(body)
    return "\n".join(chunks + binaries[:20])


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


_COUNT_HINT = re.compile(r"\b(words?|paragraphs?|sentences?|characters?|chars|lines?|bytes?|kb|kib)\b", re.IGNORECASE)
_WORD = re.compile(r"[\w']+", re.UNICODE)


def needs_measurements(criteria: list[str]) -> bool:
    return any(_COUNT_HINT.search(c) for c in criteria)


def measure_text(text: str) -> dict:
    """Counts a judge would otherwise guess at. Paragraphs are blank-line separated prose blocks,
    ignoring headings, list items, tables and fenced code."""
    paras, block, in_fence = [], [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        prose = stripped and not stripped.startswith(("#", "|", "- ", "* ", ">")) and not re.match(r"^\d+[.)] ", stripped)
        if prose:
            block.append(stripped)
        elif block:
            paras.append(" ".join(block)); block = []
    if block:
        paras.append(" ".join(block))
    return {
        "bytes": len(text.encode("utf-8")),
        "characters": len(text),
        "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        "words": len(_WORD.findall(text)),
        "paragraphs": len(paras),
        "words_per_paragraph": [len(_WORD.findall(p)) for p in paras[:20]],
    }


def facts_block(name: str, text: str) -> str:
    m = measure_text(text)
    return (f"File `{name}`: {m['bytes']} bytes, {m['characters']} characters, {m['lines']} lines, "
            f"{m['words']} words, {m['paragraphs']} prose paragraphs; words per paragraph: {m['words_per_paragraph']}")


def measured_facts(output_dir: str | None, criteria: list[str]) -> str:
    """Deterministic measurements of the main deliverable, only when a criterion talks about counts."""
    if not needs_measurements(criteria):
        return ""
    texts = []
    for path in output_files(output_dir):
        if is_backup(path) or (path.suffix and path.suffix.lower() not in TEXT_SUFFIXES):
            continue
        try:
            texts.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    texts.sort(key=lambda pt: -len(pt[1]))
    return "\n".join(facts_block(p.name, t) for p, t in texts[:3])
