"""Configurable evidence-tier classification. Presentation rules, not scientific law."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.performance import EVIDENCE_TIERS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "config" / "performance-evidence-tiers.yaml"

TIER_RANK = {name: index for index, name in enumerate(EVIDENCE_TIERS)}


def load_tiers(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_PATH
    text = target.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required to load evidence-tier config") from None
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("performance-evidence-tiers.yaml must be a mapping")
    return data


def classify_tier(known_n: int, config: dict[str, Any] | None = None) -> str:
    if known_n < 0:
        raise ValueError("known_n must be >= 0")
    cfg = config or load_tiers()
    if known_n == 0:
        return "NO_DATA"
    tiers = cfg.get("tiers") or {}
    for name in ("INSUFFICIENT", "EXPLORATORY", "PROVISIONAL", "SUPPORTED"):
        spec = tiers.get(name) or {}
        lo = int(spec.get("min_known_n", 0))
        hi = spec.get("max_known_n")
        if known_n >= lo and (hi is None or known_n <= int(hi)):
            return name
    return "SUPPORTED"


def tier_at_least(tier: str, minimum: str) -> bool:
    return TIER_RANK.get(tier, -1) >= TIER_RANK.get(minimum, 99)
