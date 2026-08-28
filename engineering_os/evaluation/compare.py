"""Baseline vs candidate classifications. Raw verdicts are never erased."""

from __future__ import annotations


def classify(baseline_verdict: str | None, candidate_verdict: str | None) -> str:
    baseline = _norm(baseline_verdict)
    candidate = _norm(candidate_verdict)
    if baseline is None or candidate is None:
        return "UNKNOWN"
    if baseline == "PASS" and candidate == "PASS":
        return "UNCHANGED_PASS"
    if baseline == "PASS" and candidate == "FAIL":
        return "INTRODUCED_FAILURE"
    if baseline == "FAIL" and candidate == "PASS":
        return "FIXED_FAILURE"
    if baseline == "FAIL" and candidate == "FAIL":
        return "UNCHANGED_FAILURE"
    return "UNKNOWN"


def _norm(value: str | None) -> str | None:
    if value in {"PASS", "FAIL"}:
        return value
    return None
