import { coalesceEvents, type HermesEvent } from "../../../vendor/ai-agent-board-ui/event-coalescing";
import { h } from "../sdk";
import { EmptyState } from "./status";

export function EventStream({ events }: { events: HermesEvent[] }): unknown {
  const grouped = coalesceEvents(events);
  if (!grouped.length) return EmptyState({ children: "No run events recorded." });
  return h(
    "ol",
    { className: "eos-events" },
    ...grouped.map((event) =>
      h(
        "li",
        { key: String(event.id), className: "eos-event" },
        h("span", { className: "eos-event__type" }, event.type),
        h("pre", null, event.toolArgs ?? event.content),
      ),
    ),
  );
}

