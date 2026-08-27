export type EvidenceStatus = "AVAILABLE" | "DEGRADED" | "UNKNOWN" | "BLOCKED_AUTH";

export interface Evidence<T = unknown> {
  status: EvidenceStatus;
  source: string;
  data: T;
  observed_at: number;
  detail?: string | null;
}

export interface Task {
  id: string;
  title: string;
  status: string;
  assignee?: string | null;
  priority?: number;
  branch_name?: string | null;
  workspace_path?: string | null;
  current_run_id?: number | null;
  created_at?: number;
}

export interface Run {
  id: number;
  task_id: string;
  profile?: string | null;
  status: string;
  worker_pid?: number | null;
  started_at?: number;
  ended_at?: number | null;
  summary?: string | null;
  error?: string | null;
}

export type ViewId =
  | "overview"
  | "tasks"
  | "runs"
  | "agents"
  | "plugins"
  | "github"
  | "workspaces"
  | "observability";

