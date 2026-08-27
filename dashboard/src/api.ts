import { sdk } from "./sdk";
import type { Evidence, Run, Task, ViewId } from "./types";

const BASE = "/api/plugins/engineering-os";

export interface Endpoints {
  overview: Record<string, unknown>;
  tasks: Evidence<Task[]>;
  runs: Evidence<Run[]>;
  agents: Record<string, unknown>;
  plugins: Evidence<Record<string, unknown>>;
  github: Record<string, unknown>;
  workspaces: Evidence<Record<string, unknown>>;
  observability: Record<string, unknown>;
}

export function fetchView<T extends ViewId>(view: T): Promise<Endpoints[T]> {
  return sdk().fetchJSON<Endpoints[T]>(`${BASE}/${view}`);
}

export function fetchTask(taskId: string): Promise<Record<string, unknown>> {
  return sdk().fetchJSON(`${BASE}/tasks/${encodeURIComponent(taskId)}`);
}

export function fetchRun(runId: number): Promise<Record<string, unknown>> {
  return sdk().fetchJSON(`${BASE}/runs/${runId}`);
}

