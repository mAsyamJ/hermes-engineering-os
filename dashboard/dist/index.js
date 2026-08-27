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
    { id: "observability", label: "Observability" }
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
            "Live runtime, canonical Kanban, workspace, Git, and GitHub evidence. Read-only by design."
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
