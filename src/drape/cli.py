"""Command-line interface for drape."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from loguru import logger

from . import __version__
from .audit import audit
from .formats import detect_format, parse_structured_file
from .masker import DEFAULT_ENTROPY_THRESHOLD, DEFAULT_PREFIX_CHARS, parse_env_file
from .sops import SopsDecryptError, parse_sops_env_file

ENV_PREFIX_CHARS = "DRAPE_PREFIX_CHARS"
ENV_ENTROPY_THRESHOLD = "DRAPE_ENTROPY_THRESHOLD"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        v = int(raw)
    except ValueError:
        logger.warning("{}={!r} is not an integer; using {}", name, raw, default)
        return default
    return v if v >= 1 else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        v = float(raw)
    except ValueError:
        logger.warning("{}={!r} is not a float; using {}", name, raw, default)
        return default
    return v if v >= 0.0 else default


def _configure_logging() -> None:
    level = os.environ.get("DRAPE_LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(sys.stderr, level=level, format="{message}")


def main() -> None:
    _configure_logging()

    parser = argparse.ArgumentParser(
        prog="drape",
        description="Mask secrets in .env / SOPS / YAML / JSON / TOML files for safe LLM inspection",
    )
    parser.add_argument("file", nargs="?", default=".env", help="Path to file (default: .env)")
    parser.add_argument(
        "--format",
        choices=("auto", "env", "sops", "yaml", "json", "toml"),
        default="auto",
        help="Input format (default: auto-detect by filename)",
    )
    parser.add_argument(
        "--prefix-chars",
        type=int,
        default=_env_int(ENV_PREFIX_CHARS, DEFAULT_PREFIX_CHARS),
        help=(
            f"Max leading chars to reveal (default: {DEFAULT_PREFIX_CHARS}, "
            f"or ${ENV_PREFIX_CHARS}). Always capped at 25%% of value length, min 1."
        ),
    )
    parser.add_argument(
        "--entropy-threshold",
        type=float,
        default=_env_float(ENV_ENTROPY_THRESHOLD, DEFAULT_ENTROPY_THRESHOLD),
        help=(
            f"Shannon entropy bits/char below which values render as "
            f"<low-entropy-secret> (default: {DEFAULT_ENTROPY_THRESHOLD}, or ${ENV_ENTROPY_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--no-patterns",
        action="store_true",
        help="Disable pattern-based credential type labels",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()
    filepath = Path(args.file)
    fmt = detect_format(filepath) if args.format == "auto" else args.format

    if args.prefix_chars < 1:
        logger.error("--prefix-chars must be >= 1, got {}", args.prefix_chars)
        sys.exit(2)

    try:
        lines = _dispatch(fmt, filepath, args)
    except FileNotFoundError as e:
        logger.error("{}", e)
        sys.exit(1)
    except SopsDecryptError as e:
        logger.error("sops: {}", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: {}", e)
        sys.exit(1)

    audit(
        "cli_mask",
        file=str(filepath),
        format=fmt,
        key_count=len(lines),
        prefix_chars=args.prefix_chars,
    )

    for line in lines:
        print(line)


def _dispatch(fmt: str, filepath: Path, args: argparse.Namespace) -> list[str]:
    use_patterns = not args.no_patterns
    common = dict(
        prefix_chars=args.prefix_chars,
        entropy_threshold=args.entropy_threshold,
        use_patterns=use_patterns,
    )
    if fmt == "env":
        return parse_env_file(filepath, **common)
    if fmt == "sops":
        return parse_sops_env_file(filepath, **common)
    if fmt in ("yaml", "json", "toml"):
        return parse_structured_file(filepath, fmt=fmt, **common)
    raise ValueError(f"Unknown format: {fmt}")


if __name__ == "__main__":
    main()
