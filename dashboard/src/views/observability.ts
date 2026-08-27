import { h } from "../sdk";
import { Card, KeyValues } from "../components/data";

export function ObservabilityView({ data }: { data: Record<string, unknown> }): unknown {
  return h(
    "div",
    { className: "eos-stack" },
    Card({
      title: "Existing Hermes OTel plugin",
      status: String(data.status ?? "UNKNOWN"),
      children: KeyValues({ value: data }),
    }),
    h(
      "p",
      { className: "eos-note" },
      "Observability is fail-open. Phoenix and the dedicated analytics PostgreSQL service are not deployed in Phase 1.",
    ),
  );
}

