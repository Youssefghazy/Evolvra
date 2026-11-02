"""Shared fixtures: run the plugin's recorder script against a temp EVOLVRA_HOME."""
import importlib.util
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RECORDER = REPO / "plugin" / "scripts" / "mission.py"
HOOK = REPO / "plugin" / "hooks" / "log_event.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def evolvra_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("EVOLVRA_HOME", str(home))
    return home


@pytest.fixture
def recorder(evolvra_home):
    mod = _load(RECORDER, "evolvra_recorder")

    def run(*argv) -> int:
        return mod.main([str(a) for a in argv])

    run.module = mod
    return run


@pytest.fixture
def hook(evolvra_home):
    mod = _load(HOOK, "evolvra_hook")

    def fire(payload: dict) -> None:
        import io
        import json
        import sys

        old = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            assert mod.main() == 0
        finally:
            sys.stdin = old

    return fire


def mission_id(evolvra_home: Path) -> str:
    dirs = sorted((evolvra_home / "missions").iterdir())
    assert dirs, "no mission recorded"
    return dirs[-1].name


__all__ = ["mission_id", "os"]
