"""Phase 5 performance contract. Derived, observational, fail-open, never mutates Hermes."""

from __future__ import annotations

CONTRACT_VERSION = "phase5-perf-v1"
ADVISORY_LOCK_KEY = 520260827
ANALYTICS_LOCK_KEY = 320260827
EVALUATION_LOCK_KEY = 420260827
TIER_CONFIG_VERSION = "phase5-tiers-v1"
COHORT_CONFIG_VERSION = "phase5-cohorts-v1"
METRIC_CONFIG_VERSION = "phase5-metrics-v1"
COMPARISON_CONFIG_VERSION = "phase5-comparisons-v1"

INTERPRETATIONS = (
    "INSUFFICIENT_DATA",
    "NO_CLEAR_DIFFERENCE",
    "OBSERVED_DIFFERENCE",
    "CONFOUNDED",
    "NOT_COMPARABLE",
)

EVIDENCE_TIERS = (
    "NO_DATA",
    "INSUFFICIENT",
    "EXPLORATORY",
    "PROVISIONAL",
    "SUPPORTED",
)

ATTRIBUTION_TYPES = (
    "SINGLE_MODEL",
    "MIXED_MODEL",
    "UNKNOWN",
    "SINGLE_SKILL",
    "MULTI_SKILL",
    "NO_SKILL",
)
