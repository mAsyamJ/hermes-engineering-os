"""agent-os-router Hermes plugin — compact routing hints + resolve tools."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("agent_os.plugin")

# Repo root on sys.path so `import agent_os` works when loaded from symlink.
_PLUGIN_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PLUGIN_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_registry_skills():
    from agent_os import REGISTRY_DIR

    path = REGISTRY_DIR / "skills.registry.json"
    if not path.exists():
        from agent_os.generate import regenerate

        regenerate(write_hermes_projection=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("skills") or []


def _stamp_otel(attrs: dict) -> None:
    """Fail-open attribute stamp onto hermes_otel current span if present."""
    try:
        tracer_mod = sys.modules.get("hermes_plugins.hermes_otel.tracer")
        if tracer_mod is None:
            return
        tracer = getattr(tracer_mod, "tracer", None)
        if tracer is None or not getattr(tracer, "is_enabled", False):
            return
        span = None
        get_span = getattr(tracer, "get_current_span", None)
        if callable(get_span):
            span = get_span()
        if span is None:
            return
        for k, v in attrs.items():
            try:
                span.set_attribute(f"hermes.agent_os.{k}", v)
            except Exception:
                return
    except Exception:
        return


def _on_pre_llm_call(user_message="", is_first_turn=False, **kwargs):
    try:
        from agent_os.router import format_routing_context, route_task

        skills = _load_registry_skills()
        # Prefer installed + virtual capability seeds for routing
        result = route_task(user_message or "", skills)
        ctx = format_routing_context(result, task_preview=(user_message or "")[:80])
        result.context_chars = len(ctx)
        _stamp_otel(
            {
                "selected": ",".join(result.selected),
                "missing": ",".join(result.missing_capabilities),
                "confidence": result.confidence,
                "context_chars": result.context_chars,
                "risk": result.classification.get("risk_class", ""),
            }
        )
        # Only inject when we have a signal — keep ordinary turns light
        if not result.selected and not result.missing_capabilities and result.confidence < 0.3:
            return None
        return {"context": ctx}
    except Exception:
        logger.exception("agent-os-router pre_llm_call failed (fail-open)")
        return None


def _on_skill_lifecycle(action="", skill_name="", **kwargs):
    try:
        from agent_os.lifecycle import mark_dirty, regenerate_if_dirty

        mark_dirty(reason=f"{action}:{skill_name}")
        regenerate_if_dirty()
        _stamp_otel({"lifecycle_action": str(action), "lifecycle_skill": str(skill_name)})
    except Exception:
        logger.exception("agent-os-router on_skill_lifecycle failed (fail-open)")


def _tool_resolve_skill(args=None, **kwargs):
    args = args or {}
    task = args.get("task") or args.get("query") or ""
    from agent_os.router import route_task

    skills = _load_registry_skills()
    result = route_task(task, skills)
    return json.dumps(result.to_dict(), indent=2)


def _tool_skill_search(args=None, **kwargs):
    args = args or {}
    capability = args.get("capability") or args.get("query") or ""
    from agent_os.resolver import hub_search, resolve_missing_capability
    from agent_os.registry.sources_util import allowlisted_repos

    skills = _load_registry_skills()
    hits = hub_search(capability, limit=10)

    def scan_fn(_ident: str):
        # Never claim allow without native guard — return None => ask/no auto
        return None

    outcome = resolve_missing_capability(
        capability,
        registry_skills=skills,
        search_results=hits if hits and "error" not in (hits[0] or {}) else [],
        allowlisted_repos=allowlisted_repos(),
        scan_fn=scan_fn,
    )
    return json.dumps(outcome.to_dict(), indent=2)


RESOLVE_SCHEMA = {
    "name": "agent_os_resolve_skill",
    "description": "Deterministically rank Hermes skills/capabilities for a task. Returns selected, supporting, rejected, missing_capabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "User task or capability request"},
        },
        "required": ["task"],
    },
}

SEARCH_SCHEMA = {
    "name": "agent_os_skill_search",
    "description": "Search for missing capabilities via Agent OS resolver + Hermes hub. Does not force-install community skills.",
    "parameters": {
        "type": "object",
        "properties": {
            "capability": {"type": "string", "description": "Capability or search query"},
        },
        "required": ["capability"],
    },
}


def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("on_skill_lifecycle", _on_skill_lifecycle)
    ctx.register_tool(
        name="agent_os_resolve_skill",
        toolset="agent-os-router",
        schema=RESOLVE_SCHEMA,
        handler=_tool_resolve_skill,
    )
    ctx.register_tool(
        name="agent_os_skill_search",
        toolset="agent-os-router",
        schema=SEARCH_SCHEMA,
        handler=_tool_skill_search,
    )

    def _setup_agent_os(subparser):
        sub = subparser.add_subparsers(dest="agent_os_action")
        regen = sub.add_parser("regenerate", help="Regenerate registry + SKILLS.md")
        regen.set_defaults(func=_cli_regenerate)

    def _cli_regenerate(args):
        from agent_os.generate import regenerate

        evidence = regenerate(write_hermes_projection=True)
        print(json.dumps(evidence, indent=2))

    try:
        ctx.register_cli_command(
            "agent-os",
            help="Hermes Agent OS capability control plane",
            setup_fn=_setup_agent_os,
            handler_fn=_cli_regenerate,
            description="Regenerate Agent OS registry and ~/.hermes/SKILLS.md",
        )
    except Exception:
        logger.warning("register_cli_command unavailable", exc_info=True)

    logger.info("agent-os-router registered")
