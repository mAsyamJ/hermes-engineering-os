"""Stamp canonical Kanban identity onto OTel resource attributes.

Hermes workers already receive HERMES_KANBAN_* in their environment.
hermes-otel does not read those variables. Engineering OS registers
before hermes_otel (directory order) and merges explicit env values
into OTEL_RESOURCE_ATTRIBUTES so Resource.create() attaches them to
every span in that process.

Never infers identity from similar strings. Never blocks. Never
mutates Kanban.
"""

from __future__ import annotations

import os
from typing import MutableMapping

ENV_TO_ATTR = (
    ("HERMES_KANBAN_TASK", "hermes.kanban.task_id"),
    ("HERMES_KANBAN_RUN_ID", "hermes.kanban.run_id"),
    ("HERMES_KANBAN_BOARD", "hermes.kanban.board"),
    ("HERMES_KANBAN_WORKSPACE", "hermes.kanban.workspace"),
)


def _parse(existing: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in existing.split(","):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        if key:
            result[key] = value
    return result


def apply_kanban_resource_attributes(
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    env: MutableMapping[str, str] = os.environ if environ is None else environ
    current = _parse(env.get("OTEL_RESOURCE_ATTRIBUTES", ""))
    stamped: dict[str, str] = {}
    try:
        for env_name, attr in ENV_TO_ATTR:
            raw = str(env.get(env_name, "")).strip()
            if not raw:
                continue
            if attr in current:
                stamped[attr] = current[attr]
                continue
            current[attr] = raw
            stamped[attr] = raw
        if stamped:
            env["OTEL_RESOURCE_ATTRIBUTES"] = ",".join(
                f"{key}={value}" for key, value in current.items()
            )
    except Exception:
        return {}
    return stamped


def expected_plugin_load_order() -> tuple[str, str]:
    return ("engineering-os", "hermes_otel")
