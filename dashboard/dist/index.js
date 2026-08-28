/* Hermes Engineering OS dashboard — generated; do not edit */
"use strict";
(() => {
  // src/sdk.ts
  function sdk() {
    const value = window.__HERMES_PLUGIN_SDK__;
    if (!value?.React || !value.hooks || !value.fetchJSON) {
      throw new Error("Hermes dashboard SDK 1.1 is unavailable");
    }
    return value;
  }
  var h = (...args) => sdk().React.createElement(...args);

  // src/api.ts
  var BASE = "/api/plugins/engineering-os";
  function fetchView(view) {
    return sdk().fetchJSON(`${BASE}/${view}`);
  }
  function fetchTask(taskId) {
    return sdk().fetchJSON(`${BASE}/tasks/${encodeURIComponent(taskId)}`);
  }
  function fetchRun(runId) {
    return sdk().fetchJSON(`${BASE}/runs/${runId}`);
  }
  function fetchAnalyticsTask(taskId, board) {
    const query = board ? `?board=${encodeURIComponent(board)}` : "";
    return sdk().fetchJSON(`${BASE}/analytics/tasks/${encodeURIComponent(taskId)}${query}`);
  }
  function fetchEvaluationTask(taskId, board) {
    const query = board ? `?board=${encodeURIComponent(board)}` : "";
    return sdk().fetchJSON(`${BASE}/evaluations/tasks/${encodeURIComponent(taskId)}${query}`);
  }
  function fetchPerformanceWhy(metric, cohort) {
    const params = new URLSearchParams({ metric, cohort: cohort || "production_all" });
    return sdk().fetchJSON(`${BASE}/performance/why?${params.toString()}`);
  }
  function fetchExperimentExplain(experimentId) {
    return sdk().fetchJSON(`${BASE}/experiments/${encodeURIComponent(experimentId)}/explain`);
  }
  function fetchAdaptationExplain(objectId) {
    return sdk().fetchJSON(`${BASE}/adaptation/explain/${encodeURIComponent(objectId)}`);
  }

  // src/components/status.ts
  var LABEL = {
    AVAILABLE: "Available",
    DEGRADED: "Degraded",
    UNKNOWN: "Unknown",
    BLOCKED_AUTH: "Blocked auth",
    HEALTHY: "Healthy",
    ACTIVE: "Active",
    DOWN: "Down"
  };
  function StatusBadge({ status }) {
    return h(
      "span",
      { className: `eos-status eos-status--${status.toLowerCase().replace("_", "-")}` },
      LABEL[status] ?? status
    );
  }
  function EmptyState({ children }) {
    return h("div", { className: "eos-empty" }, children);
  }
  function ErrorState({ message, retry }) {
    return h(
      "div",
      { className: "eos-error", role: "alert" },
      h("strong", null, "Evidence unavailable"),
      h("span", null, message),
      h("button", { type: "button", onClick: retry }, "Retry")
    );
  }

  // src/components/data.ts
  function Card(props) {
    return h(
      "section",
      { className: "eos-card" },
      h(
        "header",
        { className: "eos-card__header" },
        h("h3", null, props.title),
        props.status ? StatusBadge({ status: props.status }) : null
      ),
      h("div", { className: "eos-card__body" }, props.children)
    );
  }
  function KeyValues({ value }) {
    const rows = Object.entries(value).filter(([, item]) => {
      return item == null || ["string", "number", "boolean"].includes(typeof item);
    });
    if (!rows.length) return EmptyState({ children: "No scalar evidence reported." });
    return h(
      "dl",
      { className: "eos-kv" },
      ...rows.map(
        ([key, item]) => h(
          "div",
          { className: "eos-kv__row", key },
          h("dt", null, key.replace(/_/g, " ")),
          h("dd", null, item == null ? "\u2014" : String(item))
        )
      )
    );
  }
  function DataTable(props) {
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
            ...props.columns.map((column) => h("th", { key: column.key }, column.label))
          )
        ),
        h(
          "tbody",
          null,
          ...props.rows.map(
            (row, index) => h(
              "tr",
              {
                key: String(row.id ?? row.name ?? index),
                onClick: props.onSelect ? () => props.onSelect?.(row) : void 0,
                className: props.onSelect ? "eos-table__selectable" : void 0
              },
              ...props.columns.map(
                (column) => h("td", { key: column.key }, formatCell(row[column.key]))
              )
            )
          )
        )
      )
    );
  }
  function formatCell(value) {
    if (value == null || value === "") return "\u2014";
    if (typeof value === "boolean") return value ? "yes" : "no";
    if (typeof value === "object") return JSON.stringify(value);
    const text = String(value);
    if (/^https?:\/\/127\.0\.0\.1:6006\//.test(text)) {
      return h("a", { href: text, className: "eos-link", target: "_blank", rel: "noreferrer" }, "Open in Phoenix");
    }
    return text;
  }

  // src/views/helpers.ts
  function evidenceData(value, fallback) {
    if (!value || typeof value !== "object") return fallback;
    const candidate = value;
    return candidate.data === void 0 ? fallback : candidate.data;
  }
  function objectValue(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }
  function arrayValue(value) {
    return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") : [];
  }

  // src/views/analytics.ts
  function AnalyticsView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const coverage = objectValue(data.coverage);
    const recent = arrayValue(data.recent);
    const last = objectValue(data.last_materialization);
    const [selected, setSelected] = useState(null);
    const [detail, setDetail] = useState(null);
    useEffect(() => {
      if (!selected) {
        setDetail(null);
        return;
      }
      let active = true;
      fetchAnalyticsTask(String(selected.task_id ?? ""), String(selected.board ?? "retropick-markets-release")).then((value) => {
        if (active) setDetail(value);
      }).catch(() => {
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
              detail: data.detail
            }
          })
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
              unknown_intervention: coverage.unknown_intervention
            }
          })
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
              unknown_outcome: coverage.unknown_outcome
            }
          })
        })
      ),
      h(
        "p",
        { className: "eos-note" },
        "UNKNOWN rows stay in the denominator. Kanban DONE is not verified success. GitHub BLOCKED_AUTH is not failure."
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
            { key: "evidence_grade", label: "Evidence grade" }
          ],
          empty: "No derived outcomes yet.",
          onSelect: (row) => setSelected(row)
        })
      }),
      selected ? Card({
        title: `WHY \xB7 ${String(selected.task_id)}`,
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
              kanban: selected.task_id ? `/engineering-os` : null
            }
          }),
          traces.length ? DataTable({
            rows: traces,
            columns: [
              { key: "trace_id", label: "Trace" },
              { key: "run_id", label: "Run" },
              { key: "phoenix_url", label: "Phoenix" },
              { key: "llm_call_count", label: "LLM" },
              { key: "tool_call_count", label: "Tools" }
            ],
            empty: "No traces"
          }) : h("p", { className: "eos-note" }, "No Phoenix traces correlated for this task."),
          github.evidence_state === "BLOCKED_AUTH" ? h("p", { className: "eos-note" }, "GitHub evidence: BLOCKED_AUTH. No PR URL is invented.") : null
        )
      }) : null
    );
  }

  // src/views/evaluations.ts
  function EvaluationsView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const coverage = objectValue(data.coverage);
    const recent = arrayValue(data.recent);
    const last = objectValue(data.last_evaluation);
    const [selected, setSelected] = useState(null);
    const [detail, setDetail] = useState(null);
    useEffect(() => {
      if (!selected) {
        setDetail(null);
        return;
      }
      let active = true;
      fetchEvaluationTask(String(selected.task_id ?? ""), String(selected.board ?? "retropick-markets-release")).then((value) => {
        if (active) setDetail(value);
      }).catch(() => {
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
              detail: data.detail
            }
          })
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
              unsupported: coverage.unsupported
            }
          })
        }),
        Card({
          title: "Results",
          status: String(data.status ?? "UNKNOWN"),
          children: KeyValues({
            value: {
              verified_pass: coverage.verified_pass,
              verified_fail: coverage.verified_fail,
              partial: coverage.partial,
              error: coverage.error
            }
          })
        })
      ),
      h(
        "p",
        { className: "eos-note" },
        "Quality is a vector of independent dimensions. There is no canonical 0\u2013100 score. Missing artifacts stay INSUFFICIENT_EVIDENCE."
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
            { key: "execution_status", label: "Execution" }
          ],
          empty: "No evaluations yet. Historical production tasks are expected to remain INSUFFICIENT_EVIDENCE.",
          onSelect: (row) => setSelected(row)
        })
      }),
      selected ? Card({
        title: `WHY \xB7 ${String(selected.task_id)}`,
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
              ci: vector.ci
            }
          }),
          results.length ? DataTable({
            rows: results,
            columns: [
              { key: "evaluator_id", label: "Evaluator" },
              { key: "subject", label: "Subject" },
              { key: "verdict", label: "Verdict" },
              { key: "command", label: "Command" },
              { key: "exit_code", label: "Exit" }
            ],
            empty: "No evaluator rows"
          }) : h("p", { className: "eos-note" }, "No evaluator results (typical for INSUFFICIENT_EVIDENCE).")
        )
      }) : null
    );
  }

  // src/views/agents.ts
  function AgentsView({ data }) {
    const profileEvidence = objectValue(data.profiles);
    const workerEvidence = objectValue(data.workers);
    const profiles = arrayValue(evidenceData(profileEvidence, []));
    const workers = arrayValue(evidenceData(workerEvidence, []));
    return h(
      "div",
      { className: "eos-grid" },
      Card({
        title: `Profiles \xB7 ${profiles.length}`,
        status: String(profileEvidence.status ?? "UNKNOWN"),
        children: DataTable({
          rows: profiles,
          columns: [
            { key: "name", label: "Profile" },
            { key: "model", label: "Model" },
            { key: "provider", label: "Provider" },
            { key: "gateway_running", label: "Gateway" },
            { key: "skill_count", label: "Skills" }
          ],
          empty: "No Hermes profiles discovered."
        })
      }),
      Card({
        title: `Active workers \xB7 ${workers.length}`,
        status: String(workerEvidence.status ?? "UNKNOWN"),
        children: DataTable({
          rows: workers,
          columns: [
            { key: "profile", label: "Profile" },
            { key: "hermes_kanban_task_id", label: "Task ID" },
            { key: "hermes_kanban_run_id", label: "Run ID" },
            { key: "worker_pid", label: "PID" },
            { key: "pid_alive", label: "Alive" }
          ],
          empty: "No currently running Kanban workers."
        })
      })
    );
  }

  // src/views/github.ts
  function GitHubView({ data }) {
    const localEvidence = objectValue(data.local_git);
    const repositories = arrayValue(evidenceData(localEvidence, []));
    const apiEvidence = objectValue(data.github_api);
    return h(
      "div",
      { className: "eos-stack" },
      h(
        "div",
        { className: "eos-toolbar" },
        h("p", null, "Repository, branch, commit, PR, and checks are read-only evidence."),
        h("span", { className: "eos-lock" }, "Mutation disabled")
      ),
      Card({
        title: "Local Git repositories",
        status: String(localEvidence.status ?? "UNKNOWN"),
        children: DataTable({
          rows: repositories,
          columns: [
            { key: "label", label: "Repository" },
            { key: "branch", label: "Branch" },
            { key: "head", label: "Commit" },
            { key: "default_branch", label: "Default" },
            { key: "dirty", label: "Dirty" }
          ],
          empty: "No allowlisted repositories are available."
        })
      }),
      Card({
        title: "GitHub API",
        status: String(apiEvidence.status ?? "UNKNOWN"),
        children: KeyValues({
          value: {
            ...objectValue(apiEvidence.data),
            detail: apiEvidence.detail
          }
        })
      })
    );
  }

  // src/views/observability.ts
  function ObservabilityView({ data }) {
    const traces = arrayValue(data.recent_traces);
    const hermesOtel = objectValue(data.hermes_otel);
    const last = objectValue(data.last_trace);
    return h(
      "div",
      { className: "eos-stack" },
      h(
        "div",
        { className: "eos-grid" },
        Card({
          title: "hermes-otel",
          status: String(hermesOtel.status ?? data.status ?? "UNKNOWN"),
          children: KeyValues({
            value: {
              installed: hermesOtel.installed,
              version: hermesOtel.version,
              sdk_available: hermesOtel.sdk_available,
              fail_open: data.fail_open,
              export: data.export
            }
          })
        }),
        Card({
          title: "Phoenix",
          status: String(data.phoenix ?? "UNKNOWN"),
          children: KeyValues({
            value: {
              url: data.phoenix_url,
              last_trace: last.trace_id,
              detail: data.detail
            }
          })
        }),
        Card({
          title: "PostgreSQL",
          status: String(data.postgresql ?? "UNKNOWN"),
          children: KeyValues({
            value: {
              container: "hermes-eos-postgres",
              host_port: "none",
              isolation: "dedicated observability volume"
            }
          })
        })
      ),
      Card({
        title: "Recent runs",
        status: String(data.status ?? "UNKNOWN"),
        children: DataTable({
          rows: traces,
          columns: [
            { key: "hermes_kanban_task_id", label: "Task" },
            { key: "hermes_kanban_run_id", label: "Run" },
            { key: "agent", label: "Agent" },
            { key: "model", label: "Model" },
            { key: "duration_ms", label: "Duration" },
            { key: "llm_calls", label: "LLM" },
            { key: "tool_calls", label: "Tools" },
            { key: "trace_id", label: "Trace" },
            { key: "phoenix_url", label: "Open in Phoenix" }
          ],
          empty: "No traces reported by Phoenix yet."
        })
      }),
      h(
        "p",
        { className: "eos-note" },
        "Observability is derived and fail-open. Hermes Kanban remains the only task authority. Phoenix is the detailed viewer."
      )
    );
  }

  // src/views/overview.ts
  function OverviewView({ data }) {
    const runtimeEvidence = objectValue(data.runtime);
    const runtime = objectValue(evidenceData(runtimeEvidence, {}));
    const storage = objectValue(runtime.storage);
    const kanbanEvidence = objectValue(data.kanban);
    const kanban = objectValue(evidenceData(kanbanEvidence, {}));
    const github = objectValue(data.github);
    const githubApi = objectValue(github.github_api);
    return h(
      "div",
      { className: "eos-grid eos-grid--overview" },
      Card({
        title: "Hermes runtime",
        status: String(runtimeEvidence.status ?? "UNKNOWN"),
        children: KeyValues({ value: runtime })
      }),
      Card({
        title: "Canonical Kanban",
        status: String(kanbanEvidence.status ?? "UNKNOWN"),
        children: KeyValues({ value: kanban })
      }),
      Card({
        title: "Storage",
        children: KeyValues({ value: storage })
      }),
      Card({
        title: "GitHub API",
        status: String(githubApi.status ?? "UNKNOWN"),
        children: KeyValues({ value: objectValue(githubApi.data) })
      })
    );
  }

  // src/views/performance.ts
  function metricLabel(row) {
    const value = row.value;
    const tier = String(row.evidence_tier ?? "NO_DATA");
    if (value == null || tier === "NO_DATA") return "INSUFFICIENT DATA";
    if (typeof value === "number" && String(row.unit) === "proportion") {
      return `${(value * 100).toFixed(1)}% \xB7 ${tier}`;
    }
    return `${String(value)} \xB7 ${tier}`;
  }
  function PerformanceView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const coverage = objectValue(data.coverage);
    const metrics = arrayValue(data.metrics);
    const insights = arrayValue(data.insights);
    const failures = arrayValue(data.failures);
    const profiles = arrayValue(data.profiles);
    const comparisons = arrayValue(data.comparisons);
    const trends = arrayValue(data.trends);
    const last = objectValue(data.last_materialization);
    const [selected, setSelected] = useState(null);
    const [detail, setDetail] = useState(null);
    useEffect(() => {
      if (!selected) {
        setDetail(null);
        return;
      }
      let active = true;
      fetchPerformanceWhy(String(selected.metric_id ?? "lifecycle_completion_rate"), String(selected.cohort_id ?? "production_all")).then((value) => {
        if (active) setDetail(value);
      }).catch(() => {
        if (active) setDetail({ status: "DEGRADED" });
      });
      return () => {
        active = false;
      };
    }, [selected]);
    const why = objectValue(detail?.why);
    const qualityRows = metrics.filter((row) => String(row.metric_id).startsWith("quality_"));
    const outcomeRows = metrics.filter(
      (row) => [
        "lifecycle_completion_rate",
        "verified_success_rate",
        "first_pass_rate",
        "retry_rate",
        "rework_rate",
        "human_intervention_detection_rate"
      ].includes(String(row.metric_id))
    );
    const efficiencyRows = metrics.filter(
      (row) => ["task_wall_seconds", "run_wall_seconds", "trace_wall_seconds", "llm_call_count", "tool_call_count", "token_total", "cost_known_rate"].includes(
        String(row.metric_id)
      )
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
              causal: "false \u2014 observational only"
            }
          })
        }),
        Card({
          title: "Coverage",
          status: String(data.quality ?? data.status ?? "UNKNOWN"),
          children: KeyValues({
            value: {
              production_tasks: coverage.production_tasks,
              current_aggregates: coverage.current_aggregates,
              quality_insufficient_rows: coverage.quality_insufficient_rows,
              lifecycle_present: coverage.lifecycle_present
            }
          })
        })
      ),
      h(
        "p",
        { className: "eos-note" },
        "Coverage before ranking. UNKNOWN is not failure. There is no BEST MODEL. Phase 5 does not route Hermes."
      ),
      qualityKnown ? null : h("p", { className: "eos-note" }, "QUALITY PERFORMANCE: INSUFFICIENT DATA \u2014 0 production tasks have Phase 4 evaluation coverage."),
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
            { key: "evidence_tier", label: "Tier" }
          ],
          empty: "INSUFFICIENT DATA",
          onSelect: (row) => setSelected(row)
        })
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
            { key: "evidence_tier", label: "Tier" }
          ],
          empty: "INSUFFICIENT DATA",
          onSelect: (row) => setSelected(row)
        })
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
            { key: "evidence_tier", label: "Tier" }
          ],
          empty: "INSUFFICIENT DATA",
          onSelect: (row) => setSelected(row)
        })
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
            { key: "evidence_tier", label: "Tier" }
          ],
          empty: "NO_DATA"
        })
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
            { key: "evidence_tier", label: "Tier" }
          ],
          empty: "INSUFFICIENT DATA",
          onSelect: (row) => setSelected(row)
        })
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
            { key: "confounding_status", label: "Confounding" }
          ],
          empty: "INSUFFICIENT DATA"
        })
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
            { key: "right_n", label: "Current N" }
          ],
          empty: "INSUFFICIENT DATA"
        })
      }),
      Card({
        title: "Insights",
        children: insights.length ? h(
          "ul",
          { className: "eos-note" },
          ...insights.map((item, index) => h("li", { key: index }, String(item.body ?? "")))
        ) : h("p", { className: "eos-note" }, "No insights yet.")
      }),
      selected ? Card({
        title: `WHY \xB7 ${String(selected.metric_id)}`,
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
              prompt_version_performance: why.prompt_version_performance
            }
          })
        )
      }) : null
    );
  }

  // src/views/experiments.ts
  function ExperimentsView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const experiments = arrayValue(data.experiments);
    const coverage = objectValue(data.coverage);
    const last = objectValue(data.last_analysis);
    const [selected, setSelected] = useState(null);
    const [detail, setDetail] = useState(null);
    useEffect(() => {
      if (!selected) {
        setDetail(null);
        return;
      }
      let active = true;
      fetchExperimentExplain(String(selected.experiment_id ?? "")).then((value) => {
        if (active) setDetail(value);
      }).catch(() => {
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
              promote: "disabled"
            }
          })
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
              production_protocols: coverage.production_protocols
            }
          })
        })
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
            { key: "conclusion", label: "conclusion" }
          ],
          empty: "No pre-registered experiments.",
          onSelect: setSelected
        })
      }),
      selected ? Card({
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
            auto_route: "no"
          }
        })
      }) : null,
      h("p", { className: "eos-note" }, "Read-only. No deploy, promote, or auto-route controls.")
    );
  }

  // src/views/adaptation.ts
  function AdaptationView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const recommendations = arrayValue(data.recommendations);
    const policies = arrayValue(data.policies);
    const rollbacks = arrayValue(data.rollbacks);
    const canaries = objectValue(data.canaries);
    const [selected, setSelected] = useState(null);
    const [detail, setDetail] = useState(null);
    useEffect(() => {
      if (!selected) {
        setDetail(null);
        return;
      }
      const objectId = String(selected.recommendation_id || selected.policy_id || selected.policy_hash || "");
      if (!objectId) {
        setDetail(null);
        return;
      }
      let active = true;
      fetchAdaptationExplain(objectId).then((value) => {
        if (active) setDetail(value);
      }).catch(() => {
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
          title: "Adaptation readiness",
          status: String(data.status ?? "UNKNOWN"),
          children: KeyValues({
            value: {
              contract: data.contract_version,
              production_evidence: data.production_evidence || data.production_recommendation,
              human_approval_boundary: data.human_approval_boundary || data.production_approval,
              memory_isolation: data.memory_isolation,
              runtime_actuation: data.runtime_actuation || data.runtime_integration,
              production_adaptation: data.production_adaptation || "DISABLED",
              auto_promote: "forbidden",
              kill_switch: data.kill_switch
            }
          })
        }),
        Card({
          title: "Production adaptation",
          status: "BLOCKED",
          children: KeyValues({
            value: {
              evidence: "BLOCKED_EVIDENCE",
              approval: "BLOCKED_CAPABILITY",
              memory: "BLOCKED_CAPABILITY",
              runtime: "BLOCKED_RUNTIME_INTEGRATION",
              fixture_qualification: "separate from production"
            }
          })
        })
      ),
      Card({
        title: "Recommendations",
        children: DataTable({
          rows: recommendations,
          columns: [
            { key: "experiment_id", label: "experiment" },
            { key: "classification", label: "class" },
            { key: "state", label: "state" },
            { key: "scope", label: "scope" },
            { key: "treatment_dimension", label: "treatment" },
            { key: "production_promotable", label: "prod?" }
          ],
          empty: "No recommendations.",
          onSelect: setSelected
        })
      }),
      Card({
        title: "Policies",
        children: DataTable({
          rows: policies,
          columns: [
            { key: "policy_id", label: "policy" },
            { key: "policy_version", label: "version" },
            { key: "scope", label: "scope" },
            { key: "policy_hash", label: "hash" }
          ],
          empty: "No compiled policies.",
          onSelect: setSelected
        })
      }),
      Card({
        title: "Canary / rollback",
        children: KeyValues({
          value: {
            plans: Array.isArray(canaries.plans) ? canaries.plans.length : 0,
            auto_promote: "no",
            rollbacks: rollbacks.length
          }
        })
      }),
      selected ? Card({
        title: "WHY",
        children: KeyValues({
          value: {
            kind: detail?.kind,
            reason: why.reason || selected.reason,
            classification: why.classification || selected.classification,
            conclusion: why.conclusion,
            production_promotable: why.production_promotable,
            deploy_now: "no"
          }
        })
      }) : null,
      h("p", { className: "eos-note" }, "Read-only. PRODUCTION ADAPTATION DISABLED. No deploy, approve, or auto-optimize controls.")
    );
  }

  // src/views/plugins.ts
  function PluginsView({ data }) {
    const payload = objectValue(evidenceData(data, {}));
    const plugins = arrayValue(payload.plugins);
    return Card({
      title: `User plugins \xB7 ${plugins.length}`,
      status: String(data.status ?? "UNKNOWN"),
      children: plugins.length ? DataTable({
        rows: plugins,
        columns: [
          { key: "name", label: "Plugin" },
          { key: "version", label: "Version" },
          { key: "status", label: "Status" },
          { key: "dashboard_manifest", label: "Dashboard" },
          { key: "is_symlink", label: "Symlink" }
        ],
        empty: "No user plugins discovered."
      }) : KeyValues({ value: payload })
    });
  }

  // src/views/runs.ts
  function RunsView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const rows = Array.isArray(data.data) ? data.data : [];
    const [selectedId, setSelectedId] = useState(null);
    const [detail, setDetail] = useState(null);
    const [detailError, setDetailError] = useState(null);
    useEffect(() => {
      if (selectedId == null) {
        setDetail(null);
        setDetailError(null);
        return;
      }
      let active = true;
      setDetail(null);
      setDetailError(null);
      fetchRun(selectedId).then((value) => {
        if (active) setDetail(value);
      }).catch((reason) => {
        if (active) setDetailError(reason instanceof Error ? reason.message : String(reason));
      });
      return () => {
        active = false;
      };
    }, [selectedId]);
    const traces = arrayValue(objectValue(detail?.observability).data);
    return h(
      "div",
      { className: "eos-stack" },
      Card({
        title: `Runs \xB7 ${rows.length}`,
        status: data.status,
        children: DataTable({
          rows,
          columns: [
            { key: "id", label: "Kanban run ID" },
            { key: "task_id", label: "Kanban task ID" },
            { key: "profile", label: "Profile" },
            { key: "status", label: "Status" },
            { key: "worker_pid", label: "PID" },
            { key: "outcome", label: "Outcome" }
          ],
          empty: "No run history reported by Hermes Kanban.",
          onSelect: (row) => setSelectedId(Number(row.id))
        })
      }),
      selectedId != null ? Card({
        title: `TRACE \xB7 run ${selectedId}`,
        status: String(objectValue(detail?.observability).status ?? (detailError ? "DEGRADED" : "UNKNOWN")),
        children: traces.length ? DataTable({
          rows: traces,
          columns: [
            { key: "trace_id", label: "Trace" },
            { key: "hermes_kanban_task_id", label: "Task" },
            { key: "session_id", label: "Session" },
            { key: "model", label: "Model" },
            { key: "llm_calls", label: "LLM" },
            { key: "tool_calls", label: "Tools" },
            { key: "phoenix_url", label: "Open in Phoenix" }
          ],
          empty: "No correlated traces."
        }) : h(
          "p",
          { className: "eos-note" },
          detailError || "No exact Kanban-to-trace match for this run."
        )
      }) : h("p", { className: "eos-note" }, "Select a run to load exact TRACE evidence.")
    );
  }

  // src/views/tasks.ts
  function TasksView({ data }) {
    const { useEffect, useState } = sdk().hooks;
    const rows = Array.isArray(data.data) ? data.data : [];
    const [selectedId, setSelectedId] = useState(null);
    const [detail, setDetail] = useState(null);
    const [detailError, setDetailError] = useState(null);
    useEffect(() => {
      if (!selectedId) {
        setDetail(null);
        setDetailError(null);
        return;
      }
      let active = true;
      setDetail(null);
      setDetailError(null);
      fetchTask(selectedId).then((value) => {
        if (active) setDetail(value);
      }).catch((reason) => {
        if (active) setDetailError(reason instanceof Error ? reason.message : String(reason));
      });
      return () => {
        active = false;
      };
    }, [selectedId]);
    const traces = arrayValue(objectValue(detail?.observability).data);
    return h(
      "div",
      { className: "eos-stack" },
      h(
        "div",
        { className: "eos-toolbar" },
        h("p", null, "Hermes Kanban is the only task lifecycle authority."),
        h("a", { href: "/kanban", className: "eos-link" }, "Open native Kanban")
      ),
      Card({
        title: `Tasks \xB7 ${rows.length}`,
        status: data.status,
        children: DataTable({
          rows,
          columns: [
            { key: "id", label: "Kanban task ID" },
            { key: "title", label: "Title" },
            { key: "status", label: "Status" },
            { key: "assignee", label: "Assignee" },
            { key: "branch_name", label: "Branch" },
            { key: "current_run_id", label: "Run" }
          ],
          empty: "No tasks reported by the active Hermes board.",
          onSelect: (row) => setSelectedId(String(row.id ?? ""))
        })
      }),
      selectedId ? Card({
        title: `TRACE \xB7 ${selectedId}`,
        status: String(objectValue(detail?.observability).status ?? (detailError ? "DEGRADED" : "UNKNOWN")),
        children: h(
          "div",
          { className: "eos-stack" },
          detailError ? h("p", { className: "eos-note" }, detailError) : null,
          traces.length ? DataTable({
            rows: traces,
            columns: [
              { key: "trace_id", label: "Trace" },
              { key: "hermes_kanban_run_id", label: "Run" },
              { key: "session_id", label: "Session" },
              { key: "model", label: "Model" },
              { key: "llm_calls", label: "LLM" },
              { key: "tool_calls", label: "Tools" },
              { key: "phoenix_url", label: "Open in Phoenix" }
            ],
            empty: "No correlated traces."
          }) : h("p", { className: "eos-note" }, "No exact Kanban-to-trace match for this task."),
          detail ? KeyValues({ value: objectValue(detail.correlation) }) : null
        )
      }) : h("p", { className: "eos-note" }, "Select a task to load exact TRACE evidence.")
    );
  }

  // src/views/workspaces.ts
  function WorkspacesView({ data }) {
    const payload = objectValue(evidenceData(data, {}));
    const repositories = arrayValue(payload.repositories);
    const taskWorkspaces = arrayValue(payload.task_workspaces);
    return h(
      "div",
      { className: "eos-stack" },
      h(
        "p",
        { className: "eos-note" },
        "Fixed hierarchy: configured repository \u2192 Git worktree \u2192 canonical Hermes run. This view never creates or removes worktrees."
      ),
      Card({
        title: `Configured repositories \xB7 ${repositories.length}`,
        status: String(data.status ?? "UNKNOWN"),
        children: DataTable({
          rows: repositories,
          columns: [
            { key: "label", label: "Repository" },
            { key: "path", label: "Path" },
            { key: "exists", label: "Exists" },
            { key: "mode", label: "Mode" },
            { key: "worktrees", label: "Worktrees" }
          ],
          empty: "No configured repository evidence."
        })
      }),
      Card({
        title: `Task workspaces \xB7 ${taskWorkspaces.length}`,
        children: DataTable({
          rows: taskWorkspaces,
          columns: [
            { key: "hermes_kanban_task_id", label: "Task ID" },
            { key: "path", label: "Workspace" },
            { key: "branch", label: "Branch" },
            { key: "status", label: "Status" }
          ],
          empty: "No task workspaces reported by Hermes Kanban."
        })
      })
    );
  }

  // src/app.ts
  var VIEWS = [
    { id: "overview", label: "Overview" },
    { id: "tasks", label: "Tasks" },
    { id: "runs", label: "Runs" },
    { id: "agents", label: "Agents" },
    { id: "plugins", label: "Plugins" },
    { id: "github", label: "GitHub" },
    { id: "workspaces", label: "Workspaces" },
    { id: "observability", label: "Observability" },
    { id: "analytics", label: "Analytics" },
    { id: "evaluations", label: "Evaluations" },
    { id: "performance", label: "Performance" },
    { id: "experiments", label: "Experiments" },
    { id: "adaptation", label: "Adaptation" }
  ];
  function EngineeringOSPage() {
    const { useEffect, useState } = sdk().hooks;
    const [view, setView] = useState("overview");
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [revision, setRevision] = useState(0);
    useEffect(() => {
      let active = true;
      setData(null);
      setError(null);
      fetchView(view).then((value) => {
        if (active) setData(value);
      }).catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : String(reason));
      });
      return () => {
        active = false;
      };
    }, [view, revision]);
    return h(
      "div",
      { className: "eos-shell" },
      h(
        "header",
        { className: "eos-hero" },
        h(
          "div",
          null,
          h("p", { className: "eos-eyebrow" }, "Hermes Agent \xB7 operator evidence"),
          h("h1", null, "Engineering OS"),
          h(
            "p",
            { className: "eos-subtitle" },
            "Live runtime, canonical Kanban, workspace, Git, GitHub, observability, derived outcomes, deterministic evaluations, observational performance, controlled experiments, and controlled adaptation. Read-only by design."
          )
        ),
        h("span", { className: "eos-readonly" }, "READ ONLY")
      ),
      h(
        "nav",
        { className: "eos-nav", "aria-label": "Engineering OS views" },
        ...VIEWS.map(
          (item) => h(
            "button",
            {
              key: item.id,
              type: "button",
              className: view === item.id ? "eos-nav__item is-active" : "eos-nav__item",
              onClick: () => setView(item.id)
            },
            item.label
          )
        )
      ),
      h(
        "main",
        { className: "eos-main", "data-view": view },
        error ? ErrorState({ message: error, retry: () => setRevision((old) => old + 1) }) : data == null ? h("div", { className: "eos-loading", role: "status" }, "Loading live evidence\u2026") : renderView(view, data)
      )
    );
  }
  function renderView(view, data) {
    const object = data;
    switch (view) {
      case "overview":
        return OverviewView({ data: object });
      case "tasks":
        return h(TasksView, { data });
      case "runs":
        return h(RunsView, { data });
      case "agents":
        return AgentsView({ data: object });
      case "plugins":
        return PluginsView({ data: object });
      case "github":
        return GitHubView({ data: object });
      case "workspaces":
        return WorkspacesView({ data: object });
      case "observability":
        return ObservabilityView({ data: object });
      case "analytics":
        return h(AnalyticsView, { data: object });
      case "evaluations":
        return h(EvaluationsView, { data: object });
      case "performance":
        return h(PerformanceView, { data: object });
      case "experiments":
        return h(ExperimentsView, { data: object });
      case "adaptation":
        return h(AdaptationView, { data: object });
    }
  }
  function FooterStatus() {
    return h("span", { className: "eos-footer-status" }, "Engineering OS \xB7 read-only");
  }

  // src/index.ts
  (function register() {
    const sdk2 = window.__HERMES_PLUGIN_SDK__;
    const plugins = window.__HERMES_PLUGINS__;
    if (!sdk2 || !plugins?.register) {
      console.error("[engineering-os] Hermes dashboard SDK 1.1 unavailable");
      return;
    }
    plugins.register("engineering-os", EngineeringOSPage);
    if (plugins.registerSlot) {
      plugins.registerSlot("engineering-os", "footer-right", FooterStatus);
    }
  })();
})();
