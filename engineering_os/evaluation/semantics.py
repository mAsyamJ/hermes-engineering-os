"""phase4-eval-v1 vocabulary."""

from __future__ import annotations

ELIGIBILITY = (
    "ELIGIBLE",
    "TEST_ELIGIBLE",
    "INSUFFICIENT_EVIDENCE",
    "NOT_APPLICABLE",
    "EXCLUDED",
)

EXECUTION = (
    "PENDING",
    "RUNNING",
    "COMPLETE",
    "PARTIAL",
    "ERROR",
    "STALE",
    "LOCKED",
)

VERDICTS = (
    "PASS",
    "FAIL",
    "WARN",
    "UNKNOWN",
    "NOT_APPLICABLE",
    "BLOCKED_AUTH",
    "BLOCKED_RESOURCE",
    "BLOCKED_ENVIRONMENT",
    "ERROR",
)

COMPARISONS = (
    "UNCHANGED_PASS",
    "INTRODUCED_FAILURE",
    "FIXED_FAILURE",
    "UNCHANGED_FAILURE",
    "UNKNOWN",
)

SUMMARY_STATES = (
    "VERIFIED_PASS",
    "VERIFIED_FAIL",
    "PARTIAL",
    "INSUFFICIENT_EVIDENCE",
    "ERROR",
)

DIMENSIONS = (
    "correctness",
    "build",
    "tests",
    "regression",
    "lint",
    "typecheck",
    "security",
    "architecture",
    "scope",
    "acceptance",
    "ci",
)

FAIL_LIKE = {"FAIL", "ERROR"}
PASS_LIKE = {"PASS"}
NON_RESULT = {"UNKNOWN", "NOT_APPLICABLE", "BLOCKED_AUTH", "BLOCKED_RESOURCE", "BLOCKED_ENVIRONMENT", "ERROR"}
