"""Core masking logic for .env files.

The mask is the smallest of:
  - the configured prefix length
  - 25% of the (de-quoted) value length, floor
With a hard floor of 1 char so empty masks never happen for non-empty values.

Before computing the mask we strip a single layer of matching surrounding
quotes (`"..."` or `'...'`) so `KEY="abcd"` reveals chars from `abcd`, not
from `"abcd"`.

After length+entropy logic, if a known-credential pattern matches we replace
the value with a `<credential-type>` label (via :mod:`drape.patterns`).
This leaks strictly less than the prefix-reveal: just the type, no chars.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from loguru import logger

from .patterns import classify_secret

DEFAULT_PREFIX_CHARS = 3
# Shannon entropy threshold (bits/char). Below this, the value is more like
# English text or a structured identifier than a random secret — revealing a
# prefix would leak meaningful information. Random base64 ~= 6.0, hex ~= 4.0,
# English ~= 2-3, common passwords ~= 1.5-2.5.
DEFAULT_ENTROPY_THRESHOLD = 3.0


def shannon_entropy(value: str) -> float:
    """Shannon entropy in bits/char. 0.0 for empty input."""
    if not value:
        return 0.0
    counts = Counter(value)
    n = len(value)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _strip_quotes(value: str) -> str:
    """Remove a single matching pair of surrounding ASCII quotes."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def mask_value(
    value: str,
    prefix_chars: int = DEFAULT_PREFIX_CHARS,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    use_patterns: bool = True,
) -> str:
    """Mask a secret value.

    Resolution order:
      1. Empty value → empty mask.
      2. Strip surrounding quotes.
      3. Pattern match (AWS, GitHub, Slack, Stripe, ...) → ``<credential-type>``.
      4. Low-entropy value → ``<low-entropy-secret>`` (no chars revealed).
      5. Otherwise reveal ``min(prefix_chars, max(1, len // 4))`` chars + ``...``.
    """
    if not value:
        return ""
    if prefix_chars < 1:
        raise ValueError(f"prefix_chars must be >= 1, got {prefix_chars}")

    inner = _strip_quotes(value)
    if not inner:
        return ""

    if use_patterns:
        label = classify_secret(inner)
        if label is not None:
            return label

    if shannon_entropy(inner) < entropy_threshold:
        return "<low-entropy-secret>"

    max_visible = max(1, len(inner) // 4)
    visible = min(prefix_chars, max_visible)
    return inner[:visible] + "..."


def parse_env_file(
    filepath: Path,
    prefix_chars: int = DEFAULT_PREFIX_CHARS,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    use_patterns: bool = True,
) -> list[str]:
    """Parse a .env file and return masked KEY=VALUE lines.

    Skips empty lines and comments. Splits on the first ``=`` only so values
    with embedded equals signs survive. Whitespace around key and value is
    stripped. Each value is run through :func:`mask_value`.
    """
    if not filepath.exists():
        logger.error("File not found: {}", filepath)
        raise FileNotFoundError(f"File not found: {filepath}")

    logger.debug("Parsing .env file: {}", filepath)
    lines: list[str] = []
    skipped = 0
    with open(filepath) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                skipped += 1
                continue
            if "=" not in line:
                skipped += 1
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if value:
                masked = mask_value(
                    value,
                    prefix_chars=prefix_chars,
                    entropy_threshold=entropy_threshold,
                    use_patterns=use_patterns,
                )
            else:
                masked = ""
            lines.append(f"{key}={masked}")

    logger.debug(
        "Parsed {} masked entries (skipped {}) from {}", len(lines), skipped, filepath
    )
    return lines
