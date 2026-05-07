"""Decrypt-then-mask support for SOPS-encrypted .env files.

The decrypted plaintext only ever lives inside this process: we shell out
to ``sops -d``, capture stdout, parse it as a .env, mask every value, and
return the masked lines. The plaintext is never written to disk and never
returned to the caller.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from .masker import mask_value
from .settings import DEFAULT_ENTROPY_THRESHOLD, DEFAULT_PREFIX_CHARS, MaskConfig

SOPS_BINARY = "sops"
SOPS_TIMEOUT_SEC = 30


class SopsDecryptError(RuntimeError):
    """Raised when ``sops -d`` exits non-zero or is unavailable."""


def parse_sops_env_file(
    filepath: Path,
    prefix_chars: int = DEFAULT_PREFIX_CHARS,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    use_patterns: bool = True,
    *,
    config: Optional[MaskConfig] = None,
) -> list[str]:
    """Decrypt a SOPS-encrypted .env file in-process and return masked lines."""
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    cfg = config or MaskConfig(
        prefix_chars=prefix_chars,
        entropy_threshold=entropy_threshold,
        use_patterns=use_patterns,
    )

    try:
        proc = subprocess.run(
            [SOPS_BINARY, "-d", str(filepath)],
            capture_output=True,
            text=True,
            timeout=SOPS_TIMEOUT_SEC,
            check=False,
        )
    except FileNotFoundError as e:
        raise SopsDecryptError(
            "sops binary not found on PATH; install sops to use .env.sops support"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise SopsDecryptError(f"sops -d timed out after {SOPS_TIMEOUT_SEC}s") from e

    if proc.returncode != 0:
        # Surface stderr but never stdout (which may contain partial plaintext).
        raise SopsDecryptError(
            f"sops -d exited {proc.returncode}: {proc.stderr.strip() or 'no stderr'}"
        )

    masked: list[str] = []
    for raw in proc.stdout.splitlines():
        line = raw.rstrip("\r")
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value:
            value = mask_value(value, config=cfg)
        masked.append(f"{key}={value}")

    # Best-effort scrub of the plaintext we just had in proc.stdout.
    proc.stdout = ""  # type: ignore[misc]
    return masked
