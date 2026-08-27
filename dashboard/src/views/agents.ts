import { h } from "../sdk";
import { Card, DataTable } from "../components/data";
import { arrayValue, evidenceData, objectValue } from "./helpers";

export function AgentsView({ data }: { data: Record<string, unknown> }): unknown {
  const profileEvidence = objectValue(data.profiles);
  const workerEvidence = objectValue(data.workers);
  const profiles = arrayValue(evidenceData(profileEvidence, []));
  const workers = arrayValue(evidenceData(workerEvidence, []));
  return h(
    "div",
    { className: "eos-grid" },
    Card({
      title: `Profiles · ${profiles.length}`,
      status: String(profileEvidence.status ?? "UNKNOWN"),
      children: DataTable({
        rows: profiles,
        columns: [
          { key: "name", label: "Profile" },
          { key: "model", label: "Model" },
          { key: "provider", label: "Provider" },
          { key: "gateway_running", label: "Gateway" },
          { key: "skill_count", label: "Skills" },
        ],
        empty: "No Hermes profiles discovered.",
      }),
    }),
    Card({
      title: `Active workers · ${workers.length}`,
      status: String(workerEvidence.status ?? "UNKNOWN"),
      children: DataTable({
        rows: workers,
        columns: [
          { key: "profile", label: "Profile" },
          { key: "hermes_kanban_task_id", label: "Task ID" },
          { key: "hermes_kanban_run_id", label: "Run ID" },
          { key: "worker_pid", label: "PID" },
          { key: "pid_alive", label: "Alive" },
        ],
        empty: "No currently running Kanban workers.",
      }),
    }),
  );
}

