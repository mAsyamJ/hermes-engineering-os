"""Deterministic multi-label failure taxonomy. No LLM."""

from __future__ import annotations

from collections import Counter
from typing import Any

from engineering_os.performance.stats import coverage_ratio, proportion, wilson_interval
from engineering_os.performance.tiers import classify_tier

QUALITY_FAIL_MAP = {
    "BUILD_FAILURE": "build",
    "TEST_FAILURE": "tests",
    "INTRODUCED_REGRESSION": "regression",
    "TYPECHECK_FAILURE": "typecheck",
    "LINT_REGRESSION": "lint",
    "ARCHITECTURE_POLICY_FAILURE": "architecture",
    "SECURITY_EVALUATOR_FAILURE": "security",
}


def labels_for(task: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    if task.get("lifecycle_state") == "NOT_DONE":
        labels.append("LIFECYCLE_INCOMPLETE")
    if task.get("verification_state") == "FAIL" or task.get("final_outcome") == "VERIFIED_FAILURE":
        labels.append("VERIFICATION_FAILURE")
    evaluation = task.get("evaluation") or {}
    vector = evaluation.get("quality_vector") or {}
    eligibility = evaluation.get("eligibility")
    if eligibility == "INSUFFICIENT_EVIDENCE":
        labels.append("INSUFFICIENT_EVIDENCE")
    if evaluation.get("execution_status") == "ERROR":
        labels.append("UNKNOWN")
    if vector.get("build") == "FAIL":
        labels.append("BUILD_FAILURE")
    if vector.get("tests") == "FAIL":
        labels.append("TEST_FAILURE")
    if vector.get("regression") == "INTRODUCED_FAILURE":
        labels.append("INTRODUCED_REGRESSION")
    if vector.get("typecheck") == "FAIL":
        labels.append("TYPECHECK_FAILURE")
    if vector.get("lint") == "FAIL":
        labels.append("LINT_REGRESSION")
    if vector.get("architecture") == "FAIL":
        labels.append("ARCHITECTURE_POLICY_FAILURE")
    if vector.get("security") == "FAIL":
        labels.append("SECURITY_EVALUATOR_FAILURE")
    extras = evaluation.get("results") or []
    for result in extras:
        if result.get("timeout"):
            labels.append("TIMEOUT")
        if result.get("verdict") == "RESOURCE":
            labels.append("RESOURCE_LIMIT")
    if (task.get("error_count") or 0) > 0:
        labels.append("TOOL_ERROR")
    if not labels and task.get("lifecycle_state") == "UNKNOWN":
        labels.append("UNKNOWN")
    return sorted(set(labels))


def taxonomy(members: list[dict[str, Any]], tier_config: dict[str, Any]) -> list[dict[str, Any]]:
    population_n = len(members)
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for row in members:
        tagged = labels_for(row)
        row["failure_labels"] = tagged
        for label in tagged:
            counts[label] += 1
            examples.setdefault(label, [])
            ident = f"{row['board']}:{row['task_id']}"
            if ident not in examples[label] and len(examples[label]) < 5:
                examples[label].append(ident)
    rows = []
    for label, count in sorted(counts.items()):
        lo, hi = wilson_interval(count, population_n) if population_n else (None, None)
        rows.append(
            {
                "label": label,
                "count": count,
                "population_n": population_n,
                "known_n": population_n,
                "unknown_n": 0,
                "coverage": coverage_ratio(population_n, population_n),
                "value": proportion(count, population_n),
                "uncertainty": {"method": "wilson", "interval_low": lo, "interval_high": hi},
                "evidence_tier": classify_tier(population_n, tier_config),
                "examples": examples.get(label) or [],
            }
        )
    return rows
