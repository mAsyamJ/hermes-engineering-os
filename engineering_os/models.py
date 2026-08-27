"""Typed evidence envelopes shared by all adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class EvidenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    BLOCKED_AUTH = "BLOCKED_AUTH"


@dataclass(frozen=True)
class Evidence(Generic[T]):
    status: EvidenceStatus
    source: str
    data: T
    observed_at: int = field(default_factory=lambda: int(time.time()))
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

