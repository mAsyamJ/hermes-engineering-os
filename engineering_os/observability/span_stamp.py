"""Fail-open span attributes when Phoenix cannot filter resource attributes.

hermes-otel tracks spans in SpanTracker and does not attach them as the
OpenTelemetry current span. Engineering OS therefore stamps the explicit
Kanban identity onto active tracker spans from post_* hooks, which run
before hermes_otel ends those spans (engineering-os registers first).

The live tracer lives in ``hermes_plugins.hermes_otel.tracer``, not a
fresh ``hermes_otel`` import. Registered only when HERMES_KANBAN_* is
present so plugin preflight stays hook-free.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Mapping


def _live_get_tracer() -> Callable[[], Any] | None:
    for name, module in sys.modules.items():
        get_tracer = getattr(module, "get_tracer", None)
        if not callable(get_tracer):
            continue
        filename = (getattr(module, "__file__", "") or "").replace("\\", "/")
        if filename.endswith("/hermes_otel/tracer.py"):
            return get_tracer
    try:
        from hermes_otel.tracer import get_tracer

        return get_tracer
    except Exception:
        return None


def register_fail_open_stamps(ctx: Any, stamped: Mapping[str, str]) -> None:
    if not stamped:
        return

    def _stamp(**_kwargs: Any) -> None:
        try:
            getter = _live_get_tracer()
            if getter is None:
                return
            tracer = getter()
            spans = []
            session_id = _kwargs.get("session_id")
            parent = tracer.spans.get_current_parent(session_id)
            if parent is not None:
                spans.append(parent)
            active = getattr(tracer.spans, "_active_spans", {}) or {}
            spans.extend(active.values())
            seen: set[int] = set()
            for span in spans:
                ident = id(span)
                if ident in seen:
                    continue
                seen.add(ident)
                if not hasattr(span, "set_attribute"):
                    continue
                recording = getattr(span, "is_recording", None)
                if callable(recording) and not recording():
                    continue
                for key, value in stamped.items():
                    span.set_attribute(key, value)
        except Exception:
            return

    for name in (
        "on_session_start",
        "on_session_end",
        "post_llm_call",
        "post_api_request",
        "post_tool_call",
    ):
        try:
            ctx.register_hook(name, _stamp)
        except Exception:
            continue
