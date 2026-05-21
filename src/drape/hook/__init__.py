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
from typing import Callable, Literal, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..audit import audit
from ..formats import detect_format, parse_structured_file
from ..masker import parse_env_file
from ..settings import DrapeSettings, MaskConfig
from ..sops import SopsDecryptError, parse_sops_env_file

logger.remove()  # hook context: stay silent — never write to stderr from inside Claude


# --- Pydantic models for hook payload ----------------------------------------


class _ToolInput(BaseModel):
    """Base for tool inputs. ``extra="allow"`` so we don't reject fields the
    Claude tool layer adds in newer versions."""

    model_config = ConfigDict(extra="allow")


class ReadToolInput(_ToolInput):
    file_path: str = ""


class BashToolInput(_ToolInput):
    command: str = ""


class GrepToolInput(_ToolInput):
    pattern: str = ""
    path: Optional[str] = None
    paths: Optional[list[str]] = None

    def all_paths(self) -> list[str]:
        out: list[str] = []
        if self.path:
            out.append(self.path)
        if self.paths:
            out.extend(p for p in self.paths if isinstance(p, str))
        return out


class HookPayload(BaseModel):
    """Top-level Claude PreToolUse payload. Tool input stays as raw dict
    here so each handler can re-validate against its own typed model."""

    model_config = ConfigDict(extra="allow")

    tool_name: str = ""
    tool_input: dict = Field(default_factory=dict)


class HookSpecificOutput(BaseModel):
    hookEventName: Literal["PreToolUse"] = "PreToolUse"
    permissionDecision: Literal["deny", "allow", "ask"]
    permissionDecisionReason: str


class HookResponse(BaseModel):
    hookSpecificOutput: HookSpecificOutput


# --- Filename / pattern matching ---------------------------------------------


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
    return b.endswith((".env.json", ".env.yaml", ".env.yml", ".env.toml"))


def should_mask(filepath: str) -> bool:
    """Whether this hook should intercept reads of ``filepath``."""
    p = Path(filepath)
    basename = p.name
    if _basename_excluded(basename):
        return False
    if _basename_match_env(basename):
        return True
    for pattern in DrapeSettings().hook_patterns:
        if p.match(pattern):
            return True
    return False


# --- Bash command detection ---------------------------------------------------

# The gap between the command name and the .env filename must not cross a
# command boundary, or we get false positives like `cat run-task.sh` on one
# line matching a `.env.sops` mentioned in an `echo` string on the next line.
# `|`, `;`, `&` (covering `&&`/`||`) and newlines all delimit commands, so the
# gap class excludes every one of them.
_BASH_DIRECT_READ = re.compile(
    r"\b(cat|bat|head|tail|less|more|nl|tac)\b[^|;&\r\n]*?(\.env(?:\.sops)?(?:\.[a-z]+)?)\b",
    re.IGNORECASE,
)
_BASH_GREP_LIKE = re.compile(
    r"\b(grep|rg|ag|ack|sed|awk|cut|column)\b[^|;&\r\n]*?(\.env(?:\.sops)?(?:\.[a-z]+)?)\b",
    re.IGNORECASE,
)


def _bash_targets_env(command: str) -> Optional[str]:
    for rx in (_BASH_DIRECT_READ, _BASH_GREP_LIKE):
        m = rx.search(command)
        if m:
            return m.group(2)
    return None


# --- Mask dispatch ------------------------------------------------------------


def _mask_file(filepath: Path, config: MaskConfig, tool_name: str) -> Optional[str]:
    """Return masked rendering or None on any error."""
    fmt = detect_format(filepath)
    try:
        if fmt == "sops":
            lines = parse_sops_env_file(filepath, config=config)
        elif fmt in ("yaml", "json", "toml"):
            lines = parse_structured_file(filepath, fmt=fmt, config=config)
        else:
            lines = parse_env_file(filepath, config=config)
    except (FileNotFoundError, SopsDecryptError, Exception):
        return None

    audit(
        "hook_mask",
        tool=tool_name,
        file=str(filepath),
        format=fmt,
        key_count=len(lines),
        prefix_chars=config.prefix_chars,
    )
    return "\n".join(lines)


def _deny(reason: str) -> HookResponse:
    return HookResponse(
        hookSpecificOutput=HookSpecificOutput(
            permissionDecision="deny",
            permissionDecisionReason=reason,
        )
    )


# --- Per-tool handlers --------------------------------------------------------


def _handle_read(
    tool_input: dict, config: MaskConfig, tool_name: str
) -> Optional[HookResponse]:
    parsed = ReadToolInput.model_validate(tool_input)
    filepath = parsed.file_path
    if not filepath or not should_mask(filepath) or not os.path.isfile(filepath):
        return None
    masked = _mask_file(Path(filepath), config, tool_name)
    if masked is None:
        return None
    return _deny(
        f"drape: secrets masked for LLM safety.\n\n"
        f"# {filepath} (masked by drape)\n{masked}"
    )


def _handle_grep(
    tool_input: dict, config: MaskConfig, tool_name: str
) -> Optional[HookResponse]:
    parsed = GrepToolInput.model_validate(tool_input)
    sensitive = [t for t in parsed.all_paths() if should_mask(t) and os.path.isfile(t)]
    if not sensitive:
        return None

    try:
        rx = re.compile(parsed.pattern) if parsed.pattern else None
    except re.error:
        rx = None

    rendered: list[str] = []
    for path in sensitive:
        masked = _mask_file(Path(path), config, tool_name)
        if masked is None:
            continue
        if rx is None:
            rendered.append(f"# {path} (masked by drape)\n{masked}")
        else:
            hits = [line for line in masked.splitlines() if rx.search(line)]
            rendered.append(
                f"# {path} (masked by drape, grepped for {parsed.pattern!r})\n"
                + ("\n".join(hits) if hits else "(no matches in masked content)")
            )

    if not rendered:
        return None
    return _deny(
        "drape: Grep on a secrets file is masked.\n\n" + "\n\n".join(rendered)
    )


def _handle_bash(
    tool_input: dict, config: MaskConfig, tool_name: str
) -> Optional[HookResponse]:
    parsed = BashToolInput.model_validate(tool_input)
    if not parsed.command:
        return None
    target = _bash_targets_env(parsed.command)
    if target is None:
        return None
    audit("hook_bash_block", file=target, command=parsed.command[:200])
    return _deny(
        f"drape: this command would expose raw secrets from {target!r}. "
        f"Use `drape {target}` (or `drape --format auto {target}`) instead — "
        f"it returns the same content with values masked."
    )


_Handler = Callable[[dict, MaskConfig, str], Optional[HookResponse]]
_DISPATCH: dict[str, _Handler] = {
    "Read": _handle_read,
    "Grep": _handle_grep,
    "Bash": _handle_bash,
}


def main() -> None:
    try:
        raw = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    try:
        payload = HookPayload.model_validate(raw)
    except ValidationError:
        sys.exit(0)

    handler = _DISPATCH.get(payload.tool_name)
    if handler is None:
        sys.exit(0)

    try:
        config = DrapeSettings().mask_config()
    except ValidationError:
        sys.exit(0)

    try:
        response = handler(payload.tool_input, config, payload.tool_name)
    except Exception:
        sys.exit(0)
    if response is None:
        sys.exit(0)
    sys.stdout.write(response.model_dump_json())


if __name__ == "__main__":
    main()
