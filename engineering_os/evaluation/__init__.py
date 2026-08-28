"""Phase 4 evaluation contract. Derived, fail-open, never mutates Hermes."""

from __future__ import annotations

CONTRACT_VERSION = "phase4-eval-v1"
ADVISORY_LOCK_KEY = 420260827
SANDBOX_IMAGE = "hermes-eos-analytics:phase3"
SANDBOX_IMAGE_ID = "sha256:6a01af80fa2d7147f5857dfe93ac2fd347fb091a6de051d2f5c689e768392702"
ARTIFACT_ROOT = "/var/lib/hermes-engineering-os/evaluation-artifacts"
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ARTIFACT_BYTES = 80 * 1024 * 1024
LOG_LIMIT_BYTES = 8 * 1024
