"""HARD / SOFT / UNAVAILABLE classification for real-model experiment budgets.

Honesty rules (live Hermes c0106e50):
- `-Q` / `-q` do not cap tool-loop turns (default agent.max_turns is 500).
- CLI `--max-turns` is first in the AIAgent constructor priority chain.
- `HERMES_MAX_ITERATIONS` is only consulted if config does not already set
  agent.max_turns; CLI_CONFIG defaults include max_turns=500, so env-alone
  is not a hard cap on this SHA.
- Subprocess timeout is an OS process deadline (HARD per unit).
- Provider HTTP retries and token/dollar totals are not intercepted.
"""

from __future__ import annotations

from typing import Any

HARD = "HARD_ENFORCED"
SOFT = "SOFT_MONITORED"
UNAVAILABLE = "UNAVAILABLE"


def planned_turns(protocol: dict[str, Any]) -> int:
    return int((protocol.get("budget") or {}).get("planned_max_turns_per_unit") or 0)


def per_unit_wall_seconds(protocol: dict[str, Any]) -> int:
    budget = protocol.get("budget") or {}
    per_unit = int(budget.get("max_wall_seconds_per_unit") or 0)
    if per_unit > 0:
        return per_unit
    return int(budget.get("max_wall_seconds") or 7200)


def total_wall_seconds(protocol: dict[str, Any]) -> int:
    return int((protocol.get("budget") or {}).get("max_wall_seconds") or 0)


def classify_budget(protocol: dict[str, Any]) -> dict[str, Any]:
    budget = protocol.get("budget") or {}
    turns = planned_turns(protocol)
    units = int(budget.get("planned_max_units") or 0)
    calls = int(budget.get("planned_max_llm_calls") or 0)
    hard: list[dict[str, Any]] = [
        {
            "id": "max_units",
            "value": units,
            "enforcement": HARD,
            "how": "sequential runner will not start unit n+1",
        },
        {
            "id": "max_hermes_invocations",
            "value": calls,
            "enforcement": HARD,
            "how": "sequential runner will not spawn process n+1",
        },
        {
            "id": "max_wall_seconds_per_unit",
            "value": per_unit_wall_seconds(protocol),
            "enforcement": HARD,
            "how": "subprocess.run timeout on that Hermes process",
        },
        {
            "id": "max_wall_seconds_total",
            "value": total_wall_seconds(protocol),
            "enforcement": HARD,
            "how": "runner stop before starting the next unit",
        },
        {
            "id": "protocol_binding",
            "value": {
                "protocol_id": protocol.get("experiment_id"),
                "protocol_hash": protocol.get("_definition_hash"),
                "control": (protocol.get("control") or {}).get("model"),
                "candidate": (protocol.get("candidate") or {}).get("model"),
                "scope": protocol.get("scope"),
            },
            "enforcement": HARD,
            "how": "LLM_BUDGET_AUTHORIZATION must bind these fields; mismatch rejects",
        },
    ]
    if turns > 0:
        hard.append(
            {
                "id": "max_turns_per_unit",
                "value": turns,
                "enforcement": HARD,
                "how": (
                    "isolated argv includes --max-turns (CLI arg beats config/env); "
                    "isolated config.yaml agent.max_turns written to the same N; "
                    "delegation toolset disabled so subagent budgets cannot exceed the parent cap; "
                    "HERMES_MAX_ITERATIONS set as a third copy, not sufficient alone on this SHA"
                ),
            }
        )
    soft = [
        {
            "id": "provider_http_attempts",
            "enforcement": SOFT,
            "how": "no EOS transport interceptor; Codex/OpenAI retries are uncounted",
        },
        {
            "id": "inner_retries",
            "enforcement": SOFT,
            "how": "provider SDK retries are not Hermes --max-turns",
        },
    ]
    unavailable = [
        {
            "id": "token_totals",
            "enforcement": UNAVAILABLE,
            "how": "Codex OAuth path does not expose a trusted token meter to EOS",
        },
        {
            "id": "dollar_cost",
            "enforcement": UNAVAILABLE,
            "how": "subscription/OAuth; this protocol does not invent a price",
        },
    ]
    return {
        "protocol_id": protocol.get("experiment_id"),
        "hard": hard,
        "soft": soft,
        "unavailable": unavailable,
        "authorization_binds": "HARD fields only",
        "quiet_flag_caps_turns": False,
    }
