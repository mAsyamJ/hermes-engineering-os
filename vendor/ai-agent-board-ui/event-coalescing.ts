/*
 * Modified from DanWahlin/ai-agent-board
 * packages/client/src/components/AgentPanel.tsx, lines 75-168
 * commit 4f2965e72ad99e32e0375af837247cafb382f17c
 * MIT License; see ./LICENSE.
 *
 * Changes: Hermes-specific identifiers/types, sequence-safe grouping, generic
 * ANSI cleanup, and removal of .NET/ACP-specific assumptions.
 */

export interface HermesEvent {
  id: number | string;
  runId?: number | string | null;
  type: string;
  content?: string | null;
  sequence?: number | null;
  toolCallId?: string | null;
  timestamp?: number | string | null;
}

export interface CoalescedHermesEvent extends HermesEvent {
  content: string;
  toolLabel?: string;
  toolArgs?: string;
  sourceIds: Array<number | string>;
}

export function stripBuildNoise(content: string): string {
  return content
    .split("\n")
    .map((line) => line.replace(/\x1b\[[0-9;]*m/g, ""))
    .filter((line) => line.trim().length > 0)
    .join("\n");
}

export function parseCommandEvent(event: HermesEvent): CoalescedHermesEvent {
  const content = event.content ?? "";
  const base: CoalescedHermesEvent = {
    ...event,
    content,
    sourceIds: [event.id],
  };
  const colon = content.indexOf(": ");
  if (colon === -1) return base;
  const toolLabel = content.slice(0, colon);
  const raw = content.slice(colon + 2);
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const display = parsed.command ?? parsed.description ?? raw;
    return { ...base, toolLabel, toolArgs: String(display) };
  } catch {
    return { ...base, toolLabel, toolArgs: raw };
  }
}

function mergeKey(event: HermesEvent): string {
  return [
    event.runId ?? "",
    event.toolCallId ?? "",
    event.type === "command_output" ? "output" : event.type,
  ].join(":");
}

export function coalesceEvents(events: HermesEvent[]): CoalescedHermesEvent[] {
  const ordered = [...events].sort((left, right) => {
    const a = left.sequence ?? Number(left.id);
    const b = right.sequence ?? Number(right.id);
    return Number(a) - Number(b);
  });
  const result: CoalescedHermesEvent[] = [];
  for (const source of ordered) {
    const clean = stripBuildNoise(source.content ?? "");
    if (!clean && source.type !== "complete" && source.type !== "error") continue;
    const event = source.type === "command"
      ? parseCommandEvent({ ...source, content: clean })
      : { ...source, content: clean, sourceIds: [source.id] };
    const previous = result[result.length - 1];
    const mergeable = ["thinking", "output", "command_output"].includes(event.type);
    if (previous && mergeable && mergeKey(previous) === mergeKey(event)) {
      previous.content = [previous.content, event.content].filter(Boolean).join("\n");
      previous.sourceIds.push(...event.sourceIds);
      continue;
    }
    result.push(event);
  }
  return result;
}

