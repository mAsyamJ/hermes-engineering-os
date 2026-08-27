"""Correlation identifiers with non-interchangeable namespaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CorrelationIds:
    hermes_kanban_task_id: str | None = None
    hermes_runtime_task_id: str | None = None
    hermes_kanban_run_id: int | None = None
    session_id: str | None = None
    turn_id: str | None = None
    api_request_id: str | None = None
    tool_call_id: str | None = None
    git_sha: str | None = None
    github_pr_id: int | None = None
    github_check_id: int | None = None
    otel_trace_id: str | None = None
    otel_span_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


KANBAN_TASK_NAMESPACE = "hermes.kanban.task_id"
RUNTIME_TASK_NAMESPACE = "hermes.runtime.task_id"

