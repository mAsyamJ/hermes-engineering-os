#!/usr/bin/env python3
"""Ephemeral Phoenix E2E: hermes-otel hooks → OTLP/HTTP → GraphQL query.

Uses a loopback-only container. Does not touch production Postgres or :6006.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

IMAGE = "arizephoenix/phoenix:version-20.4.0"
CONTAINER = "hermes-eos-e2e-phoenix"
HOST_PORT = 16006
PROJECT = "hermes-otel-e2e-test"


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sudo", "-n", "docker", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def wait_http(url: str, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return
                last = str(resp.status)
        except Exception as exc:
            last = type(exc).__name__
        time.sleep(2)
    raise SystemExit(f"Phoenix UI did not become ready: {last}")


def graphql(base: str, query: str, variables: dict | None = None) -> dict:
    body = {"query": query}
    if variables is not None:
        body["variables"] = variables
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}/graphql",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload.get("data") or {}


def emit_trace(endpoint: str, session_id: str) -> None:
    os.environ["OTEL_PROJECT_NAME"] = PROJECT
    os.environ.pop("OTEL_PHOENIX_ENDPOINT", None)
    sys.path.insert(0, "/opt/hermes-engineering-os/upstream/hermes-otel")
    import hermes_otel.tracer as tracer_mod
    from hermes_otel.hooks import (
        on_post_api_request,
        on_post_llm_call,
        on_post_tool_call,
        on_pre_api_request,
        on_pre_llm_call,
        on_pre_tool_call,
        on_session_end,
        on_session_start,
    )
    from hermes_otel.tracer import HermesOTelPlugin

    plugin = HermesOTelPlugin()
    assert plugin._init_otlp(endpoint, backend_name="Phoenix"), "OTLP init failed"
    tracer_mod._tracer = plugin
    try:
        on_session_start(session_id=session_id, model="gpt-4", platform="e2e-test")
        on_pre_llm_call(
            session_id=session_id,
            user_message="List files",
            conversation_history=[],
            is_first_turn=True,
            model="gpt-4",
            platform="e2e-test",
        )
        on_pre_api_request(
            task_id=f"api-{session_id}",
            session_id=session_id,
            platform="e2e-test",
            model="gpt-4",
            provider="openai",
            base_url="",
            api_mode="chat",
            api_call_count=1,
            message_count=2,
            tool_count=1,
            approx_input_tokens=100,
            request_char_count=500,
            max_tokens=512,
        )
        on_pre_tool_call(tool_name="bash", args={"cmd": "ls"}, task_id=f"tool-{session_id}")
        on_post_tool_call(
            tool_name="bash",
            args={"cmd": "ls"},
            result="README.md",
            task_id=f"tool-{session_id}",
        )
        on_post_api_request(
            task_id=f"api-{session_id}",
            session_id=session_id,
            platform="e2e-test",
            model="gpt-4",
            provider="openai",
            base_url="",
            api_mode="chat",
            api_call_count=1,
            api_duration=0.5,
            finish_reason="stop",
            message_count=2,
            response_model="gpt-4",
            usage={"prompt_tokens": 100, "output_tokens": 30, "total_tokens": 130},
            assistant_content_chars=50,
            assistant_tool_call_count=1,
        )
        on_post_llm_call(
            session_id=session_id,
            user_message="List files",
            assistant_response="Found README.md",
            conversation_history=[],
            model="gpt-4",
            platform="e2e-test",
        )
        on_session_end(
            session_id=session_id,
            completed=True,
            interrupted=False,
            model="gpt-4",
            platform="e2e-test",
        )
        plugin._force_flush()
    finally:
        tracer_mod._tracer = None


def query_spans(base: str) -> list[dict]:
    projects = graphql(
        base,
        """
        query Projects {
          projects(first: 20) {
            edges { node { id name hasTraces } }
          }
        }
        """,
    )
    edges = ((projects.get("projects") or {}).get("edges") or [])
    project = None
    for edge in edges:
        node = edge.get("node") or {}
        if node.get("name") == PROJECT:
            project = node
            break
    if project is None:
        raise RuntimeError(f"project {PROJECT} missing: {projects}")
    data = graphql(
        base,
        """
        query ProjectSpans($projectId: ID!, $first: Int!) {
          node(id: $projectId) {
            ... on Project {
              name
              spans(first: $first, sort: { col: startTime, dir: desc }) {
                edges {
                  node {
                    name
                    statusCode
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
        {"projectId": project["id"], "first": 50},
    )
    span_edges = (((data.get("node") or {}).get("spans") or {}).get("edges") or [])
    return [e["node"] for e in span_edges if e.get("node")]


def main() -> int:
    if port_open(HOST_PORT):
        docker("rm", "-f", CONTAINER, check=False)
        time.sleep(1)
    if port_open(HOST_PORT):
        raise SystemExit(f"port {HOST_PORT} still in use")

    docker("rm", "-f", CONTAINER, check=False)
    run = docker(
        "run",
        "-d",
        "--name",
        CONTAINER,
        "-p",
        f"127.0.0.1:{HOST_PORT}:6006",
        IMAGE,
    )
    print("container", run.stdout.strip())
    try:
        wait_http(f"http://127.0.0.1:{HOST_PORT}")
        session_id = f"e2e-phase2-{int(time.time())}"
        emit_trace(f"http://127.0.0.1:{HOST_PORT}/v1/traces", session_id)
        time.sleep(4)
        spans = query_spans(f"http://127.0.0.1:{HOST_PORT}")
        ours = [s for s in spans if session_id in str(s.get("attributes", ""))]
        names = [s.get("name") for s in ours]
        result = {
            "session_id": session_id,
            "span_count": len(ours),
            "span_names": names,
            "trace_ids": sorted(
                {
                    (s.get("context") or {}).get("traceId")
                    for s in ours
                    if (s.get("context") or {}).get("traceId")
                }
            ),
            "tool_parent": next((s.get("parentId") for s in ours if s.get("name") == "tool.bash"), None),
        }
        print(json.dumps(result, indent=2))
        assert "agent" in names or any(n == "agent" or (n or "").startswith("session") for n in names), names
        assert any("llm" in (n or "") for n in names), names
        assert any("api" in (n or "") for n in names), names
        assert "tool.bash" in names, names
        tool = next(s for s in ours if s.get("name") == "tool.bash")
        assert tool.get("parentId"), "tool span missing parent"
        assert result["trace_ids"], "missing trace id"
        print("GATE_2_4_PASS")
        return 0
    finally:
        docker("rm", "-f", CONTAINER, check=False)
        print("ephemeral phoenix removed")


if __name__ == "__main__":
    raise SystemExit(main())
