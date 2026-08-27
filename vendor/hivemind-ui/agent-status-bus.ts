/*
 * Modified from dip497/hivemind
 * apps/desktop/src/renderer/src/agent-status-bus.ts
 * commit f4209b905c54342073822409f1da1a9f56da4981
 * MIT License; see ./LICENSE.
 *
 * Changes: authoritative Hermes run/profile identifiers replace tile/PTY
 * signals; Electron notifications, screen scraping, timers, and inferred
 * completion have been removed.
 */

export type HermesAgentStatus =
  | "running"
  | "ready"
  | "blocked"
  | "review"
  | "done"
  | "failed"
  | "idle"
  | "unknown";

export interface HermesAgentStatusEvent {
  profile: string;
  status: HermesAgentStatus;
  taskId?: string | null;
  runId?: number | null;
  label?: string | null;
  sequence?: number | null;
}

type Listener = (event: HermesAgentStatusEvent) => void;

const listeners = new Set<Listener>();
const emitted = new Map<string, HermesAgentStatusEvent>();

function same(left: HermesAgentStatusEvent, right: HermesAgentStatusEvent): boolean {
  return left.status === right.status
    && left.taskId === right.taskId
    && left.runId === right.runId
    && left.label === right.label;
}

export function publishAgentStatus(event: HermesAgentStatusEvent): void {
  const previous = emitted.get(event.profile);
  if (previous && same(previous, event)) return;
  if (
    previous?.sequence != null
    && event.sequence != null
    && event.sequence < previous.sequence
  ) return;
  const copy = { ...event };
  emitted.set(event.profile, copy);
  for (const listener of listeners) listener(copy);
}

export function subscribeAgentStatus(listener: Listener): () => void {
  listeners.add(listener);
  for (const event of emitted.values()) listener({ ...event });
  return () => listeners.delete(listener);
}

export function statusOf(profile: string): HermesAgentStatusEvent | null {
  const event = emitted.get(profile);
  return event ? { ...event } : null;
}

export function clearAgentStatus(profile: string): void {
  emitted.delete(profile);
}

export function resetAgentStatusBus(): void {
  emitted.clear();
  listeners.clear();
}

