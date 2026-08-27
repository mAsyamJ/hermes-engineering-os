"""Read-only Phoenix GraphQL client. Fail-open, no credentials, no DB tables."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

PHOENIX_BASE = "http://127.0.0.1:6006"
PROJECT_NAME = "hermes-agent"

KANBAN_KEYS = (
    "hermes.kanban.task_id",
    "hermes.kanban.run_id",
    "hermes.kanban.board",
    "hermes.kanban.workspace",
)
INTEREST_KEYS = KANBAN_KEYS + (
    "hermes.session.id",
    "session.id",
    "llm.model_name",
    "llm.provider",
    "tool.name",
    "gen_ai.tool.call.id",
    "openinference.project.name",
)


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                out.update(_flatten(value, next_key))
            else:
                out[next_key] = value
    elif prefix:
        out[prefix] = obj
    return out


def graphql(query: str, variables: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    request = urllib.request.Request(
        f"{PHOENIX_BASE}/graphql",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode())
    if body.get("errors"):
        raise RuntimeError(str(body["errors"]))
    return body.get("data") or {}


def ui_reachable(timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen(f"{PHOENIX_BASE}/", timeout=timeout)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def project_id(name: str = PROJECT_NAME) -> str | None:
    data = graphql("query { projects(first: 50) { edges { node { id name } } } }")
    for edge in ((data.get("projects") or {}).get("edges") or []):
        node = edge.get("node") or {}
        if node.get("name") == name:
            return str(node["id"])
    edges = ((data.get("projects") or {}).get("edges") or [])
    if edges:
        return str((edges[0].get("node") or {}).get("id") or "") or None
    return None


def _parse_attrs(raw: Any) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    if isinstance(raw, str) and raw:
        try:
            attrs = _flatten(json.loads(raw))
        except json.JSONDecodeError:
            attrs = {}
    elif isinstance(raw, dict):
        attrs = _flatten(raw)
    return attrs


def _pick(attrs: dict[str, Any]) -> dict[str, Any]:
    picked: dict[str, Any] = {}
    for key in INTEREST_KEYS:
        if key in attrs:
            picked[key] = attrs[key]
            continue
        resource_key = f"resource.{key}"
        if resource_key in attrs:
            picked[key] = attrs[resource_key]
    return picked


def _nodes(project: str, limit: int, filter_condition: str | None = None) -> list[dict[str, Any]]:
    data = graphql(
        """
        query ProjectSpans($projectId: ID!, $first: Int!, $filterCondition: String) {
          node(id: $projectId) {
            ... on Project {
              spans(
                first: $first,
                sort: { col: startTime, dir: desc },
                filterCondition: $filterCondition
              ) {
                edges {
                  node {
                    name
                    parentId
                    startTime
                    endTime
                    latencyMs
                    statusCode
                    attributes
                    context { traceId spanId }
                  }
                }
              }
            }
          }
        }
        """,
        {
            "projectId": project,
            "first": limit,
            "filterCondition": filter_condition,
        },
    )
    edges = (((data.get("node") or {}).get("spans") or {}).get("edges") or [])
    result = []
    for edge in edges:
        node = edge.get("node")
        if not node:
            continue
        attrs = _parse_attrs(node.get("attributes"))
        context = node.get("context") or {}
        result.append(
            {
                "name": node.get("name"),
                "parent_id": node.get("parentId"),
                "start_time": node.get("startTime"),
                "end_time": node.get("endTime"),
                "latency_ms": node.get("latencyMs"),
                "status_code": node.get("statusCode"),
                "trace_id": context.get("traceId"),
                "span_id": context.get("spanId") or context.get("spanID"),
                "attributes": _pick(attrs),
                "raw_attributes": attrs,
            }
        )
    return result


def _rows_from_nodes(nodes: list[dict[str, Any]], project: str, limit: int) -> list[dict[str, Any]]:
    by_trace: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        trace_id = node.get("trace_id")
        if not trace_id:
            continue
        by_trace.setdefault(str(trace_id), []).append(node)
    rows = []
    for trace_id, spans in by_trace.items():
        attrs: dict[str, Any] = {}
        for span in spans:
            attrs.update(span.get("attributes") or {})
        names = [str(span.get("name") or "") for span in spans]
        duration = max((span.get("latency_ms") or 0) for span in spans)
        rows.append(
            {
                "trace_id": trace_id,
                "hermes_kanban_task_id": attrs.get("hermes.kanban.task_id"),
                "hermes_kanban_run_id": attrs.get("hermes.kanban.run_id"),
                "hermes_kanban_board": attrs.get("hermes.kanban.board"),
                "session_id": attrs.get("hermes.session.id") or attrs.get("session.id"),
                "runtime_task_id": attrs.get("gen_ai.tool.call.id"),
                "model": attrs.get("llm.model_name"),
                "provider": attrs.get("llm.provider"),
                "agent": "hermes-agent",
                "duration_ms": duration,
                "llm_calls": sum(
                    1 for name in names if name.startswith("llm.") or name.startswith("api.")
                ),
                "tool_calls": sum(1 for name in names if name.startswith("tool.")),
                "span_count": len(spans),
                "phoenix_url": f"{PHOENIX_BASE}/projects/{project}/traces/{trace_id}",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def summarize_traces(limit: int = 20) -> list[dict[str, Any]]:
    ident = project_id()
    if not ident:
        return []
    return _rows_from_nodes(_nodes(ident, max(limit * 8, 40)), ident, limit)


def traces_for_attr(attr: str, value: str, limit: int = 20) -> list[dict[str, Any]]:
    ident = project_id()
    if not ident or not value:
        return []
    escaped = value.replace("'", "\\'")
    nodes: list[dict[str, Any]] = []
    try:
        nodes = _nodes(ident, 80, f"{attr} == '{escaped}'")
    except Exception:
        nodes = []
    if not nodes:
        nodes = [
            node
            for node in _nodes(ident, 120)
            if str((node.get("attributes") or {}).get(attr)) == value
            or str((node.get("raw_attributes") or {}).get(attr)) == value
        ]
    return _rows_from_nodes(nodes, ident, limit)


def traces_for_task(task_id: str) -> list[dict[str, Any]]:
    return traces_for_attr("hermes.kanban.task_id", task_id)


def traces_for_run(run_id: str) -> list[dict[str, Any]]:
    return traces_for_attr("hermes.kanban.run_id", str(run_id))
