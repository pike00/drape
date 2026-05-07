"""Tests for drape.patterns — credential type classification."""

from __future__ import annotations

from drape.patterns import classify_secret


def test_aws_access_key():
    assert classify_secret("AKIAIOSFODNN7EXAMPLE") == "<aws-access-key>"


def test_unknown_returns_none():
    assert classify_secret("ZqL9xD3vP8wRn1Kc6JmTbY4hUaSeWfQg") is None


def test_empty_returns_none():
    assert classify_secret("") is None


def test_jwt_three_segments():
    # Minimal-shape JWT: three base64url segments separated by dots.
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    assert classify_secret(jwt) == "<jwt>"
