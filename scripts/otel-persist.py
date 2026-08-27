#!/usr/bin/env python3
"""Emit a known synthetic trace to persistent Phoenix and query it back."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

PROJECT = "hermes-agent"
BASE = "http://127.0.0.1:6006"


def graphql(query: str, variables: dict | None = None) -> dict:
    body = {"query": query}
    if variables is not None:
        body["variables"] = variables
    req = urllib.request.Request(
        f"{BASE}/graphql",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload.get("data") or {}


def emit(session_id: str) -> None:
    os.environ["OTEL_PROJECT_NAME"] = PROJECT
    sys.path.insert(0, "/opt/hermes-engineering-os/upstream/hermes-otel")
    import hermes_otel.tracer as tracer_mod
    from hermes_otel.hooks import (
        on_post_api_request,
        on_post_llm_call,
        on_pre_api_request,
        on_pre_llm_call,
        on_session_end,
        on_session_start,
    )
    from hermes_otel.tracer import HermesOTelPlugin

    plugin = HermesOTelPlugin()
    assert plugin._init_otlp(f"{BASE}/v1/traces", backend_name="Phoenix")
    tracer_mod._tracer = plugin
    try:
        on_session_start(session_id=session_id, model="gpt-4", platform="persist-test")
        on_pre_llm_call(
            session_id=session_id,
            user_message="persist",
            conversation_history=[],
            is_first_turn=True,
            model="gpt-4",
            platform="persist-test",
        )
        on_pre_api_request(
            task_id=f"api-{session_id}",
            session_id=session_id,
            platform="persist-test",
            model="gpt-4",
            provider="openai",
            base_url="",
            api_mode="chat",
            api_call_count=1,
            message_count=1,
            tool_count=0,
            approx_input_tokens=10,
            request_char_count=20,
            max_tokens=16,
        )
        on_post_api_request(
            task_id=f"api-{session_id}",
            session_id=session_id,
            platform="persist-test",
            model="gpt-4",
            provider="openai",
            base_url="",
            api_mode="chat",
            api_call_count=1,
            api_duration=0.2,
            finish_reason="stop",
            message_count=1,
            response_model="gpt-4",
            usage={"prompt_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            assistant_content_chars=5,
            assistant_tool_call_count=0,
        )
        on_post_llm_call(
            session_id=session_id,
            user_message="persist",
            assistant_response="ok",
            conversation_history=[],
            model="gpt-4",
            platform="persist-test",
        )
        on_session_end(
            session_id=session_id,
            completed=True,
            interrupted=False,
            model="gpt-4",
            platform="persist-test",
        )
        plugin._force_flush()
    finally:
        tracer_mod._tracer = None


def find(session_id: str, attempts: int = 15) -> dict:
    for _ in range(attempts):
        projects = graphql(
            "query { projects(first: 20) { edges { node { id name } } } }"
        )
        edges = ((projects.get("projects") or {}).get("edges") or [])
        project_id = None
        for edge in edges:
            node = edge.get("node") or {}
            if node.get("name") == PROJECT:
                project_id = node["id"]
                break
        if project_id:
            data = graphql(
                """
                query ProjectSpans($projectId: ID!, $first: Int!) {
                  node(id: $projectId) {
                    ... on Project {
                      spans(first: $first, sort: { col: startTime, dir: desc }) {
                        edges {
                          node {
                            name
                            parentId
                            context { traceId spanId }
                            attributes
                          }
                        }
                      }
                    }
                  }
                }
                """,
                {"projectId": project_id, "first": 80},
            )
            nodes = [
                e["node"]
                for e in (((data.get("node") or {}).get("spans") or {}).get("edges") or [])
                if e.get("node")
            ]
            ours = [s for s in nodes if session_id in str(s.get("attributes", ""))]
            if ours:
                return {
                    "session_id": session_id,
                    "span_count": len(ours),
                    "span_names": [s.get("name") for s in ours],
                    "trace_ids": sorted(
                        {
                            (s.get("context") or {}).get("traceId")
                            for s in ours
                            if (s.get("context") or {}).get("traceId")
                        }
                    ),
                }
        time.sleep(2)
    raise SystemExit(f"trace not found for {session_id}")


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "emit":
        session_id = sys.argv[2]
        emit(session_id)
        result = find(session_id)
        print(json.dumps(result, indent=2))
        return 0
    if cmd == "query":
        print(json.dumps(find(sys.argv[2]), indent=2))
        return 0
    raise SystemExit("usage: otel-persist.py emit|query SESSION")


if __name__ == "__main__":
    raise SystemExit(main())
