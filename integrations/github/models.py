"""GitHub evidence value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryRef:
    repository_id: str
    owner: str | None
    name: str | None
    path: str

