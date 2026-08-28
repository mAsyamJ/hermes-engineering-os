"""Incremental experiment collect / drift. Fail-open; lock is success."""

from __future__ import annotations

import argparse
import json

from engineering_os.analytics.db import advisory_unlock, connect, fetch_all, try_advisory_lock
from engineering_os.experiments import ADVISORY_LOCK_KEY, CONTRACT_VERSION
from engineering_os.experiments.persist import advisory_held, analyze_experiment, collect
from engineering_os.experiments import ANALYTICS_LOCK_KEY, EVALUATION_LOCK_KEY, PERFORMANCE_LOCK_KEY


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engineering-os-experiments-materialize")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--recompute", action="store_true")
    args = parser.parse_args(argv)
    with connect() as connection:
        if not try_advisory_lock(connection, ADVISORY_LOCK_KEY):
            payload = {"status": "locked", "contract_version": CONTRACT_VERSION, "detail": "experiment lock held"}
            print(json.dumps(payload))
            return 0
        try:
            if (
                advisory_held(connection, ANALYTICS_LOCK_KEY)
                or advisory_held(connection, EVALUATION_LOCK_KEY)
                or advisory_held(connection, PERFORMANCE_LOCK_KEY)
            ):
                payload = {
                    "status": "locked",
                    "contract_version": CONTRACT_VERSION,
                    "detail": "prior phase materialization in progress",
                }
                print(json.dumps(payload))
                return 0
            protocols = fetch_all(
                connection,
                "SELECT experiment_id, state FROM experiment_protocol_versions WHERE state IN ('READY','RUNNING','COMPLETED')",
            )
            results = []
            if args.dry_run:
                payload = {"status": "success", "mode": "dry-run", "protocols": len(protocols), "contract_version": CONTRACT_VERSION}
                print(json.dumps(payload, default=str))
                return 0
            for row in protocols:
                collect(row["experiment_id"], connection=connection)
                if args.recompute or row["state"] in {"RUNNING", "COMPLETED"}:
                    results.append(analyze_experiment(row["experiment_id"], final=False, recompute=args.recompute, connection=connection))
            payload = {
                "status": "success",
                "mode": "recompute" if args.recompute else "incremental",
                "protocols": len(protocols),
                "results": len(results),
                "contract_version": CONTRACT_VERSION,
            }
            print(json.dumps(payload, default=str))
            return 0
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


if __name__ == "__main__":
    raise SystemExit(main())
