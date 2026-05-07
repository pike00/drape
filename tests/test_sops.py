"""Tests for drape.sops — decrypt-then-mask path."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from drape.sops import SopsDecryptError, parse_sops_env_file

HIGH_ENTROPY = "ZqL9xD3vP8wRn1Kc6JmTbY4hUaSeWfQg"


def _fake_run(stdout: str = "", returncode: int = 0, stderr: str = ""):
    def _impl(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], returncode, stdout=stdout, stderr=stderr)

    return _impl


def test_parse_sops_env_file_success(tmp_path: Path):
    encrypted = tmp_path / ".env.sops"
    encrypted.write_text("(encrypted blob)\n")

    fake_plaintext = f"API_KEY={HIGH_ENTROPY}\nDB_HOST=db.example.com\n# comment\n"
    with patch("drape.sops.subprocess.run", side_effect=_fake_run(stdout=fake_plaintext)):
        out = parse_sops_env_file(encrypted)

    # parse_sops_env_file masks every value (a .env contract — all values are
    # presumed sensitive). DB_HOST is high-entropy enough to take the prefix
    # path; assert it's masked rather than copy-pasting the exact prefix.
    assert out[0] == "API_KEY=ZqL..."
    assert out[1].startswith("DB_HOST=") and "db.example.com" not in out[1]
    # Plaintext must not appear anywhere in the masked rendering.
    joined = "\n".join(out)
    assert HIGH_ENTROPY not in joined


def test_sops_nonzero_exit_raises(tmp_path: Path):
    encrypted = tmp_path / ".env.sops"
    encrypted.write_text("(encrypted blob)\n")
    with patch(
        "drape.sops.subprocess.run",
        side_effect=_fake_run(returncode=1, stderr="no decryption keys"),
    ):
        with pytest.raises(SopsDecryptError, match="no decryption keys"):
            parse_sops_env_file(encrypted)


def test_sops_binary_missing(tmp_path: Path):
    encrypted = tmp_path / ".env.sops"
    encrypted.write_text("(encrypted blob)\n")
    with patch("drape.sops.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SopsDecryptError, match="sops binary not found"):
            parse_sops_env_file(encrypted)


def test_sops_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        parse_sops_env_file(tmp_path / "does-not-exist.env.sops")
