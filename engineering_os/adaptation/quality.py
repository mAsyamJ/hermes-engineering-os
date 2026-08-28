"""Adaptation data-quality invariants. Fail closed; never mutate Hermes."""

from __future__ import annotations

from typing import Any

from engineering_os.adaptation.db import connect, fetch_one


CHECKS = (
    (
        "fixture_production_leakage",
        """
        SELECT COUNT(*) AS n FROM adaptation_policy_bundles
        WHERE scope LIKE 'PRODUCTION%%' AND spec->>'source_classification' = 'TEST_ONLY'
        """,
    ),
    (
        "policy_without_experiment",
        """
        SELECT COUNT(*) AS n FROM adaptation_policy_bundles
        WHERE source_recommendation_id IS NULL
        """,
    ),
    (
        "stale_approval_active",
        """
        SELECT COUNT(*) AS n
        FROM adaptation_bindings b
        JOIN adaptation_approvals a ON a.policy_hash = b.policy_hash AND a.state = 'GRANTED'
        WHERE b.is_current AND b.mode IN ('CANARY','PROMOTED') AND a.expires_at < NOW()
        """,
    ),
    (
        "test_approval_production",
        """
        SELECT COUNT(*) AS n FROM adaptation_approvals
        WHERE approval_class = 'TEST' AND scope LIKE 'PRODUCTION%%' AND state = 'GRANTED'
        """,
    ),
    (
        "active_without_rollback",
        """
        SELECT COUNT(*) AS n FROM adaptation_policy_bundles p
        JOIN adaptation_bindings b ON b.policy_hash = p.policy_hash AND b.is_current
        WHERE b.mode IN ('CANARY','PROMOTED') AND (p.fallback_config_hash IS NULL OR p.fallback_config_hash = '')
        """,
    ),
    (
        "rollback_still_assigning",
        """
        SELECT COUNT(*) AS n FROM adaptation_bindings
        WHERE is_current AND state IN ('ROLLED_BACK','DISABLED') AND mode = 'CANARY'
        """,
    ),
)


def run_checks(connection: Any | None = None) -> dict[str, Any]:
    owns = connection is None
    cm = None
    if owns:
        cm = connect()
        connection = cm.__enter__()
    try:
        violations: list[dict[str, Any]] = []
        for name, sql in CHECKS:
            row = fetch_one(connection, sql) or {}
            n = int(row.get("n") or 0)
            if n:
                violations.append({"check": name, "n": n})
        return {"status": "PASS" if not violations else "FAIL", "violations": violations}
    finally:
        if owns and cm is not None:
            cm.__exit__(None, None, None)


def main() -> int:
    payload = run_checks()
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
