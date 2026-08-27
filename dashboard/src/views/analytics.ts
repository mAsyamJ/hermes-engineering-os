import { fetchAnalyticsTask } from "../api";
import { Card, DataTable, KeyValues } from "../components/data";
import { h, sdk } from "../sdk";
import { arrayValue, objectValue } from "./helpers";

export function AnalyticsView({ data }: { data: Record<string, unknown> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const coverage = objectValue(data.coverage);
  const recent = arrayValue(data.recent);
  const last = objectValue(data.last_materialization);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let active = true;
    fetchAnalyticsTask(String(selected.task_id ?? ""), String(selected.board ?? "retropick-markets-release"))
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

  const facts = objectValue(detail?.facts);
  const traces = arrayValue(facts.traces);
  const github = objectValue(facts.github);
  const git = objectValue(facts.git);
  return h(
    "div",
    { className: "eos-stack" },
    h(
      "div",
      { className: "eos-grid" },
      Card({
        title: "Analytics health",
        status: String(data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            last_materialization: last.materialization_id,
            last_status: last.status,
            ended_at: last.ended_at,
            task_outcomes: data.task_outcomes,
            quality: data.quality,
            detail: data.detail,
          },
        }),
      }),
      Card({
        title: "Evidence coverage",
        status: String(data.quality ?? data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            eligible_production: coverage.eligible_production,
            with_trace_metrics: coverage.with_trace_metrics,
            with_git: coverage.with_git,
            github_blocked_auth: coverage.github_blocked_auth,
            with_github: coverage.with_github,
            with_objective_verification: coverage.with_objective_verification,
            unknown_first_pass: coverage.unknown_first_pass,
            unknown_intervention: coverage.unknown_intervention,
          },
        }),
      }),
      Card({
        title: "Outcomes",
        status: String(data.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            verified_success: coverage.verified_success,
            completed_unverified: coverage.completed_unverified,
            verified_failure: coverage.verified_failure,
            incomplete: coverage.incomplete,
            unknown_outcome: coverage.unknown_outcome,
          },
        }),
      }),
    ),
    h(
      "p",
      { className: "eos-note" },
      "UNKNOWN rows stay in the denominator. Kanban DONE is not verified success. GitHub BLOCKED_AUTH is not failure.",
    ),
    Card({
      title: "Recent production outcomes",
      status: String(data.status ?? "UNKNOWN"),
      children: DataTable({
        rows: recent,
        columns: [
          { key: "task_id", label: "Task" },
          { key: "status", label: "Status" },
          { key: "final_outcome", label: "Outcome" },
          { key: "first_pass_state", label: "First pass" },
          { key: "git_evidence_state", label: "Git" },
          { key: "github_evidence_state", label: "GitHub/CI" },
          { key: "evidence_grade", label: "Evidence grade" },
        ],
        empty: "No derived outcomes yet.",
        onSelect: (row) => setSelected(row),
      }),
    }),
    selected
      ? Card({
          title: `WHY · ${String(selected.task_id)}`,
          status: String(detail?.final_outcome ?? detail?.status ?? "UNKNOWN"),
          children: h(
            "div",
            { className: "eos-stack" },
            h("p", { className: "eos-note" }, String(detail?.reason ?? "Select a task to explain the outcome.")),
            KeyValues({
              value: {
                ruleset: detail?.ruleset,
                lifecycle_state: detail?.lifecycle_state,
                verification_state: detail?.verification_state,
                first_pass_state: detail?.first_pass_state,
                retry_count: detail?.retry_count,
                human_intervention_state: detail?.human_intervention_state,
                git_sha: git.commit_sha,
                github_state: github.evidence_state,
                kanban: selected.task_id ? `/engineering-os` : null,
              },
            }),
            traces.length
              ? DataTable({
                  rows: traces,
                  columns: [
                    { key: "trace_id", label: "Trace" },
                    { key: "run_id", label: "Run" },
                    { key: "phoenix_url", label: "Phoenix" },
                    { key: "llm_call_count", label: "LLM" },
                    { key: "tool_call_count", label: "Tools" },
                  ],
                  empty: "No traces",
                })
              : h("p", { className: "eos-note" }, "No Phoenix traces correlated for this task."),
            github.evidence_state === "BLOCKED_AUTH"
              ? h("p", { className: "eos-note" }, "GitHub evidence: BLOCKED_AUTH. No PR URL is invented.")
              : null,
          ),
        })
      : null,
  );
}
