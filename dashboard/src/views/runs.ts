import { fetchRun } from "../api";
import { Card, DataTable } from "../components/data";
import { h, sdk } from "../sdk";
import type { Evidence, Run } from "../types";
import { arrayValue, objectValue } from "./helpers";

export function RunsView({ data }: { data: Evidence<Run[]> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const rows = Array.isArray(data.data) ? data.data as unknown as Array<Record<string, unknown>> : [];
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId == null) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    let active = true;
    setDetail(null);
    setDetailError(null);
    fetchRun(selectedId)
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
    Card({
      title: `Runs · ${rows.length}`,
      status: data.status,
      children: DataTable({
        rows,
        columns: [
          { key: "id", label: "Kanban run ID" },
          { key: "task_id", label: "Kanban task ID" },
          { key: "profile", label: "Profile" },
          { key: "status", label: "Status" },
          { key: "worker_pid", label: "PID" },
          { key: "outcome", label: "Outcome" },
        ],
        empty: "No run history reported by Hermes Kanban.",
        onSelect: (row) => setSelectedId(Number(row.id)),
      }),
    }),
    selectedId != null
      ? Card({
          title: `TRACE · run ${selectedId}`,
          status: String(objectValue(detail?.observability).status ?? (detailError ? "DEGRADED" : "UNKNOWN")),
          children: traces.length
            ? DataTable({
                rows: traces,
                columns: [
                  { key: "trace_id", label: "Trace" },
                  { key: "hermes_kanban_task_id", label: "Task" },
                  { key: "session_id", label: "Session" },
                  { key: "model", label: "Model" },
                  { key: "llm_calls", label: "LLM" },
                  { key: "tool_calls", label: "Tools" },
                  { key: "phoenix_url", label: "Open in Phoenix" },
                ],
                empty: "No correlated traces.",
              })
            : h(
                "p",
                { className: "eos-note" },
                detailError || "No exact Kanban-to-trace match for this run.",
              ),
        })
      : h("p", { className: "eos-note" }, "Select a run to load exact TRACE evidence."),
  );
}
