"""Fail-open adapter execution helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Evidence, EvidenceStatus


def safely(source: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        value = operation()
        if isinstance(value, Evidence):
            return value.to_dict()
        return Evidence(EvidenceStatus.AVAILABLE, source, value).to_dict()
    except TimeoutError:
        return Evidence(
            EvidenceStatus.DEGRADED, source, {}, detail="operation timed out"
        ).to_dict()
    except Exception as exc:
        return Evidence(
            EvidenceStatus.DEGRADED,
            source,
            {},
            detail=f"{type(exc).__name__}: {exc}",
        ).to_dict()

