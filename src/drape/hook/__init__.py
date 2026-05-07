"""Claude Code PreToolUse hook.

Intercepts:
  - Read on .env / .env.sops / configured structured-secret files
  - Grep on those same files (we re-grep against the masked rendering)
  - Bash commands that try to ``cat`` / ``head`` / ``tail`` / ``less`` / ``grep``
    a .env file directly — denied with a redirect to ``drape``.

All decisions return JSON to stdout. Any error path falls through with exit 0
so a buggy hook never blocks Claude from working.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ..audit import audit
from ..formats import detect_format, parse_structured_file
from ..masker import DEFAULT_ENTROPY_THRESHOLD, DEFAULT_PREFIX_CHARS, parse_env_file
from ..sops import SopsDecryptError, parse_sops_env_file

logger.remove()  # hook context: stay silent — never write to stderr from inside Claude

ENV_PREFIX_CHARS = "DRAPE_PREFIX_CHARS"
ENV_ENTROPY_THRESHOLD = "DRAPE_ENTROPY_THRESHOLD"
ENV_HOOK_PATTERNS = "DRAPE_HOOK_PATTERNS"  # extra glob patterns, comma-separated


def _prefix_chars() -> int:
    raw = os.environ.get(ENV_PREFIX_CHARS)
    if raw is None:
        return DEFAULT_PREFIX_CHARS
    try:
        v = int(raw)
    except ValueError:
        return DEFAULT_PREFIX_CHARS
    return v if v >= 1 else DEFAULT_PREFIX_CHARS


def _entropy_threshold() -> float:
    raw = os.environ.get(ENV_ENTROPY_THRESHOLD)
    if raw is None:
        return DEFAULT_ENTROPY_THRESHOLD
    try:
        v = float(raw)
    except ValueError:
        return DEFAULT_ENTROPY_THRESHOLD
    return v if v >= 0.0 else DEFAULT_ENTROPY_THRESHOLD


def _extra_patterns() -> list[str]:
    raw = os.environ.get(ENV_HOOK_PATTERNS, "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _basename_match_env(basename: str) -> bool:
    """True if ``basename`` looks like a .env file we should mask."""
    b = basename.lower()
    if b == ".env":
        return True
    if b.endswith(".env"):
        return True
    if b.endswith(".env.sops") or b == ".env.sops":
        return True
    return False


def _basename_excluded(basename: str) -> bool:
    """``.env.example`` / ``.env.json`` / ``.env.yaml`` are not secret payloads."""
    b = basename.lower()
    excluded_suffixes = (".example", ".sample", ".template")
    if any(b.endswith(f".env{s}") for s in excluded_suffixes):
        return True
    # .env.json / .env.yaml etc. — handled by their own format if requested
    return b.endswith((".env.json", ".env.yaml", ".env.yml", ".env.toml"))


def should_mask(filepath: str) -> bool:
    """Whether this hook should intercept reads of ``filepath``."""
    p = Path(filepath)
    basename = p.name
    if _basename_excluded(basename):
        return False
    if _basename_match_env(basename):
        return True
    # User-provided extra glob patterns (e.g. "*.secrets.yaml,credentials.json")
    for pattern in _extra_patterns():
        if p.match(pattern):
            return True
    return False


def _mask_file(filepath: Path) -> Optional[str]:
    """Return masked rendering or None on any error."""
    fmt = detect_format(filepath)
    pc = _prefix_chars()
    et = _entropy_threshold()
    try:
        if fmt == "sops":
            lines = parse_sops_env_file(
                filepath, prefix_chars=pc, entropy_threshold=et, use_patterns=True
            )
        elif fmt in ("yaml", "json", "toml"):
            lines = parse_structured_file(
                filepath, fmt=fmt, prefix_chars=pc, entropy_threshold=et, use_patterns=True
            )
        else:
            lines = parse_env_file(
                filepath, prefix_chars=pc, entropy_threshold=et, use_patterns=True
            )
    except (FileNotFoundError, SopsDecryptError, Exception):
        return None

    audit(
        "hook_mask",
        tool=os.environ.get("_DRAPE_HOOK_TOOL", "Read"),
        file=str(filepath),
        format=fmt,
        key_count=len(lines),
        prefix_chars=pc,
    )
    return "\n".join(lines)


# --- Bash command detection ---------------------------------------------------

# Match commands that read a .env file directly. Crude but effective.
_BASH_DIRECT_READ = re.compile(
    r"\b(cat|bat|head|tail|less|more|nl|tac)\b[^|;&]*?(\.env(?:\.sops)?(?:\.[a-z]+)?)\b",
    re.IGNORECASE,
)
_BASH_GREP_LIKE = re.compile(
    r"\b(grep|rg|ag|ack|sed|awk|cut|column)\b[^|;&]*?(\.env(?:\.sops)?(?:\.[a-z]+)?)\b",
    re.IGNORECASE,
)


def _bash_targets_env(command: str) -> Optional[str]:
    for rx in (_BASH_DIRECT_READ, _BASH_GREP_LIKE):
        m = rx.search(command)
        if m:
            return m.group(2)
    return None


# --- Tool dispatch ------------------------------------------------------------


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _handle_read(tool_input: dict[str, Any]) -> Optional[dict[str, Any]]:
    filepath = tool_input.get("file_path", "")
    if not filepath or not should_mask(filepath) or not os.path.isfile(filepath):
        return None
    masked = _mask_file(Path(filepath))
    if masked is None:
        return None
    return _deny(
        f"drape: secrets masked for LLM safety.\n\n"
        f"# {filepath} (masked by drape)\n{masked}"
    )


def _handle_grep(tool_input: dict[str, Any]) -> Optional[dict[str, Any]]:
    # Grep tool inputs vary by version; check both `path` and `paths`.
    targets: list[str] = []
    for k in ("path", "paths"):
        v = tool_input.get(k)
        if isinstance(v, str):
            targets.append(v)
        elif isinstance(v, list):
            targets.extend(t for t in v if isinstance(t, str))

    sensitive = [t for t in targets if should_mask(t) and os.path.isfile(t)]
    if not sensitive:
        return None

    pattern = tool_input.get("pattern", "")
    try:
        rx = re.compile(pattern) if pattern else None
    except re.error:
        rx = None

    rendered: list[str] = []
    for path in sensitive:
        masked = _mask_file(Path(path))
        if masked is None:
            continue
        if rx is None:
            rendered.append(f"# {path} (masked by drape)\n{masked}")
        else:
            hits = [line for line in masked.splitlines() if rx.search(line)]
            rendered.append(
                f"# {path} (masked by drape, grepped for {pattern!r})\n"
                + ("\n".join(hits) if hits else "(no matches in masked content)")
            )

    if not rendered:
        return None
    return _deny(
        "drape: Grep on a secrets file is masked.\n\n" + "\n\n".join(rendered)
    )


def _handle_bash(tool_input: dict[str, Any]) -> Optional[dict[str, Any]]:
    cmd = tool_input.get("command", "")
    if not isinstance(cmd, str) or not cmd:
        return None
    target = _bash_targets_env(cmd)
    if target is None:
        return None
    audit("hook_bash_block", file=target, command=cmd[:200])
    return _deny(
        f"drape: this command would expose raw secrets from {target!r}. "
        f"Use `drape {target}` (or `drape --format auto {target}`) instead — "
        f"it returns the same content with values masked."
    )


_DISPATCH = {
    "Read": _handle_read,
    "Grep": _handle_grep,
    "Bash": _handle_bash,
}


def main() -> None:
    try:
        payload: dict[str, Any] = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    handler = _DISPATCH.get(tool_name)
    if handler is None:
        sys.exit(0)

    os.environ["_DRAPE_HOOK_TOOL"] = tool_name
    try:
        response = handler(tool_input)
    except Exception:
        sys.exit(0)
    if response is None:
        sys.exit(0)
    json.dump(response, sys.stdout)


if __name__ == "__main__":
    main()
