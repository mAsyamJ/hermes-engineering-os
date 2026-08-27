import { h } from "../sdk";
import type { EvidenceStatus } from "../types";

const LABEL: Record<string, string> = {
  AVAILABLE: "Available",
  DEGRADED: "Degraded",
  UNKNOWN: "Unknown",
  BLOCKED_AUTH: "Blocked auth",
};

export function StatusBadge({ status }: { status: EvidenceStatus | string }): unknown {
  return h(
    "span",
    { className: `eos-status eos-status--${status.toLowerCase().replace("_", "-")}` },
    LABEL[status] ?? status,
  );
}

export function EmptyState({ children }: { children: string }): unknown {
  return h("div", { className: "eos-empty" }, children);
}

export function ErrorState({ message, retry }: { message: string; retry: () => void }): unknown {
  return h(
    "div",
    { className: "eos-error", role: "alert" },
    h("strong", null, "Evidence unavailable"),
    h("span", null, message),
    h("button", { type: "button", onClick: retry }, "Retry"),
  );
}

