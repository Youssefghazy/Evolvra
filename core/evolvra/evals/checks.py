"""Deterministic checks. Free, instant, and never wrong about what they measure."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

MAX_ATTEMPTS = 3
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".jsx",
                 ".html", ".htm", ".css", ".sql", ".sh", ".ps1", ".psm1", ".psd1", ".bat", ".cmd", ".csv", ".tsv",
                 ".xml", ".ini", ".cfg", ".log", ".stdout", ".stderr", ".out", ".err"}
# never read into a judge prompt (it goes to external providers), never even listed
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "secrets.json"}
SECRET_SUFFIXES = {".env", ".pem", ".key", ".pfx", ".p12"}
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


LOW_PRIORITY_DIRS = {"scratch", "tmp", "temp", "fixture", "fixtures", "fx", "work", "build", "dist", "copy", "copies",
                     "mutants", "mutant", "mutations", "sabotage", "sabotaged", "broken", "negative"}
# deliberately broken copies a QA agent makes to prove its checks bite (10 Nov: a judge graded one as the subject)
DECOY_MARKERS = ("mutant", "sabotage", "broken-copy")
EVIDENCE_DIRS = {"evidence", "proof", "proofs", "results", "logs", "captures", "outputs"}
BULK_DIR_FILES = 50        # an unrecognised folder with more files than this is treated like scratch
WALK_LIMIT = 20000         # metadata only; contents are read just for the files that make it into the prompt
NAMED_OMITTED = 25
LOW_SAMPLES = 3            # scratch/fixture files shown with content, as examples only


def _walk_all(root: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in JUNK_DIRS and not (here / d / "pyvenv.cfg").is_file()]
        files += [here / f for f in filenames if not f.startswith(".")]
        if len(files) >= WALK_LIMIT:
            break
    return files


def read_output(output_dir: str | None, *, per_file: int = 3000, total: int = 16000,
                primary_chars: int = PRIMARY_CHARS, mentions: str = "") -> str:
    """Build the judge's view of an output folder within `total` characters (headers included).

    Ranking happens on metadata for every file before anything is cut (8 Nov: a folder of 6,458 fixtures hid the
    agent's report behind a 400-file cap). Groups, each largest first:
      0. the main deliverable: the largest non-scratch, non-proof file the agent mentions (else the largest);
      1. proof files the main deliverable or the agent's statement cite by path, then the other proof files
         (anything under evidence/, proof/, results/, logs/...);
      2. other files the agent names; 3. everything else;
      4. scratch, work, fixtures, copies, and any unrecognised folder holding more than 50 files.
    With proof files present the main file gets ~35% of the budget and cited proofs come first, each at least
    ~800 characters; what does not fit is named (proof first) with a note that it exists. Empty files are skipped.
    """
    if not output_dir:
        return ""
    root = Path(output_dir)
    if not root.is_dir():
        return ""
    paths = [p for p in _walk_all(root) if not is_backup(p)]
    top_counts: dict[str, int] = {}
    for p in paths:
        parts = p.relative_to(root).parts
        if len(parts) > 1:
            top_counts[parts[0].lower()] = top_counts.get(parts[0].lower(), 0) + 1
    m = mentions.lower().replace("\\", "/")
    entries, binaries = [], []
    for path in paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size == 0:
            continue  # empty captures (any suffix) say nothing and read as "the evidence is empty"
        if path.name.lower() in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix:
            binaries.append(f"--- {rel} (binary, {size} bytes) ---")
            continue
        dirs = rel.lower().split("/")[:-1]
        proof = any(d in EVIDENCE_DIRS for d in dirs)
        bulk = bool(dirs) and dirs[0] not in EVIDENCE_DIRS and top_counts.get(dirs[0], 0) > BULK_DIR_FILES
        decoy = any(mk in path.name.lower() for mk in DECOY_MARKERS)
        low = decoy or (not proof and (bulk or any(d in LOW_PRIORITY_DIRS for d in dirs)))
        by_path = "/" in rel and rel.lower() in m
        named = by_path or (bool(m) and path.name.lower() in m)
        entries.append({"path": path, "rel": rel, "size": size, "low": low, "proof": (proof or by_path) and not decoy,
                        "named": named, "cited": by_path, "top": not dirs})
    if not entries:
        return "\n".join(binaries[:20])
    pool = [e for e in entries if not e["low"] and not e["proof"]] or [e for e in entries if not e["low"]] or entries
    primary = max(pool, key=lambda e: (e["named"], e["top"], e["size"]))   # a named top-level file is the deliverable

    def text_of(e) -> str:
        if "text" not in e:
            try:
                e["text"] = e["path"].read_text(encoding="utf-8", errors="replace")
            except OSError:
                e["text"] = ""
        return e["text"]

    cited_by_primary = text_of(primary).lower().replace("\\", "/")
    for e in entries:  # proofs the main report points at (by path) are the ones a judge needs to check it
        if e["proof"] and "/" in e["rel"] and e["rel"].lower() in cited_by_primary:
            e["cited"] = True

    def rank(e):
        if e is primary:
            return (0, 0, 0, "")
        if e["low"]:
            return (4, 0, -e["size"], e["rel"])
        if e["proof"]:
            return (1, 0 if e["cited"] else 1, -e["size"], e["rel"])
        return (2 if e["named"] else 3, 0, -e["size"], e["rel"])

    ordered = sorted(entries, key=rank)
    proofs = [e for e in ordered if rank(e)[0] == 1]
    first_limit = min(primary_chars, int(total * 0.35)) if proofs else primary_chars
    proof_room = int((total - min(primary["size"], first_limit)) * 0.8)
    # small proofs cost only their size; large ones share the room, never below ~800 characters each
    per_proof = max(800, min(per_file, proof_room // len(proofs))) if proofs else per_file
    chunks, used, rest, low_shown = [], 0, [], 0
    for i, e in enumerate(ordered):
        is_proof = rank(e)[0] == 1
        room = total - used
        # scratch/fixture files are noise: at most LOW_SAMPLES of them as examples, the rest summarised by folder
        # (8 Nov, Windows: spare room filled with ~81 fixture files because NTFS lists them first)
        if (room < 400 and i > 0) or (e["low"] and e is not primary and low_shown >= LOW_SAMPLES):
            rest.append(e)
            continue
        if e["low"] and e is not primary:
            low_shown += 1
        header = f"--- {e['rel']} ({e['size']} bytes) ---\n"
        limit = first_limit if i == 0 else per_proof if is_proof else per_file
        body = excerpt(text_of(e), max(0, min(limit, room - len(header))))
        chunks.append(header + body)
        used += len(header) + len(body)
    if rest:  # name what was left out (proof first), so the judge knows it exists instead of calling it missing
        named = [e for e in rest if not e["low"]][:NAMED_OMITTED]
        low_dirs: dict[str, int] = {}
        for e in rest:
            if e["low"]:
                top = e["rel"].split("/")[0] + "/"
                low_dirs[top] = low_dirs.get(top, 0) + 1
        parts = [f"{e['rel']} ({e['size']} bytes)" for e in named]
        hidden = len([e for e in rest if not e["low"]]) - len(named)
        if hidden > 0:
            parts.append(f"{hidden} more")
        parts += [f"{d} ({n} files)" for d, n in sorted(low_dirs.items(), key=lambda kv: -kv[1])]
        chunks.append("--- not shown to fit the prompt (they exist; do not report them as missing): "
                      + ", ".join(parts) + " ---")
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
