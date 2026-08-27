import { fetchTask } from "../api";
import { Card, DataTable, KeyValues } from "../components/data";
import { h, sdk } from "../sdk";
import type { Evidence, Task } from "../types";
import { arrayValue, objectValue } from "./helpers";

export function TasksView({ data }: { data: Evidence<Task[]> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const rows = Array.isArray(data.data) ? data.data as unknown as Array<Record<string, unknown>> : [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    let active = true;
    setDetail(null);
    setDetailError(null);
    fetchTask(selectedId)
      .then((value) => {
        if (active) setDetail(value);
      })
      .catch((reason: unknown) => {
        if (active) setDetailError(reason instanceof Error ? reason.message : String(reason));
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  const traces = arrayValue(objectValue(detail?.observability).data);
  return h(
    "div",
    { className: "eos-stack" },
    h(
      "div",
      { className: "eos-toolbar" },
      h("p", null, "Hermes Kanban is the only task lifecycle authority."),
      h("a", { href: "/kanban", className: "eos-link" }, "Open native Kanban"),
    ),
    Card({
      title: `Tasks · ${rows.length}`,
      status: data.status,
      children: DataTable({
        rows,
        columns: [
          { key: "id", label: "Kanban task ID" },
          { key: "title", label: "Title" },
          { key: "status", label: "Status" },
          { key: "assignee", label: "Assignee" },
          { key: "branch_name", label: "Branch" },
          { key: "current_run_id", label: "Run" },
        ],
        empty: "No tasks reported by the active Hermes board.",
        onSelect: (row) => setSelectedId(String(row.id ?? "")),
      }),
    }),
    selectedId
      ? Card({
          title: `TRACE · ${selectedId}`,
          status: String(objectValue(detail?.observability).status ?? (detailError ? "DEGRADED" : "UNKNOWN")),
          children: h(
            "div",
            { className: "eos-stack" },
            detailError ? h("p", { className: "eos-note" }, detailError) : null,
            traces.length
              ? DataTable({
                  rows: traces,
                  columns: [
                    { key: "trace_id", label: "Trace" },
                    { key: "hermes_kanban_run_id", label: "Run" },
                    { key: "session_id", label: "Session" },
                    { key: "model", label: "Model" },
                    { key: "llm_calls", label: "LLM" },
                    { key: "tool_calls", label: "Tools" },
                    { key: "phoenix_url", label: "Open in Phoenix" },
                  ],
                  empty: "No correlated traces.",
                })
              : h("p", { className: "eos-note" }, "No exact Kanban-to-trace match for this task."),
            detail ? KeyValues({ value: objectValue(detail.correlation) }) : null,
          ),
        })
      : h("p", { className: "eos-note" }, "Select a task to load exact TRACE evidence."),
  );
}
