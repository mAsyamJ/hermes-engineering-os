import { h } from "../sdk";
import { Card, DataTable } from "../components/data";
import type { Evidence, Task } from "../types";

export function TasksView({ data }: { data: Evidence<Task[]> }): unknown {
  const rows = Array.isArray(data.data) ? data.data as unknown as Array<Record<string, unknown>> : [];
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
      }),
    }),
  );
}

