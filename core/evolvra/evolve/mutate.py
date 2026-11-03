"""Propose persona variants. One targeted change per variant, full file returned, lint-checked."""
from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..registry import personas
from ..router import client, quota
from .diagnose import Diagnosis

# The mutator needs to write long, careful Markdown. gpt-oss-120b on Groq is the strongest free writer.
DEFAULT_MUTATOR = ("groq", "openai/gpt-oss-120b")

SYSTEM = (
    "You are a senior prompt engineer improving one AI agent persona file. You make ONE targeted, "
    "evidence-driven change per revision and keep everything else intact. You return the complete "
    "revised Markdown file and nothing else: no preamble, no code fences."
)

PROMPT = """# Current persona file (Markdown with YAML frontmatter)
<<<PERSONA
{persona}
PERSONA

# Evidence of failures
{diagnosis}

# Your assignment
Revise the persona to fix this failure class: **{target}**
{hint}

Rules:
1. Keep the YAML frontmatter keys exactly (name, description, color, emoji, vibe if present). Do not rename the agent.
2. Change as little as possible: add or sharpen one rule, one checklist, one workflow step, or one deliverable template that directly prevents the failure. Prefer concrete, checkable instructions over adjectives.
3. Keep all existing section headings. The file must stay a complete, valid persona at least as long as before.
4. Do not mention this revision process inside the file.
5. Output the full revised file only.
"""

HINTS = {
    "none": "No dominant failure class was recorded. Tighten the weakest area you can see in the evidence.",
}


@dataclass
class Candidate:
    index: int
    target: str
    content: str
    path: Path | None = None
    lint_ok: bool = False
    problems: list[str] | None = None
    sha: str = ""


def mutator_from_env() -> tuple[str, str]:
    spec = os.environ.get("EVOLVRA_MUTATOR")
    if spec and ":" in spec:
        p, _, m = spec.partition(":")
        return p.strip(), m.strip()
    return DEFAULT_MUTATOR


def pick_targets(diag: Diagnosis, k: int) -> list[str]:
    targets = [fc for fc, _ in diag.failure_classes]
    generic = ["weak_evidence", "missing_acceptance_criteria_check", "vague_deliverable", "overlong_output"]
    for g in generic:
        if len(targets) >= k:
            break
        if g not in targets:
            targets.append(g)
    return targets[:k]


def propose(conn: sqlite3.Connection, persona_text: str, diag: Diagnosis, *, k: int = 3,
            mutator: tuple[str, str] | None = None, out_dir: Path | None = None, _transport=None) -> list[Candidate]:
    provider, model = mutator or mutator_from_env()
    cands: list[Candidate] = []
    for i, target in enumerate(pick_targets(diag, k), start=1):
        prompt = PROMPT.format(persona=persona_text, diagnosis=diag.to_markdown(), target=target,
                               hint=HINTS.get(target, ""))
        try:
            res = client.chat(conn, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                              provider=provider, model=model, max_tokens=6000, temperature=0.4,
                              _transport=_transport)
            content = _clean(res.text)
        except (client.ProviderError, quota.QuotaExceeded) as e:
            cands.append(Candidate(i, target, "", problems=[f"mutator error: {e}"]))
            continue
        cand = Candidate(i, target, content)
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            cand.path = out_dir / f"candidate-{i}-{re.sub(r'[^a-z0-9]+', '-', target)[:40]}.md"
            cand.path.write_text(content, encoding="utf-8")
            p = personas.load_persona(cand.path)
            cand.lint_ok, cand.problems, cand.sha = p.ok, p.problems, p.sha
        cands.append(cand)
    return cands


def _clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    if not text.startswith("---"):
        idx = text.find("\n---\n")
        if idx != -1:
            text = text[idx + 1:]
    return text.rstrip() + "\n"
