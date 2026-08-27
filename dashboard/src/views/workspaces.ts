import { h } from "../sdk";
import { Card, DataTable } from "../components/data";
import { arrayValue, evidenceData, objectValue } from "./helpers";

export function WorkspacesView({ data }: { data: Record<string, unknown> }): unknown {
  const payload = objectValue(evidenceData(data, {}));
  const repositories = arrayValue(payload.repositories);
  const taskWorkspaces = arrayValue(payload.task_workspaces);
  return h(
    "div",
    { className: "eos-stack" },
    h(
      "p",
      { className: "eos-note" },
      "Fixed hierarchy: configured repository → Git worktree → canonical Hermes run. This view never creates or removes worktrees.",
    ),
    Card({
      title: `Configured repositories · ${repositories.length}`,
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: repositories,
        columns: [
          { key: "label", label: "Repository" },
          { key: "path", label: "Path" },
          { key: "exists", label: "Exists" },
          { key: "mode", label: "Mode" },
          { key: "worktrees", label: "Worktrees" },
        ],
        empty: "No configured repository evidence.",
      }),
    }),
    Card({
      title: `Task workspaces · ${taskWorkspaces.length}`,
      children: DataTable({
        rows: taskWorkspaces,
        columns: [
          { key: "hermes_kanban_task_id", label: "Task ID" },
          { key: "path", label: "Workspace" },
          { key: "branch", label: "Branch" },
          { key: "status", label: "Status" },
        ],
        empty: "No task workspaces reported by Hermes Kanban.",
      }),
    }),
  );
}

