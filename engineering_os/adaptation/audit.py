"""Append-only audit helpers. No secrets."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from engineering_os.redaction import redact


def event(
    action: str,
    *,
    actor_class: str,
    actor_identity: str,
    object_type: str,
    object_id: str | None = None,
    previous_state_hash: str | None = None,
    new_state_hash: str | None = None,
    reason: str | None = None,
    source_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return redact(
        {
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "actor_class": actor_class,
            "actor_identity": actor_identity,
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "previous_state_hash": previous_state_hash,
            "new_state_hash": new_state_hash,
            "reason": reason,
            "source_evidence": source_evidence or {},
        }
    )
