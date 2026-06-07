"""Command-line interface for drape."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Literal, cast

from loguru import logger
from pydantic import ValidationError

from . import __version__
from .audit import audit
from .formats import detect_format, parse_structured_file
from .masker import parse_env_file
from .settings import DEFAULT_ENTROPY_THRESHOLD, DEFAULT_PREFIX_CHARS, DrapeSettings, MaskConfig
from .sops import SopsDecryptError, parse_sops_env_file

Format = Literal["auto", "env", "sops", "yaml", "json", "toml"]
ResolvedFormat = Literal["env", "sops", "yaml", "json", "toml"]


def _configure_logging(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level, format="{message}")


def _build_parser(settings: DrapeSettings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drape",
        description=(
            "Mask secrets in .env / SOPS / YAML / JSON / TOML files for safe LLM inspection"
        ),
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
        default=settings.prefix_chars,
        help=(
            f"Max leading chars to reveal (default: {DEFAULT_PREFIX_CHARS}, "
            f"or $DRAPE_PREFIX_CHARS). Always capped at 25%% of value length, min 1."
        ),
    )
    parser.add_argument(
        "--entropy-threshold",
        type=float,
        default=settings.entropy_threshold,
        help=(
            f"Shannon entropy bits/char below which values render as "
            f"<low-entropy-secret> (default: {DEFAULT_ENTROPY_THRESHOLD}, or "
            f"$DRAPE_ENTROPY_THRESHOLD)"
        ),
    )
    parser.add_argument(
        "--no-patterns",
        action="store_true",
        help="Disable pattern-based credential type labels",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> None:
    try:
        settings = DrapeSettings()
    except ValidationError as e:
        sys.stderr.write(f"drape: invalid DRAPE_* environment: {e}\n")
        sys.exit(2)
    _configure_logging(settings.log_level)

    parser = _build_parser(settings)
    args = parser.parse_args()

    filepath = Path(args.file)
    fmt = cast(
        ResolvedFormat,
        detect_format(filepath) if args.format == "auto" else args.format,
    )

    try:
        config = MaskConfig(
            prefix_chars=args.prefix_chars,
            entropy_threshold=args.entropy_threshold,
            use_patterns=not args.no_patterns,
        )
    except ValidationError as e:
        logger.error("invalid options: {}", e)
        sys.exit(2)

    try:
        lines = _dispatch(fmt, filepath, config)
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
        prefix_chars=config.prefix_chars,
    )

    for line in lines:
        print(line)


def _dispatch(fmt: ResolvedFormat, filepath: Path, config: MaskConfig) -> list[str]:
    if fmt == "env":
        return parse_env_file(filepath, config=config)
    if fmt == "sops":
        return parse_sops_env_file(filepath, config=config)
    if fmt in ("yaml", "json", "toml"):
        return parse_structured_file(filepath, fmt=fmt, config=config)
    raise ValueError(f"Unknown format: {fmt}")


if __name__ == "__main__":
    main()
