"""Tests for drape.audit — JSONL append-only logging."""

from __future__ import annotations

import json
from pathlib import Path

from drape.audit import audit


def test_no_op_when_env_unset(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("DRAPE_AUDIT_LOG", raising=False)
    audit("test_event", file="x")  # should not raise, should not create anything
    assert list(tmp_path.iterdir()) == []


def test_writes_jsonl(monkeypatch, tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("DRAPE_AUDIT_LOG", str(log))
    audit("hook_mask", file=".env", key_count=3)
    audit("hook_mask", file="prod.env", key_count=5)

    lines = log.read_text().splitlines()
    assert len(lines) == 2
    rec1 = json.loads(lines[0])
    assert rec1["event"] == "hook_mask"
    assert rec1["file"] == ".env"
    assert rec1["key_count"] == 3
    assert "ts" in rec1


def test_failure_swallowed(monkeypatch):
    # Pointing at an unwritable path must not raise.
    monkeypatch.setenv("DRAPE_AUDIT_LOG", "/proc/this/cannot/be/written")
    audit("test")  # no exception
