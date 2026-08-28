"""CLI: engineering-os-adapt. Never mutates Hermes or production routing."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from engineering_os.adaptation import CONTRACT_VERSION, PRODUCTION_APPROVAL
from engineering_os.adaptation.approval import approve_production
from engineering_os.adaptation.compiler import compile_policy
from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.adaptation.resolver import resolve_policy, load_cache
from engineering_os.adaptation.schema import PolicyError, load_id, load_path
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engineering-os-adapt")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    p_rec = sub.add_parser("recommend")
    p_rec.add_argument("experiment")
    p_exp = sub.add_parser("explain-recommendation")
    p_exp.add_argument("recommendation_id")
    p_comp = sub.add_parser("compile-policy")
    p_comp.add_argument("recommendation")
    p_comp.add_argument("--policy", required=True)
    p_req = sub.add_parser("request-approval")
    p_req.add_argument("policy")
    p_req.add_argument("--stage", default="A")
    p_at = sub.add_parser("approve-test")
    p_at.add_argument("policy")
    p_at.add_argument("--stage", default="A")
    sub.add_parser("approve")
    p_ss = sub.add_parser("shadow-start")
    p_ss.add_argument("policy")
    p_ss.add_argument("--board")
    p_sst = sub.add_parser("shadow-status")
    p_sst.add_argument("policy")
    p_cp = sub.add_parser("canary-plan")
    p_cp.add_argument("policy")
    p_cs = sub.add_parser("canary-start-fixture")
    p_cs.add_argument("policy")
    p_cst = sub.add_parser("canary-status")
    p_cst.add_argument("policy")
    p_dis = sub.add_parser("disable")
    p_dis.add_argument("policy")
    p_dis.add_argument("--reason", default="operator disable")
    p_rb = sub.add_parser("rollback")
    p_rb.add_argument("policy")
    p_rb.add_argument("--reason", default="operator rollback")
    p_pr = sub.add_parser("promotion-request")
    p_pr.add_argument("policy")
    sub.add_parser("status")
    p_da = sub.add_parser("disable-all")
    p_da.add_argument("--reason", default="global kill switch")
    p_res = sub.add_parser("resolve")
    p_res.add_argument("--board", default="eos-phase6-exp")
    p_res.add_argument("--task-class", default="fixture")
    p_res.add_argument("--environment", default="fixture")
    p_res.add_argument("--scope", default="FIXTURE")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload: dict[str, Any]
        if args.command == "approve":
            payload = approve_production()
        elif args.command == "resolve":
            payload = resolve_policy(
                {
                    "board": args.board,
                    "task_class": args.task_class,
                    "environment": args.environment,
                    "scope": args.scope,
                    "task_id": "cli-resolve",
                }
            )
        elif args.command == "status":
            from engineering_os.adaptation.persist import health

            payload = health()
        elif args.command == "recommend":
            from engineering_os.adaptation.persist import recommend

            payload = recommend(args.experiment)
        elif args.command == "explain-recommendation":
            from engineering_os.adaptation.explain import explain

            payload = explain(args.recommendation_id)
        elif args.command == "compile-policy":
            from engineering_os.adaptation.persist import compile_and_store

            payload = compile_and_store(args.recommendation, args.policy)
        elif args.command == "request-approval":
            from engineering_os.adaptation.persist import request_approval

            payload = request_approval(args.policy, stage=args.stage)
        elif args.command == "approve-test":
            from engineering_os.adaptation.persist import approve_test

            payload = approve_test(args.policy, stage=args.stage)
        elif args.command == "shadow-start":
            from engineering_os.adaptation.persist import shadow_start

            payload = shadow_start(args.policy, board=args.board)
        elif args.command == "shadow-status":
            from engineering_os.adaptation.api import shadow

            payload = shadow()
        elif args.command == "canary-plan":
            from engineering_os.adaptation.canary import plan_canary
            from engineering_os.adaptation.schema import load_id

            payload = plan_canary(load_id(args.policy))
        elif args.command == "canary-start-fixture":
            from engineering_os.adaptation.persist import canary_start_fixture

            payload = canary_start_fixture(args.policy)
        elif args.command == "canary-status":
            from engineering_os.adaptation.api import canaries

            payload = canaries()
        elif args.command == "disable":
            from engineering_os.adaptation.persist import disable_policy

            payload = disable_policy(args.policy, reason=args.reason)
        elif args.command == "rollback":
            from engineering_os.adaptation.persist import rollback_policy

            payload = rollback_policy(args.policy, reason=args.reason)
        elif args.command == "promotion-request":
            from engineering_os.adaptation.persist import promotion_request

            payload = promotion_request(args.policy)
        elif args.command == "disable-all":
            from engineering_os.adaptation.persist import disable_all

            payload = disable_all(reason=args.reason)
        else:
            payload = {"status": "error", "reason": "unknown command"}
    except Exception as exc:
        payload = {"status": "error", "reason": f"{type(exc).__name__}: {exc}", "contract_version": CONTRACT_VERSION}
        print(json.dumps(payload, default=str))
        return 1
    if not args.json and "status" in payload:
        pass
    print(json.dumps(payload, default=str))
    if payload.get("status") in {"error", "rejected", "conflict", "not_found", "BLOCKED_APPROVAL_BOUNDARY"}:
        return 1 if payload.get("status") == "error" else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
