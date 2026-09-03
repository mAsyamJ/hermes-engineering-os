"""Deterministic capability → skill router with progressive disclosure hints."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from agent_os import CONTEXT_BUDGET_CHARS
from agent_os.classify import TaskClassification, classify_task
from agent_os.schema import flatten_value


@dataclass
class RouteResult:
    selected: list[str] = field(default_factory=list)
    supporting: list[str] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason_codes: list[str] = field(default_factory=list)
    classification: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    context_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cap_list(entry: dict[str, Any]) -> list[str]:
    caps = flatten_value(entry.get("capabilities", []))
    if isinstance(caps, list):
        return [str(c) for c in caps]
    return []


def _str_list(entry: dict[str, Any], key: str) -> list[str]:
    val = flatten_value(entry.get(key, []))
    if isinstance(val, list):
        return [str(x).lower() for x in val]
    if isinstance(val, str) and val:
        return [val.lower()]
    return []


def score_skill(entry: dict[str, Any], tc: TaskClassification) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    caps = set(_cap_list(entry))
    req = set(tc.required_capabilities)
    overlap = caps & req
    if overlap:
        score += 10.0 * len(overlap)
        reasons.append(f"capability_match:{','.join(sorted(overlap))}")
    # domain
    domains = set(_str_list(entry, "domains"))
    for d in tc.domain:
        if d.lower() in domains:
            score += 3.0
            reasons.append(f"domain:{d}")
    # triggers
    text_blob = " ".join(tc.tokens)
    full_text = " ".join(tc.tokens)
    for trig in _str_list(entry, "triggers"):
        if trig and trig in text_blob:
            score += 4.0
            reasons.append(f"trigger:{trig}")
    for neg in _str_list(entry, "negative_triggers"):
        if not neg:
            continue
        # Phrase match against full token blob only (avoid short-token false positives like "a" in "branding")
        if neg in full_text or all(part in tc.tokens for part in neg.split() if len(part) > 2):
            # Require multi-word negatives to match as phrase; single-word negatives must equal a token
            if " " in neg:
                if neg in full_text:
                    score -= 8.0
                    reasons.append(f"negative_trigger:{neg}")
            elif neg in tc.tokens:
                score -= 8.0
                reasons.append(f"negative_trigger:{neg}")
    # trust
    tier = flatten_value(entry.get("trust_tier", "T3"))
    tier_bonus = {"T0": 2.0, "T1": 1.5, "T2": 1.0, "T3": 0.0, "T4": -100.0}
    score += tier_bonus.get(str(tier), 0.0)
    if str(tier) == "T4":
        reasons.append("rejected_tier_T4")
    # specificity: prefer fewer capabilities when overlap exists
    if overlap and len(caps) <= 3:
        score += 1.5
        reasons.append("specificity")
    # install state
    install = flatten_value(entry.get("install_state", "unknown"))
    if install != "installed":
        score -= 0.5  # still rank for missing path
        reasons.append("not_installed")
    # penalize branding when audit
    name = str(flatten_value(entry.get("skill_id", ""))).lower()
    if "audit" in tc.task_type or "solidity-audit" in req:
        if any(x in name for x in ("pitch", "brand", "marketing", "design")):
            score -= 12.0
            reasons.append("irrelevant_marketing")
    if "ai-engineering" in req and any(x in name for x in ("solidity", "monad", "web3")):
        score -= 12.0
        reasons.append("irrelevant_web3")
    return score, reasons


def route_task(
    text: str,
    registry_skills: list[dict[str, Any]],
    *,
    max_selected: int = 3,
    max_supporting: int = 2,
) -> RouteResult:
    tc = classify_task(text)
    result = RouteResult(
        classification={
            "domain": tc.domain,
            "task_type": tc.task_type,
            "risk_class": tc.risk_class,
            "required_capabilities": tc.required_capabilities,
            "stage": tc.stage,
            "entities": tc.entities,
        }
    )
    if not tc.required_capabilities:
        result.confidence = 0.2
        result.reason_codes.append("no_capability_signal")
        return result

    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    for entry in registry_skills:
        s, reasons = score_skill(entry, tc)
        sid = str(flatten_value(entry.get("skill_id", "")))
        result.scores[sid] = s
        if s > 0:
            scored.append((s, entry, reasons))
        elif any(r.startswith("negative") or r.startswith("irrelevant") or r.startswith("rejected") for r in reasons):
            result.rejected.append({"skill_id": sid, "reason": ",".join(reasons[:3])})

    scored.sort(
        key=lambda x: (
            0 if flatten_value(x[1].get("install_state")) == "installed" else 1,
            -x[0],
            str(flatten_value(x[1].get("skill_id", ""))),
        )
    )

    # Cover required capabilities greedily with installed skills first
    remaining = set(tc.required_capabilities)
    selected: list[str] = []
    supporting: list[str] = []
    for s, entry, reasons in scored:
        sid = str(flatten_value(entry.get("skill_id")))
        caps = set(_cap_list(entry))
        install = flatten_value(entry.get("install_state"))
        if not (caps & remaining) and selected:
            # supporting if related and installed
            if install == "installed" and caps & set(tc.required_capabilities) and len(supporting) < max_supporting:
                if sid not in selected and sid not in supporting:
                    supporting.append(sid)
                    result.reason_codes.append(f"supporting:{sid}")
            continue
        if caps & remaining or (not selected and s >= 5):
            if install == "installed":
                if sid not in selected and len(selected) < max_selected:
                    selected.append(sid)
                    remaining -= caps
                    result.reason_codes.extend(reasons[:4])
            else:
                # missing — track capability only if no installed skill already covered it
                still = caps & remaining
                for c in still:
                    if c not in result.missing_capabilities:
                        result.missing_capabilities.append(c)
                # Do not drop remaining for virtual seeds when install_state is virtual
                if install != "virtual":
                    remaining -= caps
                result.reason_codes.append(f"missing_skill:{sid}")

    # Any required capability never covered
    for c in remaining:
        if c not in result.missing_capabilities:
            result.missing_capabilities.append(c)
            result.reason_codes.append(f"uncovered:{c}")

    # Avoid loading ten unrelated skills on multi-domain: keep max_selected
    result.selected = selected
    result.supporting = supporting
    req = set(tc.required_capabilities)
    accounted: set[str] = set(result.missing_capabilities)
    by_id = {
        str(flatten_value(e.get("skill_id"))): e
        for e in registry_skills
    }
    for sid in selected + supporting:
        accounted |= set(_cap_list(by_id.get(sid, {})))
    coverage = len(accounted & req) / max(1, len(req))
    # Correctly identifying missing capabilities still counts as high-confidence routing
    result.confidence = round(min(1.0, 0.35 + 0.65 * coverage + (0.1 if selected else 0.0)), 3)
    return result


def format_routing_context(result: RouteResult, task_preview: str = "") -> str:
    lines = [
        "Agent OS capability routing:",
        f"Task: {(task_preview or 'see user message')[:120]}",
        f"Recommended: {', '.join(result.selected) or '(none installed)'}",
    ]
    if result.supporting:
        lines.append(f"Supporting: {', '.join(result.supporting)}")
    risk = result.classification.get("risk_class", "low")
    lines.append(f"Risk: {risk}")
    missing = result.missing_capabilities
    lines.append(f"Missing capabilities: {', '.join(missing) if missing else 'none'}")
    lines.append("Load exact skills before implementation.")
    if result.reason_codes[:3]:
        lines.append(f"Reasons: {'; '.join(result.reason_codes[:3])}")
    text = "\n".join(lines)
    if len(text) > CONTEXT_BUDGET_CHARS:
        text = text[: CONTEXT_BUDGET_CHARS - 20] + "\n…[truncated]"
    return text
