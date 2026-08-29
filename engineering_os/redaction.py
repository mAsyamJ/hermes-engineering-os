"""Conservative secret redaction for evidence returned to the browser."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEY = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|cookie|credential)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9]{16,})"
)
# Public enum cells whose names contain otherwise-secret substrings.
_PUBLIC_STATUS_KEYS = frozenset(
    {
        "budget_authorization",
        "llm_budget",
    }
)


def redact(value: Any, key: str = "") -> Any:
    if key and key.lower() not in _PUBLIC_STATUS_KEYS and _SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return value

