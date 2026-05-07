"""Append-only JSONL audit log of masking operations.

Records *that* a file was masked, never the masked content. If
``DRAPE_AUDIT_LOG`` is unset the writer is a no-op. All errors are swallowed
— audit logging must never crash the hook.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from .settings import DrapeSettings


class AuditRecord(BaseModel):
    """One JSONL audit entry. ``extra="allow"`` lets callers pass arbitrary
    structured fields (file, key_count, format, ...) through to the log."""

    model_config = ConfigDict(extra="allow")

    ts: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    event: str


def audit(event: str, **fields: Any) -> None:
    """Append one JSONL record. Silent no-op if no log path is configured."""
    log_path = DrapeSettings().audit_log
    if log_path is None:
        return

    record = AuditRecord(event=event, **fields)
    try:
        path = Path(log_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(record.model_dump_json() + "\n")
    except Exception as e:  # never let audit failure break the caller
        logger.debug("audit write failed: {}", e)
