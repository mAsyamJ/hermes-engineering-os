import { fetchPerformanceWhy } from "../api";
import { Card, DataTable, KeyValues } from "../components/data";
import { h, sdk } from "../sdk";
import { arrayValue, objectValue } from "./helpers";

function metricLabel(row: Record<string, unknown>): string {
  const value = row.value;
  const tier = String(row.evidence_tier ?? "NO_DATA");
  if (value == null || tier === "NO_DATA") return "INSUFFICIENT DATA";
  if (typeof value === "number" && String(row.unit) === "proportion") {
    return `${(value * 100).toFixed(1)}% · ${tier}`;
  }
  return `${String(value)} · ${tier}`;
}

export function PerformanceView({ data }: { data: Record<string, unknown> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const coverage = objectValue(data.coverage);
  const metrics = arrayValue(data.metrics);
  const insights = arrayValue(data.insights);
  const failures = arrayValue(data.failures);
  const profiles = arrayValue(data.profiles);
  const comparisons = arrayValue(data.comparisons);
  const trends = arrayValue(data.trends);
  const last = objectValue(data.last_materialization);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let active = true;
    fetchPerformanceWhy(String(selected.metric_id ?? "lifecycle_completion_rate"), String(selected.cohort_id ?? "production_all"))
      .then((value) => {
        if (active) setDetail(value);
      })
      .catch(() => {
        if (active) setDetail({ status: "DEGRADED" });
      });
    return () => {
      active = false;
    };
  }, [selected]);

  const why = objectValue(detail?.why);
  const qualityRows = metrics.filter((row) => String(row.metric_id).startsWith("quality_"));
  const outcomeRows = metrics.filter((row) =>
    [
      "lifecycle_completion_rate",
      "verified_success_rate",
      "first_pass_rate",
      "retry_rate",
      "rework_rate",
      "human_intervention_detection_rate",
    ].includes(String(row.metric_id)),
  );
  const efficiencyRows = metrics.filter((row) =>
    ["task_wall_seconds", "run_wall_seconds", "trace_wall_seconds", "llm_call_count", "tool_call_count", "token_total", "cost_known_rate"].includes(
      String(row.metric_id),
    ),
  );
  const qualityKnown = qualityRows.some((row) => Number(row.known_n) > 0);

  return h(
    "div",
    { className: "eos-stack" },
    h(
      "div",
      { className: "eos-grid" },
      Card({
        title: "Performance data health",
        status: String(data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            contract: data.contract_version,
            last_materialization: last.materialization_id,
            last_status: last.status,
            ended_at: last.ended_at,
            current_aggregates: data.current_aggregates,
            quality: data.quality,
            causal: "false — observational only",
          },
        }),
      }),
      Card({
        title: "Coverage",
        status: String(data.quality ?? data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            production_tasks: coverage.production_tasks,
            current_aggregates: coverage.current_aggregates,
            quality_insufficient_rows: coverage.quality_insufficient_rows,
            lifecycle_present: coverage.lifecycle_present,
          },
        }),
      }),
    ),
    h(
      "p",
      { className: "eos-note" },
      "Coverage before ranking. UNKNOWN is not failure. There is no BEST MODEL. Phase 5 does not route Hermes.",
    ),
    qualityKnown
      ? null
      : h("p", { className: "eos-note" }, "QUALITY PERFORMANCE: INSUFFICIENT DATA — 0 production tasks have Phase 4 evaluation coverage."),
    Card({
      title: "Outcomes",
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: outcomeRows.map((row) => ({ ...row, display: metricLabel(row) })),
        columns: [
          { key: "metric_id", label: "Metric" },
          { key: "population_n", label: "N" },
          { key: "known_n", label: "Known N" },
          { key: "unknown_n", label: "Unknown N" },
          { key: "coverage", label: "Coverage" },
          { key: "display", label: "Estimate" },
          { key: "evidence_tier", label: "Tier" },
        ],
        empty: "INSUFFICIENT DATA",
        onSelect: (row) => setSelected(row),
      }),
    }),
    Card({
      title: "Quality",
      status: qualityKnown ? String(data.status ?? "UNKNOWN") : "INSUFFICIENT_DATA",
      children: DataTable({
        rows: qualityRows.map((row) => ({ ...row, display: metricLabel(row) })),
        columns: [
          { key: "metric_id", label: "Dimension" },
          { key: "known_n", label: "Evaluated known N" },
          { key: "display", label: "Estimate" },
          { key: "evidence_tier", label: "Tier" },
        ],
        empty: "INSUFFICIENT DATA",
        onSelect: (row) => setSelected(row),
      }),
    }),
    Card({
      title: "Efficiency",
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: efficiencyRows.map((row) => ({ ...row, display: metricLabel(row) })),
        columns: [
          { key: "metric_id", label: "Metric" },
          { key: "known_n", label: "Known N" },
          { key: "unknown_n", label: "Unknown N" },
          { key: "display", label: "Median / status" },
          { key: "evidence_tier", label: "Tier" },
        ],
        empty: "INSUFFICIENT DATA",
        onSelect: (row) => setSelected(row),
      }),
    }),
    Card({
      title: "Failure taxonomy",
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: failures.map((row) => ({ ...row, display: metricLabel(row) })),
        columns: [
          { key: "label", label: "Label" },
          { key: "count", label: "Count" },
          { key: "known_n", label: "Known N" },
          { key: "display", label: "Rate" },
          { key: "evidence_tier", label: "Tier" },
        ],
        empty: "NO_DATA",
      }),
    }),
    Card({
      title: "Profile name (not config version)",
      status: "OBSERVATIONAL",
      children: DataTable({
        rows: profiles.map((row) => ({ ...row, display: metricLabel(row) })),
        columns: [
          { key: "dimension_value", label: "Profile name" },
          { key: "population_n", label: "N" },
          { key: "known_n", label: "Known N" },
          { key: "display", label: "Lifecycle completion" },
          { key: "evidence_tier", label: "Tier" },
        ],
        empty: "INSUFFICIENT DATA",
        onSelect: (row) => setSelected(row),
      }),
    }),
    Card({
      title: "Comparisons (no ranking)",
      status: "OBSERVATIONAL",
      children: DataTable({
        rows: comparisons,
        columns: [
          { key: "left_identity", label: "Left" },
          { key: "right_identity", label: "Right" },
          { key: "metric_id", label: "Metric" },
          { key: "interpretation", label: "Interpretation" },
          { key: "comparability", label: "Comparability" },
          { key: "confounding_status", label: "Confounding" },
        ],
        empty: "INSUFFICIENT DATA",
      }),
    }),
    Card({
      title: "Trends",
      status: "OBSERVATIONAL",
      children: DataTable({
        rows: trends,
        columns: [
          { key: "metric_id", label: "Metric" },
          { key: "comparison_set", label: "Window" },
          { key: "interpretation", label: "State" },
          { key: "left_n", label: "Prior N" },
          { key: "right_n", label: "Current N" },
        ],
        empty: "INSUFFICIENT DATA",
      }),
    }),
    Card({
      title: "Insights",
      children: insights.length
        ? h(
            "ul",
            { className: "eos-note" },
            ...insights.map((item, index) => h("li", { key: index }, String(item.body ?? ""))),
          )
        : h("p", { className: "eos-note" }, "No insights yet."),
    }),
    selected
      ? Card({
          title: `WHY · ${String(selected.metric_id)}`,
          status: String(detail?.status ?? "UNKNOWN"),
          children: h(
            "div",
            { className: "eos-stack" },
            h("p", { className: "eos-note" }, String(why.denominator ?? "Select a metric to explain the denominator.")),
            KeyValues({
              value: {
                population_n: why.population_n,
                known_n: why.known_n,
                unknown_n: why.unknown_n,
                na_n: why.na_n,
                excluded_total: why.excluded_total,
                member_total: why.member_total,
                causal: "false",
                prompt_version_performance: why.prompt_version_performance,
              },
            }),
          ),
        })
      : null,
  );
}
