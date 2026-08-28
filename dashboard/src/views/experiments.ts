import { fetchExperimentExplain } from "../api";
import { Card, DataTable, KeyValues } from "../components/data";
import { h, sdk } from "../sdk";
import { arrayValue, objectValue } from "./helpers";

export function ExperimentsView({ data }: { data: Record<string, unknown> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const experiments = arrayValue(data.experiments);
  const coverage = objectValue(data.coverage);
  const last = objectValue(data.last_analysis);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let active = true;
    fetchExperimentExplain(String(selected.experiment_id ?? ""))
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

  return h(
    "div",
    { className: "eos-stack" },
    h(
      "div",
      { className: "eos-grid" },
      Card({
        title: "Experiment health",
        status: String(data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            contract: data.contract_version,
            last_analysis: last.analysis_run_id,
            last_status: last.status,
            protocols: data.protocols,
            quality: data.quality,
            auto_route: "disabled",
            promote: "disabled",
          },
        }),
      }),
      Card({
        title: "Coverage",
        status: String(data.quality ?? data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            protocols: coverage.protocols,
            assignments: coverage.assignments,
            observations: coverage.observations,
            current_results: coverage.current_results,
            production_protocols: coverage.production_protocols,
          },
        }),
      }),
    ),
    Card({
      title: "Experiments",
      children: DataTable({
        rows: experiments,
        columns: [
          { key: "experiment_id", label: "name" },
          { key: "protocol_version", label: "version" },
          { key: "state", label: "state" },
          { key: "treatment_dimension", label: "treatment" },
          { key: "design", label: "design" },
          { key: "conclusion", label: "conclusion" },
        ],
        empty: "No pre-registered experiments.",
        onSelect: setSelected,
      }),
    }),
    selected
      ? Card({
          title: "WHY",
          children: KeyValues({
            value: {
              protocol_hash: why.protocol_hash || detail?.protocol_hash,
              hypothesis: why.hypothesis,
              primary_metric: JSON.stringify(why.primary_metric ?? ""),
              effect: why.effect,
              uncertainty: JSON.stringify(why.uncertainty ?? {}),
              validity: JSON.stringify(why.validity ?? {}),
              reason: why.reason,
              conclusion: why.conclusion,
              missingness: JSON.stringify(why.missingness ?? {}),
              auto_route: "no",
            },
          }),
        })
      : null,
    h("p", { className: "eos-note" }, "Read-only. No deploy, promote, or auto-route controls."),
  );
}
