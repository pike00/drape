"""Tests for the drape CLI entry point."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


from drape.cli import main

HIGH_ENTROPY = "ZqL9xD3vP8wRn1Kc6JmTbY4hUaSeWfQg"


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with patch.object(sys, "argv", ["drape", *argv]):
        with redirect_stdout(out), redirect_stderr(err):
            try:
                main()
            except SystemExit as e:
                code = e.code or 0
    return code, out.getvalue(), err.getvalue()


def test_cli_basic_env(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(f"API_KEY={HIGH_ENTROPY}\n")
    code, out, _ = _run([str(env)])
    assert code == 0
    assert "API_KEY=ZqL..." in out
    assert HIGH_ENTROPY not in out


def test_cli_prefix_chars_flag(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(f"K={HIGH_ENTROPY}\n")
    code, out, _ = _run(["--prefix-chars", "6", str(env)])
    assert code == 0
    assert "K=ZqL9xD..." in out


def test_cli_invalid_prefix_chars(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("K=v\n")
    code, _, _ = _run(["--prefix-chars", "0", str(env)])
    assert code == 2


def test_cli_file_not_found(tmp_path: Path):
    code, _, _ = _run([str(tmp_path / "missing.env")])
    assert code == 1


def test_cli_format_json(tmp_path: Path):
    j = tmp_path / "config.json"
    j.write_text(json.dumps({"service": "api", "password": HIGH_ENTROPY}))
    code, out, _ = _run([str(j)])
    assert code == 0
    assert "service=api" in out
    assert HIGH_ENTROPY not in out


def test_cli_no_patterns(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE\n")
    code, out, _ = _run(["--no-patterns", str(env)])
    assert code == 0
    # With patterns off, we should NOT see the <aws-access-key> label.
    assert "<aws-access-key>" not in out


def test_cli_audit_log_writes(tmp_path: Path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(f"K={HIGH_ENTROPY}\n")
    audit_log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("DRAPE_AUDIT_LOG", str(audit_log))
    code, _, _ = _run([str(env)])
    assert code == 0
    lines = audit_log.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["event"] == "cli_mask"
    assert rec["format"] == "env"
    assert rec["key_count"] == 1
