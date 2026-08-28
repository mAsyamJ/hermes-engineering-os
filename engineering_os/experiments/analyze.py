"""Fixed-horizon ITT analysis. No hidden metric search. No peeking."""

from __future__ import annotations

from typing import Any

from engineering_os.experiments import ANALYSIS_VERSION, CONCLUSIONS, CONTRACT_VERSION
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text
from engineering_os.experiments.stats import independent_binary, paired_binary
from engineering_os.evaluation import CONTRACT_VERSION as PHASE4
from engineering_os.performance import CONTRACT_VERSION as PHASE5

PHASE3 = "phase3-v1"
CONFIRMATORY = {
    "EVIDENCE_FOR_CANDIDATE",
    "EVIDENCE_AGAINST_CANDIDATE",
    "NO_CLEAR_EFFECT",
}


def _binary(value: Any) -> int | None:
    if value in (None, "UNKNOWN", "NOT_APPLICABLE", "ERROR", "MISSING"):
        return None
    if value in (1, True, "PASS", "1", "true"):
        return 1
    if value in (0, False, "FAIL", "0", "false"):
        return 0
    return None


def analyze(
    protocol: dict[str, Any],
    assignments: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    exposures: list[dict[str, Any]] | None = None,
    validity: dict[str, str] | None = None,
    *,
    final: bool = False,
    population: str = "INTENTION_TO_TREAT",
    guardrail_state: str = "PASS",
) -> dict[str, Any]:
    if population != "INTENTION_TO_TREAT" and protocol["analysis"].get("primary_population", "INTENTION_TO_TREAT") == "INTENTION_TO_TREAT":
        secondary = True
    else:
        secondary = population != "INTENTION_TO_TREAT"
    primary_id = protocol["primary_metric"]["id"]
    planned_n = int(protocol["sample_plan"]["planned_n"])
    threshold = float((protocol.get("missingness") or {}).get("threshold") or 0.25)
    on_exceed = (protocol.get("missingness") or {}).get("on_exceed") or "INSUFFICIENT_DATA"
    obs_by_unit = {
        row["unit_id"]: row
        for row in observations
        if row.get("metric_id") == primary_id
    }
    exp_by_unit = {row["unit_id"]: row for row in (exposures or [])}

    if population == "PER_PROTOCOL":
        eligible_ids = {
            unit_id
            for unit_id, row in exp_by_unit.items()
            if row.get("fidelity") == "MATCHED"
        }
        assignments = [row for row in assignments if row["unit_id"] in eligible_ids]

    control_vals: list[int | None] = []
    cand_vals: list[int | None] = []
    control_units: list[str] = []
    cand_units: list[str] = []
    for row in assignments:
        value = _binary((obs_by_unit.get(row["unit_id"]) or {}).get("value"))
        if row["variant_role"] == "CONTROL":
            control_vals.append(value)
            control_units.append(row["unit_id"])
        else:
            cand_vals.append(value)
            cand_units.append(row["unit_id"])

    assigned_n = len(assignments)
    known_n = sum(v is not None for v in control_vals + cand_vals)
    missing_n = assigned_n - known_n
    started_n = sum(
        1
        for row in assignments
        if (obs_by_unit.get(row["unit_id"]) or {}).get("started") or row["unit_id"] in obs_by_unit
    )
    completed_n = sum(1 for row in assignments if row["unit_id"] in obs_by_unit)

    if protocol["design"] == "PAIRED":
        pair_ids = {row.get("pair_id") for row in assignments}
        collected_pairs = 0
        for pair in pair_ids:
            members = [item for item in assignments if item.get("pair_id") == pair]
            if members and all(item["unit_id"] in obs_by_unit for item in members):
                collected_pairs += 1
        horizon_reached = len(pair_ids) >= planned_n and collected_pairs >= planned_n
    else:
        horizon_reached = assigned_n >= planned_n and completed_n >= planned_n

    blocked = None
    conclusion = "COLLECTING"
    if not horizon_reached:
        if final:
            blocked = "BLOCKED_HORIZON"
            conclusion = "COLLECTING"
        else:
            conclusion = "COLLECTING"
    validity = validity or {}
    required_fail = [name for name, state in validity.items() if state not in {"PASS", "NA", "BLOCKED_CAPABILITY"}]
    # BLOCKED_CAPABILITY is allowed only for MEMORY_ISOLATION on fixture experiments.
    mem = validity.get("MEMORY_ISOLATION")
    if mem == "BLOCKED_CAPABILITY" and protocol.get("scope") != "FIXTURE":
        required_fail.append("MEMORY_ISOLATION")
    if mem == "FAIL":
        required_fail.append("MEMORY_ISOLATION")

    stats: dict[str, Any]
    if protocol["design"] == "PAIRED":
        by_pair: dict[str, dict[str, int | None]] = {}
        for row in assignments:
            pair = str(row.get("pair_id"))
            by_pair.setdefault(pair, {})[row["variant_role"]] = _binary(
                (obs_by_unit.get(row["unit_id"]) or {}).get("value")
            )
        control_paired = [item.get("CONTROL") for item in by_pair.values()]
        cand_paired = [item.get("CANDIDATE") for item in by_pair.values()]
        stats = paired_binary(control_paired, cand_paired)
    else:
        stats = independent_binary(control_vals, cand_vals)

    missing_rate = None if assigned_n == 0 else missing_n / assigned_n
    source_versions = {
        "phase3_ruleset": PHASE3,
        "phase4_contract": PHASE4,
        "phase5_contract": PHASE5,
        "phase6_contract": CONTRACT_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "analysis_hash": sha256_text(canonical_dumps({"analysis": protocol["analysis"], "primary": primary_id})),
    }

    if blocked:
        conclusion = "COLLECTING"
    elif required_fail:
        conclusion = "INVALIDATED"
    elif guardrail_state == "FAIL":
        conclusion = "GUARDRAIL_FAILURE"
    elif horizon_reached and missing_rate is not None and missing_rate > threshold:
        conclusion = on_exceed if on_exceed in CONCLUSIONS else "INSUFFICIENT_DATA"
    elif horizon_reached and known_n == 0:
        conclusion = "INSUFFICIENT_DATA"
    elif horizon_reached:
        lo = stats.get("interval_low")
        hi = stats.get("interval_high")
        delta = stats.get("absolute_difference")
        if delta is None or lo is None or hi is None:
            conclusion = "INSUFFICIENT_DATA"
        elif lo > 0:
            conclusion = "EVIDENCE_FOR_CANDIDATE"
        elif hi < 0:
            conclusion = "EVIDENCE_AGAINST_CANDIDATE"
        else:
            conclusion = "NO_CLEAR_EFFECT"

    if conclusion in CONFIRMATORY and protocol.get("fixture_validation_only"):
        reason_suffix = " FIXTURE_VALIDATION_ONLY; not production causal evidence."
    else:
        reason_suffix = ""

    if secondary and conclusion in CONFIRMATORY:
        reason_suffix += " Secondary population; primary remains ITT."

    result = {
        "status": "success" if blocked is None else "blocked",
        "blocked": blocked,
        "conclusion": conclusion,
        "population": population,
        "primary_metric": primary_id,
        "assigned_n": assigned_n,
        "started_n": started_n,
        "completed_n": completed_n,
        "known_n": known_n,
        "missing_n": missing_n,
        "missing_rate": missing_rate,
        "itt_n_control": len(control_vals),
        "itt_n_candidate": len(cand_vals),
        "effect_estimate": stats.get("absolute_difference"),
        "uncertainty": {
            "interval_low": stats.get("interval_low"),
            "interval_high": stats.get("interval_high"),
            "method": stats.get("method"),
            "z": 1.96,
        },
        "stats": stats,
        "guardrail_state": guardrail_state,
        "validity": validity,
        "horizon_reached": horizon_reached,
        "planned_n": planned_n,
        "analysis_version": ANALYSIS_VERSION,
        "source_versions": source_versions,
        "fixture_validation_only": bool(protocol.get("fixture_validation_only")),
        "reason": _reason(conclusion, blocked, missing_rate, threshold) + reason_suffix,
        "auto_route": False,
        "promote": False,
    }
    return result


def _reason(conclusion: str, blocked: str | None, missing_rate: float | None, threshold: float) -> str:
    if blocked == "BLOCKED_HORIZON":
        return "Confirmatory analysis blocked until the pre-registered sample horizon."
    if conclusion == "COLLECTING":
        return "Fixed-horizon experiment has not reached planned N."
    if conclusion == "INVALIDATED":
        return "Required validity dimension failed; confirmatory interpretation is invalid."
    if conclusion == "GUARDRAIL_FAILURE":
        return "Safety guardrail triggered. This is not an efficacy ranking."
    if conclusion == "INSUFFICIENT_DATA":
        if missing_rate is not None and missing_rate > threshold:
            return f"Missingness {missing_rate:.3f} exceeds threshold {threshold:.3f}."
        return "Primary outcome coverage is insufficient for confirmatory interpretation."
    if conclusion == "NO_CLEAR_EFFECT":
        return "Uncertainty interval includes 0; no clear candidate effect."
    if conclusion == "EVIDENCE_FOR_CANDIDATE":
        return "ITT interval excludes 0 in the candidate direction."
    if conclusion == "EVIDENCE_AGAINST_CANDIDATE":
        return "ITT interval excludes 0 against the candidate."
    return conclusion
