import { Card, DataTable } from "../components/data";
import type { Evidence, Run } from "../types";

export function RunsView({ data }: { data: Evidence<Run[]> }): unknown {
  const rows = Array.isArray(data.data) ? data.data as unknown as Array<Record<string, unknown>> : [];
  return Card({
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
    }),
  });
}

