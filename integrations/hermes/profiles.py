"""Read-only profile inventory using Hermes' supported profile API."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from hermes_cli import profiles as hermes_profiles


def list_profiles() -> list[dict[str, Any]]:
    result = []
    for profile in hermes_profiles.list_profiles():
        if is_dataclass(profile):
            item = asdict(profile)
        elif hasattr(profile, "__dict__"):
            item = dict(vars(profile))
        elif isinstance(profile, dict):
            item = dict(profile)
        else:
            item = {"name": str(profile)}
        for key in tuple(item):
            if "token" in key.lower() or "secret" in key.lower() or "key" in key.lower():
                item.pop(key, None)
        result.append(item)
    return result

