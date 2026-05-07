"""Append-only JSONL audit log of masking operations.

Records *that* a file was masked, never the masked content. If
``DRAPE_AUDIT_LOG`` is unset the writer is a no-op. All errors are swallowed
— audit logging must never crash the hook.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

ENV_AUDIT_LOG = "DRAPE_AUDIT_LOG"


def audit(event: str, **fields: Any) -> None:
    """Append one JSONL record. Silent no-op if no log path is configured."""
    log_path = os.environ.get(ENV_AUDIT_LOG)
    if not log_path:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        **fields,
    }
    try:
        path = Path(log_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except Exception as e:  # never let audit failure break the caller
        logger.debug("audit write failed: {}", e)
