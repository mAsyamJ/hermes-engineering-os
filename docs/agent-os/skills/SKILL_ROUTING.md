# Skill Routing

See [ADR-HERMES-AGENT-OS.md](../../architecture/decisions/ADR-HERMES-AGENT-OS.md).

## Pipeline

1. `classify_task` — keyword/regex → domain, task_type, risk, required_capabilities.
2. `route_task` — score registry entries (capability, domain, triggers, negative triggers, trust, specificity, install state).
3. Result: `selected`, `supporting`, `rejected`, `missing_capabilities`, `confidence`, `reason_codes`.
4. `format_routing_context` — compact card injected via `pre_llm_call` (user message), budget **2000** chars.
5. Progressive load — Hermes native `skills_list` / `skill_view` remain the body loaders. Agent OS does **not** dump SKILL.md bodies.

## Evaluation

`tests/python/test_agent_os_router.py` covers the ten acceptance cases (audit, Monad, AI math, JTBD, assumptions, pitch, Next.js, Temporal missing/T3 refuse, multi-domain bound, malicious/T4).
