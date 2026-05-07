"""Typed configuration surface for drape.

Two models live here:

* :class:`MaskConfig` — per-call masking parameters (prefix length, entropy
  threshold, pattern toggle). Frozen so it can be passed around as an
  immutable value object.
* :class:`DrapeSettings` — process-wide environment-variable configuration.
  Read once at startup; every ``DRAPE_*`` env var is parsed and validated
  here, not scattered across the CLI / hook entrypoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated

DEFAULT_PREFIX_CHARS: int = 3
# Shannon entropy threshold (bits/char). Below this, the value is more like
# English text or a structured identifier than a random secret — revealing a
# prefix would leak meaningful information. Random base64 ~= 6.0, hex ~= 4.0,
# English ~= 2-3, common passwords ~= 1.5-2.5.
DEFAULT_ENTROPY_THRESHOLD: float = 3.0


class MaskConfig(BaseModel):
    """Per-call masking parameters.

    ``prefix_chars`` is the maximum number of leading characters of a value
    we are ever willing to reveal; the actual reveal is further capped at
    25% of value length. ``entropy_threshold`` is the bits-per-char floor
    below which a value renders as ``<low-entropy-secret>``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    prefix_chars: int = Field(default=DEFAULT_PREFIX_CHARS, ge=1)
    entropy_threshold: float = Field(default=DEFAULT_ENTROPY_THRESHOLD, ge=0.0)
    use_patterns: bool = True


class DrapeSettings(BaseSettings):
    """Process-wide drape configuration sourced from ``DRAPE_*`` env vars.

    Construct fresh whenever the current environment matters
    (``DrapeSettings()``); pydantic-settings reads ``os.environ`` at
    instantiation, so per-test ``monkeypatch.setenv`` works as expected.
    """

    model_config = SettingsConfigDict(
        env_prefix="DRAPE_",
        extra="ignore",
        case_sensitive=False,
    )

    prefix_chars: int = Field(default=DEFAULT_PREFIX_CHARS, ge=1)
    entropy_threshold: float = Field(default=DEFAULT_ENTROPY_THRESHOLD, ge=0.0)
    use_patterns: bool = True
    log_level: str = "INFO"
    audit_log: Optional[Path] = None
    # ``NoDecode`` keeps pydantic-settings from JSON-parsing the env var; we
    # split on commas via the validator below so callers can write
    # ``DRAPE_HOOK_PATTERNS="*.secrets.yaml,credentials.json"``.
    hook_patterns: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("hook_patterns", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("log_level", mode="after")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    def mask_config(self) -> MaskConfig:
        """Project the env-derived defaults onto a :class:`MaskConfig`."""
        return MaskConfig(
            prefix_chars=self.prefix_chars,
            entropy_threshold=self.entropy_threshold,
            use_patterns=self.use_patterns,
        )
