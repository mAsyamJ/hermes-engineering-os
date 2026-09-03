"""Missing-skill resolver — discover/inspect/rank; install only per trust policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from agent_os import POLICIES_DIR


@dataclass
class ResolveOutcome:
    capability: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    installed: list[str] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    action: str = "none"
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_trust_policy() -> dict[str, Any]:
    path = POLICIES_DIR / "trust-policy.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def map_hermes_trust(level: str, policy: dict[str, Any] | None = None) -> str:
    policy = policy or load_trust_policy()
    return (policy.get("hermes_trust_map") or {}).get(level, "T3")


def decide_auto_install(trust_tier: str, scan_allowed: bool | None, policy: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Return (may_install, reason). Never allows force."""
    policy = policy or load_trust_policy()
    tiers = policy.get("tiers") or {}
    t = tiers.get(trust_tier) or {}
    if trust_tier == "T4":
        return False, "T4 rejected/dangerous — never install"
    if not t.get("auto_install"):
        if trust_tier == "T3":
            return False, "T3 community — auto-install disabled"
        if t.get("auto_install") is False:
            return False, f"{trust_tier} auto-install disabled"
    if t.get("auto_install") == "only_if_allowlisted_and_scan_allows":
        if scan_allowed is not True:
            return False, "T2 requires allowlist + native scan allow (not ask/block)"
        return True, "T2 allowlisted and scan allowed"
    if t.get("auto_install") is True:
        if scan_allowed is False:
            return False, f"{trust_tier} blocked by scan"
        if scan_allowed is None and trust_tier in {"T0", "T1"}:
            return True, f"{trust_tier} local/official — install permitted when safe"
        if scan_allowed is True:
            return True, f"{trust_tier} scan allowed"
        return False, f"{trust_tier} scan inconclusive — not auto-installing"
    return False, "policy deny"


def resolve_missing_capability(
    capability: str,
    *,
    registry_skills: list[dict[str, Any]],
    search_results: list[dict[str, Any]] | None = None,
    allowlisted_repos: set[str] | None = None,
    scan_fn=None,
) -> ResolveOutcome:
    """Pure-ish resolver.

    search_results: optional list of hub hits with keys name, identifier, trust_level, source, repository
    scan_fn: optional callable(identifier) -> bool | None  (True allow, False block, None ask)
    """
    policy = load_trust_policy()
    allowlisted_repos = allowlisted_repos or set()
    out = ResolveOutcome(capability=capability)

    # Local registry candidates
    for e in registry_skills:
        caps = e.get("capabilities") or []
        if capability not in caps:
            continue
        if e.get("install_state") == "installed":
            out.installed.append(e["skill_id"])
        else:
            out.candidates.append(
                {
                    "skill_id": e["skill_id"],
                    "repository": e.get("repository", ""),
                    "trust_tier": e.get("trust_tier", "T3"),
                    "origin": "registry",
                }
            )

    for hit in search_results or []:
        trust_level = hit.get("trust_level") or hit.get("trust") or "community"
        tier = map_hermes_trust(str(trust_level), policy)
        repo = hit.get("repository") or hit.get("repo") or ""
        if tier == "T2" and repo and repo not in allowlisted_repos:
            # curated only if allowlisted
            if hit.get("source") not in {"official", "builtin"}:
                tier = "T3"
        cand = {
            "skill_id": hit.get("name") or hit.get("identifier"),
            "identifier": hit.get("identifier"),
            "repository": repo,
            "trust_tier": tier,
            "origin": "hub_search",
        }
        out.candidates.append(cand)

    if out.installed:
        out.action = "already_installed"
        out.explanation = f"Capability {capability} covered by {out.installed}"
        return out

    if not out.candidates:
        out.action = "not_found"
        out.explanation = f"No candidates for capability {capability}"
        return out

    # Rank: T0/T1/T2 before T3; skip T4
    rank = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 9}
    out.candidates.sort(key=lambda c: (rank.get(c.get("trust_tier", "T3"), 5), c.get("skill_id") or ""))

    for cand in out.candidates:
        tier = cand.get("trust_tier", "T3")
        if tier == "T4":
            out.rejected.append({"skill_id": str(cand.get("skill_id")), "reason": "T4"})
            continue
        scan_allowed: bool | None
        if scan_fn and cand.get("identifier"):
            scan_allowed = scan_fn(cand["identifier"])
        elif tier in {"T0", "T1"}:
            scan_allowed = True
        else:
            scan_allowed = None
        ok, reason = decide_auto_install(tier, scan_allowed, policy)
        if ok:
            out.action = "would_install"
            out.explanation = f"Would install {cand.get('identifier') or cand.get('skill_id')}: {reason}"
            return out
        out.rejected.append({"skill_id": str(cand.get("skill_id")), "reason": reason})

    out.action = "refused"
    out.explanation = (
        f"No safe auto-install for {capability}. "
        f"Rejected={len(out.rejected)}. Discover/inspect/rank only for T3+."
    )
    return out


def hub_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Best-effort structured search via hermes skills search --json."""
    import json
    import subprocess

    try:
        proc = subprocess.run(
            ["hermes", "skills", "search", query, "--json", "--limit", str(limit)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [{"error": str(exc)}]
    if proc.returncode != 0:
        return []
    raw = proc.stdout.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return list(data["results"])
    if isinstance(data, dict) and "items" in data:
        return list(data["items"])
    return []
