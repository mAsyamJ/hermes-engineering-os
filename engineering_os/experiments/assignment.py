"""Deterministic HMAC assignment. No Python hash(), no process entropy."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Iterable

from engineering_os.experiments import ASSIGNMENT_ALGORITHM_VERSION, VARIANT_ROLES

ALG = ASSIGNMENT_ALGORITHM_VERSION


def _digest(seed: str, message: str) -> bytes:
    return hmac.new(seed.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()


def _hex(seed: str, message: str) -> str:
    return _digest(seed, message).hex()


def sort_key(seed: str, stratum: str, unit_id: str) -> str:
    return _hex(seed, f"{ALG}|{stratum}|{unit_id}")


def start_bit(seed: str, stratum: str) -> int:
    return _digest(seed, f"{ALG}|{stratum}|start")[0] % 2


def pair_order_bit(seed: str, pair_id: str) -> int:
    return _digest(seed, f"order|{pair_id}")[0] % 2


def assign_blocked(
    units: Iterable[dict[str, Any]],
    seed: str,
    control_variant_id: str,
    candidate_variant_id: str,
    algorithm_version: str = ALG,
) -> list[dict[str, Any]]:
    if algorithm_version != ALG:
        raise ValueError(f"unsupported assignment algorithm {algorithm_version}")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        stratum = str(unit.get("stratum") or "default")
        grouped.setdefault(stratum, []).append(unit)
    rows: list[dict[str, Any]] = []
    for stratum in sorted(grouped):
        ordered = sorted(
            grouped[stratum],
            key=lambda unit: sort_key(seed, stratum, str(unit["unit_id"])),
        )
        bit = start_bit(seed, stratum)
        for index, unit in enumerate(ordered):
            role = VARIANT_ROLES[(index + bit) % 2]
            variant_id = control_variant_id if role == "CONTROL" else candidate_variant_id
            assignment_hash = _hex(seed, f"{ALG}|{stratum}|{unit['unit_id']}|{role}|{variant_id}")
            rows.append(
                {
                    "unit_id": unit["unit_id"],
                    "stratum": stratum,
                    "variant_role": role,
                    "variant_id": variant_id,
                    "pair_id": unit.get("pair_id"),
                    "seed": seed,
                    "assignment_algorithm_version": ALG,
                    "assignment_hash": assignment_hash,
                    "sort_key": sort_key(seed, stratum, str(unit["unit_id"])),
                }
            )
    return sorted(rows, key=lambda row: (row["stratum"], row["unit_id"]))


def assign_paired(
    cases: Iterable[dict[str, Any]],
    seed: str,
    control_variant_id: str,
    candidate_variant_id: str,
    algorithm_version: str = ALG,
) -> list[dict[str, Any]]:
    """Each case yields two independent units, one per arm. Order is randomized."""
    if algorithm_version != ALG:
        raise ValueError(f"unsupported assignment algorithm {algorithm_version}")
    rows: list[dict[str, Any]] = []
    for case in cases:
        pair_id = str(case["pair_id"])
        stratum = str(case.get("stratum") or "default")
        order = pair_order_bit(seed, pair_id)
        sequence = ("CONTROL", "CANDIDATE") if order == 0 else ("CANDIDATE", "CONTROL")
        for role in sequence:
            unit_id = f"{pair_id}:{role.lower()}"
            variant_id = control_variant_id if role == "CONTROL" else candidate_variant_id
            assignment_hash = _hex(seed, f"{ALG}|{stratum}|{unit_id}|{role}|{variant_id}")
            rows.append(
                {
                    "unit_id": unit_id,
                    "stratum": stratum,
                    "variant_role": role,
                    "variant_id": variant_id,
                    "pair_id": pair_id,
                    "execution_order": sequence.index(role),
                    "seed": seed,
                    "assignment_algorithm_version": ALG,
                    "assignment_hash": assignment_hash,
                    "case_id": case.get("case_id") or pair_id,
                }
            )
    return rows


def balance_report(assignments: list[dict[str, Any]], planned_ratio: float = 1.0) -> dict[str, Any]:
    control = sum(1 for row in assignments if row["variant_role"] == "CONTROL")
    candidate = sum(1 for row in assignments if row["variant_role"] == "CANDIDATE")
    total = control + candidate
    actual_ratio = None if control == 0 else candidate / control
    mismatch = False
    reason = "PASS"
    if total >= 8 and actual_ratio is not None:
        # Documented rule: invalidate only when |actual - planned| > 0.35 and n>=8.
        if abs(actual_ratio - planned_ratio) > 0.35:
            mismatch = True
            reason = "sample-ratio mismatch exceeds documented tolerance"
    return {
        "assigned_n": total,
        "assigned_control": control,
        "assigned_candidate": candidate,
        "planned_ratio": planned_ratio,
        "actual_ratio": actual_ratio,
        "mismatch": mismatch,
        "reason": reason,
        "integrity": "FAIL" if mismatch else "PASS",
    }
