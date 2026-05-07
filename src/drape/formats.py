"""Key-pattern masking for structured config formats.

Walks YAML / JSON / TOML documents and masks any leaf value whose key matches
a known-secret keyword list (``password``, ``token``, ``api_key``, ...). The
output is a flat list of ``dotted.path=masked`` lines, identical in shape to
the .env output so an LLM gets one consistent format.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .masker import (
    DEFAULT_ENTROPY_THRESHOLD,
    DEFAULT_PREFIX_CHARS,
    mask_value,
)

# Substrings that, if present in a key (case-insensitive), trigger masking of
# its value. Conservative defaults — extend via DRAPE_SECRET_KEYS env var.
DEFAULT_SECRET_KEY_PATTERNS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "private_key",
    "privatekey",
    "access_key",
    "accesskey",
    "client_secret",
    "session",
    "cookie",
    "salt",
    "signature",
)


def _key_looks_secret(key: str, patterns: Iterable[str]) -> bool:
    k = key.lower()
    return any(p in k for p in patterns)


def _walk(
    obj: Any,
    path: str,
    patterns: Iterable[str],
    prefix_chars: int,
    entropy_threshold: float,
    use_patterns: bool,
    out: list[str],
) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            sub = f"{path}.{k}" if path else str(k)
            if isinstance(v, (dict, list)):
                _walk(v, sub, patterns, prefix_chars, entropy_threshold, use_patterns, out)
            else:
                rendered = "" if v is None else str(v)
                if _key_looks_secret(str(k), patterns) and rendered:
                    rendered = mask_value(
                        rendered,
                        prefix_chars=prefix_chars,
                        entropy_threshold=entropy_threshold,
                        use_patterns=use_patterns,
                    )
                out.append(f"{sub}={rendered}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            sub = f"{path}[{i}]"
            if isinstance(v, (dict, list)):
                _walk(v, sub, patterns, prefix_chars, entropy_threshold, use_patterns, out)
            else:
                # List items inherit the parent key's secret-ness — caught by
                # the recursive frame above; here we just render as-is.
                rendered = "" if v is None else str(v)
                out.append(f"{sub}={rendered}")
    else:
        out.append(f"{path}={obj!r}")


def _load_yaml(filepath: Path) -> Any:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as e:
        raise RuntimeError("PyYAML not installed; install drape[yaml]") from e
    with open(filepath) as f:
        return yaml.safe_load(f)


def _load_json(filepath: Path) -> Any:
    with open(filepath) as f:
        return json.load(f)


def _load_toml(filepath: Path) -> Any:
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-untyped, no-redef]
        except ImportError as e:
            raise RuntimeError("tomli not installed; install drape[toml]") from e
    with open(filepath, "rb") as f:
        return tomllib.load(f)


_LOADERS = {
    "yaml": _load_yaml,
    "yml": _load_yaml,
    "json": _load_json,
    "toml": _load_toml,
}


def parse_structured_file(
    filepath: Path,
    fmt: str,
    prefix_chars: int = DEFAULT_PREFIX_CHARS,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    use_patterns: bool = True,
    secret_key_patterns: Iterable[str] = DEFAULT_SECRET_KEY_PATTERNS,
) -> list[str]:
    """Parse a YAML/JSON/TOML file and return masked dotted-path=value lines."""
    fmt = fmt.lower()
    if fmt not in _LOADERS:
        raise ValueError(f"Unsupported format: {fmt!r}. Choose from {sorted(_LOADERS)}.")
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    data = _LOADERS[fmt](filepath)
    out: list[str] = []
    _walk(
        data, "", secret_key_patterns, prefix_chars, entropy_threshold, use_patterns, out
    )
    return out


def detect_format(filepath: Path) -> str:
    """Infer format from filename. Returns ``env``, ``sops``, ``yaml``, ``json``, or ``toml``."""
    name = filepath.name.lower()
    if name.endswith(".env.sops") or name.endswith(".sops"):
        return "sops"
    if name.endswith(".json"):
        return "json"
    if name.endswith((".yaml", ".yml")):
        return "yaml"
    if name.endswith(".toml"):
        return "toml"
    # default: treat as .env
    return "env"


# Used by hook patterns matching — kept here so hook code can stay thin.
_SECRET_FILENAME_HINTS = re.compile(r"(secret|credential|password|token)", re.IGNORECASE)


def filename_suggests_secrets(filepath: Path) -> bool:
    return bool(_SECRET_FILENAME_HINTS.search(filepath.name))
