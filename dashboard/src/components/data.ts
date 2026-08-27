import { h } from "../sdk";
import { EmptyState, StatusBadge } from "./status";

export function Card(props: { title: string; children: unknown; status?: string }): unknown {
  return h(
    "section",
    { className: "eos-card" },
    h(
      "header",
      { className: "eos-card__header" },
      h("h3", null, props.title),
      props.status ? StatusBadge({ status: props.status }) : null,
    ),
    h("div", { className: "eos-card__body" }, props.children),
  );
}

export function KeyValues({ value }: { value: Record<string, unknown> }): unknown {
  const rows = Object.entries(value).filter(([, item]) => {
    return item == null || ["string", "number", "boolean"].includes(typeof item);
  });
  if (!rows.length) return EmptyState({ children: "No scalar evidence reported." });
  return h(
    "dl",
    { className: "eos-kv" },
    ...rows.map(([key, item]) =>
      h(
        "div",
        { className: "eos-kv__row", key },
        h("dt", null, key.replace(/_/g, " ")),
        h("dd", null, item == null ? "—" : String(item)),
      ),
    ),
  );
}

export function DataTable(props: {
  rows: Array<Record<string, unknown>>;
  columns: Array<{ key: string; label: string }>;
  empty: string;
  onSelect?: (row: Record<string, unknown>) => void;
}): unknown {
  if (!props.rows.length) return EmptyState({ children: props.empty });
  return h(
    "div",
    { className: "eos-table-wrap" },
    h(
      "table",
      { className: "eos-table" },
      h(
        "thead",
        null,
        h(
          "tr",
          null,
          ...props.columns.map((column) => h("th", { key: column.key }, column.label)),
        ),
      ),
      h(
        "tbody",
        null,
        ...props.rows.map((row, index) =>
          h(
            "tr",
            {
              key: String(row.id ?? row.name ?? index),
              onClick: props.onSelect ? () => props.onSelect?.(row) : undefined,
              className: props.onSelect ? "eos-table__selectable" : undefined,
            },
            ...props.columns.map((column) =>
              h("td", { key: column.key }, formatCell(row[column.key])),
            ),
          ),
        ),
      ),
    ),
  );
}

function formatCell(value: unknown): unknown {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  if (/^https?:\/\/127\.0\.0\.1:6006\//.test(text)) {
    return h("a", { href: text, className: "eos-link", target: "_blank", rel: "noreferrer" }, "Open in Phoenix");
  }
  return text;
}

