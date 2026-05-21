"""Tests for the Claude Code PreToolUse hook."""

from __future__ import annotations

import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from drape.hook import (
    _bash_targets_env,
    _basename_excluded,
    _basename_match_env,
    main as hook_main,
    should_mask,
)

HIGH_ENTROPY = "ZqL9xD3vP8wRn1Kc6JmTbY4hUaSeWfQg"


class TestPatternMatcher:
    def test_basename_match_env(self):
        assert _basename_match_env(".env")
        assert _basename_match_env("app.env")
        assert _basename_match_env(".env.sops")
        assert _basename_match_env("production.env")

    def test_basename_excluded(self):
        assert _basename_excluded(".env.example")
        assert _basename_excluded(".env.sample")
        assert _basename_excluded(".env.template")
        assert _basename_excluded(".env.json")
        assert _basename_excluded(".env.yaml")

    def test_should_mask_via_extra_pattern(self, monkeypatch):
        monkeypatch.setenv("DRAPE_HOOK_PATTERNS", "*.secrets.yaml,credentials.json")
        # Use an actual file path so should_mask treats it as a real candidate.
        f = tempfile.NamedTemporaryFile(suffix=".secrets.yaml", delete=False)
        f.close()
        try:
            assert should_mask(f.name)
        finally:
            os.unlink(f.name)


class TestBashDetection:
    def test_cat_env(self):
        assert _bash_targets_env("cat .env") == ".env"

    def test_head_env(self):
        assert _bash_targets_env("head -n 5 production.env")

    def test_grep_env(self):
        assert _bash_targets_env("grep PASSWORD .env")

    def test_rg_env(self):
        assert _bash_targets_env("rg KEY .env.sops")

    def test_awk_env(self):
        assert _bash_targets_env("awk -F= '{print $1}' .env")

    def test_unrelated_command(self):
        assert _bash_targets_env("echo hello") is None

    def test_cat_other_file(self):
        assert _bash_targets_env("cat README.md") is None

    def test_match_does_not_cross_newline(self):
        # A `cat` of a non-secret file on one line must not match a `.env.sops`
        # mentioned in an unrelated command on the next line. Regression for
        # the false positive that blocked `drape .env.sops` diagnostics.
        cmd = (
            "echo '=== run-task.sh ===' && cat -n run-task.sh\n"
            "echo '=== .env.sops keys ===' && drape .env.sops | sed 's/=.*/=<v>/'"
        )
        assert _bash_targets_env(cmd) is None

    def test_match_does_not_cross_separator(self):
        # `;` and `&&` delimit commands; a `cat` before one must not reach a
        # `.env` filename after it.
        assert _bash_targets_env("cat README.md; echo .env") is None
        assert _bash_targets_env("cat README.md && echo .env.sops") is None

    def test_real_cat_env_still_blocked_among_other_commands(self):
        # The guard must still fire when a command genuinely reads a secrets
        # file, even alongside unrelated commands.
        cmd = "cd /tmp\ncat .env.sops\necho done"
        assert _bash_targets_env(cmd) == ".env.sops"


def _run_hook(payload: dict) -> dict:
    buf = io.StringIO()
    with patch("sys.stdin", io.StringIO(json.dumps(payload))):
        with redirect_stdout(buf):
            try:
                hook_main()
            except SystemExit:
                pass
    output = buf.getvalue().strip()
    return json.loads(output) if output else {}


class TestHookDispatch:
    def test_read_env_file_returns_masked(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text(f"API_KEY={HIGH_ENTROPY}\n")
        result = _run_hook(
            {"tool_name": "Read", "tool_input": {"file_path": str(env)}}
        )
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "API_KEY=ZqL..." in reason
        assert HIGH_ENTROPY not in reason

    def test_read_non_env_passes_through(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("hello")
        result = _run_hook(
            {"tool_name": "Read", "tool_input": {"file_path": str(readme)}}
        )
        assert result == {}  # exit 0, no JSON written

    def test_bash_cat_env_blocked(self):
        result = _run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "cat .env"}}
        )
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "drape" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_bash_unrelated_passes_through(self):
        result = _run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
        )
        assert result == {}

    def test_grep_env_returns_masked_hits(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text(f"API_KEY={HIGH_ENTROPY}\nDB_HOST=db.example.com\n")
        result = _run_hook(
            {
                "tool_name": "Grep",
                "tool_input": {"pattern": "API", "path": str(env)},
            }
        )
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "API_KEY=" in reason
        assert HIGH_ENTROPY not in reason

    def test_unknown_tool_passes_through(self):
        result = _run_hook(
            {"tool_name": "Glob", "tool_input": {"pattern": "*.py"}}
        )
        assert result == {}
