"""Tests for drape.formats — YAML/JSON/TOML key-pattern masking."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from drape.formats import detect_format, parse_structured_file

HIGH_ENTROPY = "ZqL9xD3vP8wRn1Kc6JmTbY4hUaSeWfQg"


def _write(suffix: str, content: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.flush()
    f.close()
    return Path(f.name)


def test_detect_format_env():
    assert detect_format(Path(".env")) == "env"
    assert detect_format(Path("app.env")) == "env"


def test_detect_format_sops():
    assert detect_format(Path(".env.sops")) == "sops"
    assert detect_format(Path("infra/.env.sops")) == "sops"


def test_detect_format_extensions():
    assert detect_format(Path("config.yaml")) == "yaml"
    assert detect_format(Path("config.yml")) == "yaml"
    assert detect_format(Path("config.json")) == "json"
    assert detect_format(Path("pyproject.toml")) == "toml"


def test_json_masks_secret_keys_only():
    payload = {
        "service": "api",
        "database": {"host": "db.example.com", "password": HIGH_ENTROPY},
        "client_secret": HIGH_ENTROPY,
    }
    path = _write(".json", json.dumps(payload))
    try:
        out = parse_structured_file(path, fmt="json")
        joined = "\n".join(out)
        assert "database.host=db.example.com" in joined
        assert "service=api" in joined
        # Secret keys masked.
        assert any(line.startswith("database.password=") and HIGH_ENTROPY not in line for line in out)
        assert any(line.startswith("client_secret=") and HIGH_ENTROPY not in line for line in out)
    finally:
        path.unlink()


def test_json_nested_lists():
    payload = {"users": [{"name": "alice", "token": HIGH_ENTROPY}]}
    path = _write(".json", json.dumps(payload))
    try:
        out = parse_structured_file(path, fmt="json")
        joined = "\n".join(out)
        assert "users[0].name=alice" in joined
        assert any("users[0].token=" in line and HIGH_ENTROPY not in line for line in out)
    finally:
        path.unlink()


def test_yaml_format():
    pytest.importorskip("yaml")
    content = (
        "service: api\n"
        "database:\n"
        f"  password: {HIGH_ENTROPY}\n"
        "  host: db.example.com\n"
    )
    path = _write(".yaml", content)
    try:
        out = parse_structured_file(path, fmt="yaml")
        joined = "\n".join(out)
        assert "service=api" in joined
        assert "database.host=db.example.com" in joined
        assert any(
            line.startswith("database.password=") and HIGH_ENTROPY not in line
            for line in out
        )
    finally:
        path.unlink()


def test_toml_format():
    content = (
        "service = \"api\"\n"
        "[database]\n"
        f"password = \"{HIGH_ENTROPY}\"\n"
        "host = \"db.example.com\"\n"
    )
    path = _write(".toml", content)
    try:
        out = parse_structured_file(path, fmt="toml")
        joined = "\n".join(out)
        assert "database.host=db.example.com" in joined
        assert any(
            line.startswith("database.password=") and HIGH_ENTROPY not in line
            for line in out
        )
    finally:
        path.unlink()


def test_unsupported_format_raises():
    with pytest.raises(ValueError):
        parse_structured_file(Path("/dev/null"), fmt="xml")
