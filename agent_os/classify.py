"""Deterministic task classifier — rules/keywords first, no LLM required."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskClassification:
    domain: list[str] = field(default_factory=list)
    task_type: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    stage: str = "unknown"
    risk_class: str = "low"
    required_capabilities: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)


_RULES: list[tuple[re.Pattern[str], dict[str, Any]]] = [
    (
        re.compile(r"solidity|smart\s*contract|reentrancy|escrow\s+contract", re.I),
        {
            "domain": ["solidity", "security", "web3"],
            "task_type": ["audit", "security-review"],
            "risk": "critical",
            "capabilities": ["solidity-audit", "web3-testing"],
        },
    ),
    (
        re.compile(r"\bmonad\b|payment\s+escrow\s+on\s+monad", re.I),
        {
            "domain": ["monad", "web3", "solidity"],
            "task_type": ["build", "implement"],
            "risk": "high",
            "capabilities": ["monad-routing", "monad-implementation", "web3-testing", "solidity-audit"],
        },
    ),
    (
        re.compile(r"ai\s+engineering|math\s+foundations|transformers?\b|backprop", re.I),
        {
            "domain": ["ai-engineering", "math"],
            "task_type": ["learn", "teach"],
            "risk": "low",
            "capabilities": ["ai-engineering"],
        },
    ),
    (
        re.compile(r"jobs?\s+to\s+be\s+done|\bjtbd\b|interview\s+transcript", re.I),
        {
            "domain": ["product", "research"],
            "task_type": ["research", "discovery"],
            "risk": "low",
            "capabilities": ["jtbd"],
        },
    ),
    (
        re.compile(r"fatal\s+assumption|test(?:ing)?\s+business\s+ideas?|startup\s+idea", re.I),
        {
            "domain": ["startup", "validation"],
            "task_type": ["validate"],
            "risk": "medium",
            "capabilities": ["assumption-testing", "adversarial-review"],
        },
    ),
    (
        re.compile(r"hackathon\s+pitch|memorable\s+pitch|pitch\s+deck", re.I),
        {
            "domain": ["pitch", "hackathon"],
            "task_type": ["pitch"],
            "risk": "low",
            "capabilities": ["pitch-storytelling"],
        },
    ),
    (
        re.compile(r"next\.?js|production\s+frontend", re.I),
        {
            "domain": ["frontend"],
            "task_type": ["optimize", "build"],
            "risk": "medium",
            "capabilities": ["frontend-nextjs"],
        },
    ),
    (
        re.compile(r"\btemporal\b.*workflow|temporal\.io", re.I),
        {
            "domain": ["backend"],
            "task_type": ["setup"],
            "risk": "medium",
            "capabilities": ["temporal-workflows"],
        },
    ),
    (
        re.compile(r"\bgrill\b|adversarial\s+review|judge\s+sim", re.I),
        {
            "domain": ["startup", "review"],
            "task_type": ["review"],
            "risk": "medium",
            "capabilities": ["adversarial-review"],
        },
    ),
]


def classify_task(text: str) -> TaskClassification:
    tc = TaskClassification()
    tc.tokens = re.findall(r"[a-zA-Z0-9_+#.-]+", text.lower())
    matched = 0
    for pattern, rule in _RULES:
        if pattern.search(text):
            matched += 1
            for d in rule.get("domain", []):
                if d not in tc.domain:
                    tc.domain.append(d)
            for t in rule.get("task_type", []):
                if t not in tc.task_type:
                    tc.task_type.append(t)
            for c in rule.get("capabilities", []):
                if c not in tc.required_capabilities:
                    tc.required_capabilities.append(c)
            risk = rule.get("risk", "low")
            order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            if order.get(risk, 0) > order.get(tc.risk_class, 0):
                tc.risk_class = risk
    if matched >= 2:
        tc.stage = "multi-domain"
    elif matched == 1:
        tc.stage = "focused"
    else:
        tc.stage = "ambiguous"
        # weak fallbacks
        if "deploy" in tc.tokens:
            tc.required_capabilities.append("devops-deploy")
            tc.domain.append("devops")
    # Entity hints
    for ent in ("solidity", "monad", "next.js", "nextjs", "temporal", "jtbd"):
        if ent.replace(".", "") in text.lower().replace(".", "") or ent in text.lower():
            if ent not in tc.entities:
                tc.entities.append(ent)
    return tc
