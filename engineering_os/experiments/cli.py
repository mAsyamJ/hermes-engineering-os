"""CLI: engineering-os-experiment. Never mutates Hermes or production routing."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from engineering_os.experiments import CONTRACT_VERSION
from engineering_os.experiments.definitions import DefinitionError, load_id, load_path
from engineering_os.experiments.explain import explain
from engineering_os.experiments.plan import plan_binary
from engineering_os.experiments.preregister import freeze


def _ensure_experiment_runtime() -> None:
    os.environ.setdefault("EOS_EXPERIMENT_RUNTIME", "/opt/hermes-engineering-os/.runtime/experiments")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engineering-os-experiment")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("definition")
    p_preg = sub.add_parser("preregister")
    p_preg.add_argument("definition")
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("experiment")
    p_assign = sub.add_parser("assign")
    p_assign.add_argument("experiment")
    p_run = sub.add_parser("run-fixture")
    p_run.add_argument("experiment")
    p_collect = sub.add_parser("collect")
    p_collect.add_argument("experiment")
    p_analyze = sub.add_parser("analyze")
    p_analyze.add_argument("experiment")
    p_analyze.add_argument("--final", action="store_true")
    p_analyze.add_argument("--recompute", action="store_true")
    p_explain = sub.add_parser("explain")
    p_explain.add_argument("experiment")
    p_inv = sub.add_parser("invalidate")
    p_inv.add_argument("experiment")
    p_inv.add_argument("--reason", required=True)
    p_limits = sub.add_parser("budget-limits")
    p_limits.add_argument("experiment")
    p_wb = sub.add_parser("write-budget")
    p_wb.add_argument("--phrase", required=True)
    p_wb.add_argument("--created-by", required=True)
    p_wb.add_argument("--expiry", required=True)
    p_real = sub.add_parser("run-real")
    p_real.add_argument("experiment")
    p_areal = sub.add_parser("analyze-real")
    p_areal.add_argument("experiment")
    p_areal.add_argument("--final", action="store_true")
    p_status = sub.add_parser("status")
    p_status.add_argument("experiment", nargs="?")
    return parser


def _definition(target: str) -> dict[str, Any]:
    path = Path(target)
    if path.suffix in {".yaml", ".yml"}:
        return load_path(path)
    return load_id(target)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload: dict[str, Any]
        if args.command == "validate":
            definition = _definition(args.definition)
            protocol = freeze(definition)
            payload = {
                "status": "success",
                "experiment_id": definition["experiment_id"],
                "definition_hash": definition["_definition_hash"],
                "pre_registration_hash": protocol["pre_registration_hash"],
                "state": "VALIDATED",
                "contract_version": CONTRACT_VERSION,
            }
        elif args.command == "plan":
            definition = _definition(args.experiment)
            sample = definition["sample_plan"]
            payload = plan_binary(
                baseline_rate=float(sample.get("baseline_rate") or 0.5),
                mde=float(sample.get("mde") or 0.2),
                alpha=float(sample["alpha"]),
                power=float(sample["power"]),
                allocation_ratio=float(sample.get("allocation_ratio") or 1.0),
                max_units=int((definition.get("budget") or {}).get("max_units") or 0) or None,
                max_llm_calls=int((definition.get("budget") or {}).get("max_llm_calls") or 0),
                requires_llm=definition["treatment_dimension"] in {"MODEL", "PROFILE", "PROMPT", "SKILL"},
                paired=definition["design"] == "PAIRED",
                discordance=sample.get("discordance"),
            )
            payload["registered_planned_n"] = sample["planned_n"]
            payload["shrunk"] = False
        elif args.command == "preregister":
            from engineering_os.experiments.persist import preregister

            payload = preregister(args.definition)
        elif args.command == "assign":
            from engineering_os.experiments.persist import assign

            payload = assign(args.experiment)
        elif args.command == "run-fixture":
            from engineering_os.experiments.persist import run_fixture

            payload = run_fixture(args.experiment)
        elif args.command == "collect":
            from engineering_os.experiments.persist import collect

            payload = collect(args.experiment)
        elif args.command == "analyze":
            from engineering_os.experiments.persist import analyze_experiment

            payload = analyze_experiment(args.experiment, final=args.final, recompute=args.recompute)
        elif args.command == "explain":
            payload = explain(args.experiment)
        elif args.command == "invalidate":
            from engineering_os.experiments.persist import invalidate

            payload = invalidate(args.experiment, args.reason)
        elif args.command == "budget-limits":
            from engineering_os.experiments.budget_limits import classify_budget

            definition = _definition(args.experiment)
            payload = {"status": "success", **classify_budget(definition)}
        elif args.command == "write-budget":
            from engineering_os.adaptation.pag2_ops import read_h1_status
            from engineering_os.experiments.budget_gate import write_h2_authorization

            definition = load_id("real-model-sol-vs-terra-v2")
            payload = write_h2_authorization(
                phrase=args.phrase,
                created_by=args.created_by,
                expiry=args.expiry,
                h1_status=read_h1_status(),
                protocol=definition,
            )
        elif args.command == "run-real":
            from engineering_os.experiments.hard_runner import (
                assignments_from_protocol,
                run_authorized_sequence,
            )

            _ensure_experiment_runtime()
            definition = _definition(args.experiment)
            assignments = assignments_from_protocol(definition)
            payload = run_authorized_sequence(assignments, definition)
        elif args.command == "analyze-real":
            from engineering_os.experiments.real_analyze import analyze_persisted

            _ensure_experiment_runtime()
            definition = _definition(args.experiment)
            payload = analyze_persisted(str(definition["experiment_id"]), definition, final=True)
        elif args.command == "status":
            from engineering_os.experiments.persist import status

            payload = status(args.experiment)
        else:
            payload = {"status": "error", "detail": "unknown command"}
    except (DefinitionError, ValueError, PermissionError) as exc:
        payload = {"status": "rejected", "detail": str(exc), "contract_version": CONTRACT_VERSION}
        print(json.dumps(payload, default=str) if args.json else str(exc), file=sys.stderr if not args.json else sys.stdout)
        return 2
    if args.json or True:
        print(json.dumps(payload, default=str, indent=2 if not args.json else None))
    ok_status = {
        "success",
        "AVAILABLE",
        "unchanged",
        "FEASIBLE",
        "blocked",
        "COMPLETE",
        "HARD_STOP_UNITS",
        "HARD_STOP_INVOCATIONS",
        "HARD_STOP_WALL_TOTAL",
    }
    return 0 if payload.get("status") in ok_status or payload.get("ok") is True or payload.get("conclusion") else 1


if __name__ == "__main__":
    raise SystemExit(main())
