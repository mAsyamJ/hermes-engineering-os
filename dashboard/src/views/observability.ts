import { h } from "../sdk";
import { Card, DataTable, KeyValues } from "../components/data";
import { arrayValue, objectValue } from "./helpers";

export function ObservabilityView({ data }: { data: Record<string, unknown> }): unknown {
  const traces = arrayValue(data.recent_traces);
  const hermesOtel = objectValue(data.hermes_otel);
  const last = objectValue(data.last_trace);
  return h(
    "div",
    { className: "eos-stack" },
    h(
      "div",
      { className: "eos-grid" },
      Card({
        title: "hermes-otel",
        status: String(hermesOtel.status ?? data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            installed: hermesOtel.installed,
            version: hermesOtel.version,
            sdk_available: hermesOtel.sdk_available,
            fail_open: data.fail_open,
            export: data.export,
          },
        }),
      }),
      Card({
        title: "Phoenix",
        status: String(data.phoenix ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            url: data.phoenix_url,
            last_trace: last.trace_id,
            detail: data.detail,
          },
        }),
      }),
      Card({
        title: "PostgreSQL",
        status: String(data.postgresql ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            container: "hermes-eos-postgres",
            host_port: "none",
            isolation: "dedicated observability volume",
          },
        }),
      }),
    ),
    Card({
      title: "Recent runs",
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: traces,
        columns: [
          { key: "hermes_kanban_task_id", label: "Task" },
          { key: "hermes_kanban_run_id", label: "Run" },
          { key: "agent", label: "Agent" },
          { key: "model", label: "Model" },
          { key: "duration_ms", label: "Duration" },
          { key: "llm_calls", label: "LLM" },
          { key: "tool_calls", label: "Tools" },
          { key: "trace_id", label: "Trace" },
          { key: "phoenix_url", label: "Open in Phoenix" },
        ],
        empty: "No traces reported by Phoenix yet.",
      }),
    }),
    h(
      "p",
      { className: "eos-note" },
      "Observability is derived and fail-open. Hermes Kanban remains the only task authority. Phoenix is the detailed viewer.",
    ),
  );
}
