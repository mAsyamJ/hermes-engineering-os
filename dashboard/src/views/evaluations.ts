import { fetchEvaluationTask } from "../api";
import { Card, DataTable, KeyValues } from "../components/data";
import { h, sdk } from "../sdk";
import { arrayValue, objectValue } from "./helpers";

export function EvaluationsView({ data }: { data: Record<string, unknown> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const coverage = objectValue(data.coverage);
  const recent = arrayValue(data.recent);
  const last = objectValue(data.last_evaluation);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let active = true;
    fetchEvaluationTask(String(selected.task_id ?? ""), String(selected.board ?? "retropick-markets-release"))
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

  const summary = objectValue(detail?.summary);
  const vector = objectValue(summary.quality_vector);
  const run = objectValue(detail?.run);
  const artifact = objectValue(detail?.artifact);
  const projection = objectValue(detail?.projection);
  const results = arrayValue(detail?.results);
  return h(
    "div",
    { className: "eos-stack" },
    h(
      "div",
      { className: "eos-grid" },
      Card({
        title: "Evaluation health",
        status: String(data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            contract: data.contract_version,
            last_evaluation: last.evaluation_run_id,
            last_status: last.execution_status,
            evaluation_runs: data.evaluation_runs,
            quality: data.quality,
            canonical_store: data.canonical_store,
            detail: data.detail,
          },
        }),
      }),
      Card({
        title: "Coverage",
        status: String(data.quality ?? data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            production_tasks_seen: coverage.production_tasks_seen,
            eligible: coverage.eligible,
            evaluated: coverage.evaluated,
            insufficient_evidence: coverage.insufficient_evidence,
            unsupported: coverage.unsupported,
          },
        }),
      }),
      Card({
        title: "Results",
        status: String(data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            verified_pass: coverage.verified_pass,
            verified_fail: coverage.verified_fail,
            partial: coverage.partial,
            error: coverage.error,
          },
        }),
      }),
    ),
    h(
      "p",
      { className: "eos-note" },
      "Quality is a vector of independent dimensions. There is no canonical 0–100 score. Missing artifacts stay INSUFFICIENT_EVIDENCE.",
    ),
    Card({
      title: "Recent evaluations",
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: recent,
        columns: [
          { key: "task_id", label: "Task" },
          { key: "candidate_artifact_hash", label: "Artifact" },
          { key: "profile_id", label: "Profile" },
          { key: "summary_state", label: "Result" },
          { key: "eligibility", label: "Eligibility" },
          { key: "execution_status", label: "Execution" },
        ],
        empty: "No evaluations yet. Historical production tasks are expected to remain INSUFFICIENT_EVIDENCE.",
        onSelect: (row) => setSelected(row),
      }),
    }),
    selected
      ? Card({
          title: `WHY · ${String(selected.task_id)}`,
          status: String(summary.summary_state ?? detail?.status ?? "UNKNOWN"),
          children: h(
            "div",
            { className: "eos-stack" },
            h("p", { className: "eos-note" }, String(summary.reason ?? detail?.status ?? "Select a row.")),
            KeyValues({
              value: {
                eligibility: run.eligibility,
                profile: run.profile_id,
                profile_version: run.profile_version,
                candidate_hash: run.candidate_artifact_hash,
                baseline_hash: run.baseline_artifact_hash,
                trace_id: run.trace_id,
                artifact_method: artifact.method,
                projection: projection.status,
                correctness: vector.correctness,
                tests: vector.tests,
                build: vector.build,
                regression: vector.regression,
                lint: vector.lint,
                typecheck: vector.typecheck,
                security: vector.security,
                architecture: vector.architecture,
                acceptance: vector.acceptance,
                ci: vector.ci,
              },
            }),
            results.length
              ? DataTable({
                  rows: results,
                  columns: [
                    { key: "evaluator_id", label: "Evaluator" },
                    { key: "subject", label: "Subject" },
                    { key: "verdict", label: "Verdict" },
                    { key: "command", label: "Command" },
                    { key: "exit_code", label: "Exit" },
                  ],
                  empty: "No evaluator rows",
                })
              : h("p", { className: "eos-note" }, "No evaluator results (typical for INSUFFICIENT_EVIDENCE)."),
          ),
        })
      : null,
  );
}
