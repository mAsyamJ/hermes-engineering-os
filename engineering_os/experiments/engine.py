"""DB-free experiment engine for golden tests."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments.analyze import analyze
from engineering_os.experiments.assignment import assign_blocked, assign_paired, balance_report
from engineering_os.experiments.benchmarks import default_cases
from engineering_os.experiments.executor import collect_from_execution, run_unit
from engineering_os.experiments.exposure import record as record_exposure
from engineering_os.experiments.guardrails import evaluate as eval_guardrails
from engineering_os.experiments.preregister import freeze
from engineering_os.experiments.validity import evaluate as eval_validity


def qualify(definition: dict[str, Any], *, execute: bool = True, final: bool = True) -> dict[str, Any]:
    protocol = freeze(definition)
    planned = int(protocol["sample_plan"]["planned_n"])
    suite = protocol.get("benchmark_suite") or "fixture-v1"
    seed = protocol["assignment"]["seed"]
    control_id = protocol["control"]["variant_id"]
    cand_id = protocol["candidate"]["variant_id"]
    if protocol["design"] == "PAIRED":
        cases = protocol.get("cases") or default_cases(planned, "clean", suite)
        assignments = assign_paired(cases, seed, control_id, cand_id)
    else:
        cases = protocol.get("cases") or default_cases(planned, "clean", suite)
        units = [{"unit_id": item["case_id"], "stratum": item.get("stratum") or suite} for item in cases]
        assignments = assign_blocked(units, seed, control_id, cand_id)
    observations: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    executions: list[dict[str, Any]] = []
    if execute:
        for assignment in assignments:
            execution = run_unit(assignment, protocol)
            executions.append(execution)
            observations.extend(collect_from_execution(execution, protocol))
            variant = protocol["control"] if assignment["variant_role"] == "CONTROL" else protocol["candidate"]
            exposures.append(
                record_exposure(
                    {**assignment, "assigned_config_hash": variant["config_hash"]},
                    execution["tree_hash"],
                    True,
                )
            )
    guard = eval_guardrails(protocol, observations, llm_calls=0)
    validity = eval_validity(
        {
            "scope": protocol["scope"],
            "protocol_hash_ok": True,
            "assignment_ok": balance_report(assignments)["integrity"] == "PASS",
            "config_ok": protocol["config_diff"]["ok"],
            "environment_ok": True,
            "memory_mode": "fixture_executor",
            "workspace_ok": all(item.get("workspace_ok", True) for item in executions) if executions else True,
            "coverage_ok": True,
            "evaluator_ok": True,
            "fidelity_required": False,
        }
    )
    result = analyze(
        protocol,
        assignments,
        observations,
        exposures,
        validity,
        final=final,
        guardrail_state=guard["state"],
    )
    return {
        "protocol": protocol,
        "assignments": assignments,
        "observations": observations,
        "exposures": exposures,
        "executions": executions,
        "guardrails": guard,
        "validity": validity,
        "result": result,
        "balance": balance_report(assignments),
    }
