import { fetchView } from "./api";
import { ErrorState } from "./components/status";
import { h, sdk } from "./sdk";
import type { ViewId } from "./types";
import { AnalyticsView } from "./views/analytics";
import { AgentsView } from "./views/agents";
import { GitHubView } from "./views/github";
import { ObservabilityView } from "./views/observability";
import { OverviewView } from "./views/overview";
import { PluginsView } from "./views/plugins";
import { RunsView } from "./views/runs";
import { TasksView } from "./views/tasks";
import { WorkspacesView } from "./views/workspaces";

const VIEWS: Array<{ id: ViewId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "tasks", label: "Tasks" },
  { id: "runs", label: "Runs" },
  { id: "agents", label: "Agents" },
  { id: "plugins", label: "Plugins" },
  { id: "github", label: "GitHub" },
  { id: "workspaces", label: "Workspaces" },
  { id: "observability", label: "Observability" },
  { id: "analytics", label: "Analytics" },
];

export function EngineeringOSPage(): unknown {
  const { useEffect, useState } = sdk().hooks;
  const [view, setView] = useState<ViewId>("overview");
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setData(null);
    setError(null);
    fetchView(view)
      .then((value) => {
        if (active) setData(value);
      })
      .catch((reason: unknown) => {
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
        h("p", { className: "eos-eyebrow" }, "Hermes Agent · operator evidence"),
        h("h1", null, "Engineering OS"),
        h(
          "p",
          { className: "eos-subtitle" },
          "Live runtime, canonical Kanban, workspace, Git, GitHub, observability, and derived outcomes. Read-only by design.",
        ),
      ),
      h("span", { className: "eos-readonly" }, "READ ONLY"),
    ),
    h(
      "nav",
      { className: "eos-nav", "aria-label": "Engineering OS views" },
      ...VIEWS.map((item) =>
        h(
          "button",
          {
            key: item.id,
            type: "button",
            className: view === item.id ? "eos-nav__item is-active" : "eos-nav__item",
            onClick: () => setView(item.id),
          },
          item.label,
        ),
      ),
    ),
    h(
      "main",
      { className: "eos-main", "data-view": view },
      error
        ? ErrorState({ message: error, retry: () => setRevision((old) => old + 1) })
        : data == null
          ? h("div", { className: "eos-loading", role: "status" }, "Loading live evidence…")
          : renderView(view, data),
    ),
  );
}

function renderView(view: ViewId, data: unknown): unknown {
  const object = data as Record<string, unknown>;
  switch (view) {
    case "overview": return OverviewView({ data: object });
    case "tasks": return h(TasksView, { data: data as never });
    case "runs": return h(RunsView, { data: data as never });
    case "agents": return AgentsView({ data: object });
    case "plugins": return PluginsView({ data: object });
    case "github": return GitHubView({ data: object });
    case "workspaces": return WorkspacesView({ data: object });
    case "observability": return ObservabilityView({ data: object });
    case "analytics": return h(AnalyticsView, { data: object });
  }
}

export function FooterStatus(): unknown {
  return h("span", { className: "eos-footer-status" }, "Engineering OS · read-only");
}

