"""Sequential isolated real-model runner. Enforces HARD unit/invocation/wall caps."""

from __future__ import annotations

import json
import time
from typing import Any

from engineering_os.experiments.assignment import assign_paired
from engineering_os.experiments.benchmarks import load_suite
from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.budget_limits import per_unit_wall_seconds, total_wall_seconds
from engineering_os.experiments.hermes_runner import execute_authorized_unit
from engineering_os.experiments.real_analyze import analyze_real_sequence, persist_sequence


def confirmatory_cases(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """28 independent pairs over the 5 real-v1 templates. Unique pair_id per execution."""
    planned = int((protocol.get("sample_plan") or {}).get("planned_n") or 0)
    suite_id = str(protocol.get("benchmark_suite") or "real-v1")
    templates = list((load_suite(suite_id).get("cases") or []))
    if not templates:
        raise ValueError(f"no cases in suite {suite_id}")
    rows: list[dict[str, Any]] = []
    for index in range(planned):
        tmpl = templates[index % len(templates)]
        rows.append(
            {
                "case_id": tmpl["case_id"],
                "pair_id": f"{suite_id}-pair-{index + 1:02d}",
                "stratum": tmpl.get("stratum") or suite_id,
                "artifact": tmpl.get("artifact") or "broken",
                "suite": suite_id,
            }
        )
    return rows


def assignments_from_protocol(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    return assign_paired(
        confirmatory_cases(protocol),
        str(protocol["assignment"]["seed"]),
        str(protocol["control"]["variant_id"]),
        str(protocol["candidate"]["variant_id"]),
    )


def run_authorized_sequence(
    assignments: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    gate = require_budget_authorization(protocol)
    if not gate.get("ok"):
        return {
            "ok": False,
            "executed": False,
            "status": gate.get("status"),
            "reason": gate.get("reason"),
            "results": [],
        }
    max_units = int(gate.get("max_units") or 0)
    max_calls = int(gate.get("max_llm_calls") or 0)
    wall_total = total_wall_seconds(protocol)
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    invocations = 0
    for index, assignment in enumerate(assignments):
        if index >= max_units:
            return _finish("HARD_STOP_UNITS", protocol, assignments, results, invocations, time.monotonic() - started)
        if invocations >= max_calls:
            return _finish("HARD_STOP_INVOCATIONS", protocol, assignments, results, invocations, time.monotonic() - started)
        elapsed = time.monotonic() - started
        if wall_total and elapsed >= wall_total:
            return _finish("HARD_STOP_WALL_TOTAL", protocol, assignments, results, invocations, elapsed)
        remaining_total = max(1, int(wall_total - elapsed)) if wall_total else per_unit_wall_seconds(protocol)
        remaining_gate = dict(gate)
        remaining_gate["max_llm_calls"] = max_calls - invocations
        remaining_gate["remaining_wall_seconds"] = remaining_total
        result = dict(assignment)
        result.update(execute_authorized_unit(assignment, protocol, remaining_gate))
        results.append(result)
        persist_sequence(protocol, assignments, results, extra={"status": "RUNNING", "invocations": invocations})
        if result.get("executed"):
            invocations += int(result.get("llm_calls") or 1)
    return _finish("COMPLETE", protocol, assignments, results, invocations, time.monotonic() - started)


def _finish(
    status: str,
    protocol: dict[str, Any],
    assignments: list[dict[str, Any]],
    results: list[dict[str, Any]],
    invocations: int,
    elapsed: float | None = None,
) -> dict[str, Any]:
    persist_sequence(protocol, assignments, results, extra={"status": status, "invocations": invocations})
    analyzed = analyze_real_sequence(protocol, assignments, results, final=True)
    from engineering_os.experiments.real_analyze import artifact_dir

    analysis_path = artifact_dir(protocol) / "analysis.json"
    analysis_path.write_text(json.dumps(analyzed, default=str, indent=2) + "\n", encoding="utf-8")
    payload = {
        "ok": True,
        "status": status,
        "results": results,
        "units": len(results),
        "invocations": invocations,
        "pag2_label": analyzed.get("pag2_label"),
        "analysis": analyzed.get("analysis"),
        "recommendation": analyzed.get("recommendation"),
        "auto_promote": False,
        "promote": False,
    }
    if elapsed is not None:
        payload["elapsed_seconds"] = elapsed
    return payload
