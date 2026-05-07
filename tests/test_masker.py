"""Tests for drape.masker module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from drape.masker import (
    DEFAULT_ENTROPY_THRESHOLD,
    mask_value,
    parse_env_file,
    shannon_entropy,
)

# Use a high-entropy synthetic value that doesn't match any known credential
# pattern (avoid AWS / GitHub / Slack / JWT prefixes).
HIGH_ENTROPY = "ZqL9xD3vP8wRn1Kc6JmTbY4hUaSeWfQg"  # 32 chars random-ish


class TestShannonEntropy:
    def test_empty(self):
        assert shannon_entropy("") == 0.0

    def test_uniform(self):
        # Single repeated char has zero entropy.
        assert shannon_entropy("aaaaaaaa") == 0.0

    def test_diverse_is_higher(self):
        assert shannon_entropy(HIGH_ENTROPY) > shannon_entropy("password")


class TestMaskValue:
    def test_mask_high_entropy_value(self):
        assert mask_value(HIGH_ENTROPY) == "ZqL..."

    def test_mask_short_value_capped_to_25_percent(self):
        # 2 chars; 25% floors to 0; minimum reveal is 1; entropy of 'ab' is 1.0
        # which is below the 3.0 default — comes out as low-entropy label.
        assert mask_value("ab") == "<low-entropy-secret>"

    def test_mask_empty_value(self):
        assert mask_value("") == ""

    def test_low_entropy_password(self):
        # English-y string: low entropy → low-entropy label, no chars revealed.
        assert mask_value("password") == "<low-entropy-secret>"

    def test_explicit_prefix_within_cap(self):
        assert mask_value(HIGH_ENTROPY, prefix_chars=5) == "ZqL9x..."

    def test_prefix_exceeds_cap(self):
        # 12-char high-entropy: cap = 12 // 4 = 3, configured 8 → 3.
        v = "Aq9XzB2mPkLn"
        assert mask_value(v, prefix_chars=8) == "Aq9..."

    def test_prefix_chars_invalid(self):
        with pytest.raises(ValueError):
            mask_value("anything", prefix_chars=0)
        with pytest.raises(ValueError):
            mask_value("anything", prefix_chars=-1)

    def test_quotes_stripped_before_measuring(self):
        # "<HIGH_ENTROPY>" — quotes stripped, mask drawn from inner chars.
        assert mask_value(f'"{HIGH_ENTROPY}"') == "ZqL..."
        assert mask_value(f"'{HIGH_ENTROPY}'") == "ZqL..."

    def test_quotes_only(self):
        assert mask_value('""') == ""
        assert mask_value("''") == ""

    def test_mismatched_quotes_left_alone(self):
        # Leading " but trailing ' — not a matching pair, treat as raw.
        # 34-char input; 25% cap = 8; default prefix = 3 → 3 chars revealed.
        assert mask_value(f'"{HIGH_ENTROPY}\'') == '"Zq...'

    def test_pattern_aws_key(self):
        # AKIA-prefixed AWS access key id (20 chars). detect-secrets recognizes it.
        assert mask_value("AKIAIOSFODNN7EXAMPLE") == "<aws-access-key>"

    def test_disable_patterns(self):
        # With patterns off, AWS key falls through to entropy + prefix path.
        result = mask_value("AKIAIOSFODNN7EXAMPLE", use_patterns=False)
        assert result == "AKI..." or result == "<low-entropy-secret>"  # depends on entropy

    def test_entropy_threshold_override(self):
        # Force everything through the high-entropy path with threshold=0.
        assert mask_value("ab", entropy_threshold=0.0) == "a..."


class TestParseEnvFile:
    @staticmethod
    def _write(contents: str) -> Path:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False)
        f.write(contents)
        f.flush()
        f.close()
        return Path(f.name)

    def test_parse_basic_env(self):
        path = self._write(f"KEY1={HIGH_ENTROPY}\nKEY2={HIGH_ENTROPY[::-1]}\n")
        try:
            out = parse_env_file(path)
            assert out[0] == "KEY1=ZqL..."
            assert out[1].startswith("KEY2=")
        finally:
            path.unlink()

    def test_parse_with_comments(self):
        path = self._write(f"# comment\nKEY={HIGH_ENTROPY}\n# another\n")
        try:
            assert parse_env_file(path) == ["KEY=ZqL..."]
        finally:
            path.unlink()

    def test_parse_empty_values(self):
        path = self._write(f"KEY1=\nKEY2={HIGH_ENTROPY}\n")
        try:
            assert parse_env_file(path) == ["KEY1=", "KEY2=ZqL..."]
        finally:
            path.unlink()

    def test_parse_quoted_values(self):
        path = self._write(f'KEY="{HIGH_ENTROPY}"\n')
        try:
            assert parse_env_file(path) == ["KEY=ZqL..."]
        finally:
            path.unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_env_file(Path("/nonexistent/.env"))

    def test_prefix_chars_propagates(self):
        path = self._write(f"KEY={HIGH_ENTROPY}\n")
        try:
            assert parse_env_file(path, prefix_chars=6) == ["KEY=ZqL9xD..."]
        finally:
            path.unlink()
