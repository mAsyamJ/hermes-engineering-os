"""Descriptive temporal windows. No automatic action."""

from __future__ import annotations

from typing import Any

from engineering_os.performance.compare import pairwise
from engineering_os.performance.metrics import compute_metric


def _ts(row: dict[str, Any]) -> int | None:
    for key in ("completed_at_source", "created_at_source", "started_at_source"):
        value = row.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def split_calendar(members: list[dict[str, Any]], days: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stamps = [(_ts(row), row) for row in members]
    known = [(ts, row) for ts, row in stamps if ts is not None]
    if not known:
        return [], []
    latest = max(ts for ts, _row in known)
    window = days * 86400
    # Source clocks are milliseconds in Kanban.
    if latest > 10_000_000_000:
        window *= 1000
    current = [row for ts, row in known if ts >= latest - window]
    prior = [row for ts, row in known if latest - 2 * window <= ts < latest - window]
    return current, prior


def split_rolling(members: list[dict[str, Any]], n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(members, key=lambda row: (_ts(row) is None, _ts(row) or 0, str(row.get("task_id"))))
    if len(ordered) < 2:
        return ordered, []
    current = ordered[-n:]
    prior = ordered[-2 * n : -n]
    return current, prior


def trend(
    members: list[dict[str, Any]],
    metric_id: str,
    *,
    cohort_id: str,
    tier_config: dict[str, Any],
    comparison_config: dict[str, Any],
    ruleset: str,
    eval_contract: str | None,
    mode: str,
    size: int,
) -> dict[str, Any]:
    if mode == "calendar":
        current, prior = split_calendar(members, size)
        window_label = f"calendar_{size}d"
    else:
        current, prior = split_rolling(members, size)
        window_label = f"rolling_{size}"
    current_agg = compute_metric(metric_id, current, tier_config)
    prior_agg = compute_metric(metric_id, prior, tier_config)
    compared = pairwise(
        f"prior:{window_label}",
        f"current:{window_label}",
        prior,
        current,
        metric_id,
        left_aggregate=prior_agg,
        right_aggregate=current_agg,
        tier_config=tier_config,
        comparison_config=comparison_config,
        left_ruleset=ruleset,
        right_ruleset=ruleset,
        left_eval_contract=eval_contract,
        right_eval_contract=eval_contract,
        stratifiers=[],
    )
    state = "INSUFFICIENT_DATA"
    if compared["interpretation"] == "INSUFFICIENT_DATA":
        state = "INSUFFICIENT_DATA"
    elif compared["interpretation"] in {"NO_CLEAR_DIFFERENCE", "CONFOUNDED", "NOT_COMPARABLE"}:
        state = "NO_CLEAR_SHIFT"
    elif compared["interpretation"] == "OBSERVED_DIFFERENCE":
        state = "OBSERVED_SHIFT"
    return {
        "cohort_id": cohort_id,
        "metric_id": metric_id,
        "window": window_label,
        "mode": mode,
        "current": current_agg,
        "previous": prior_agg,
        "delta": compared.get("absolute_difference"),
        "coverage": compared.get("coverage"),
        "left_tier": compared.get("left_tier"),
        "right_tier": compared.get("right_tier"),
        "state": state,
        "auto_action": False,
        "comparison": compared,
    }
