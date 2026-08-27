import { h } from "../sdk";
import { Card, KeyValues } from "../components/data";
import { evidenceData, objectValue } from "./helpers";

export function OverviewView({ data }: { data: Record<string, unknown> }): unknown {
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
      children: KeyValues({ value: runtime }),
    }),
    Card({
      title: "Canonical Kanban",
      status: String(kanbanEvidence.status ?? "UNKNOWN"),
      children: KeyValues({ value: kanban }),
    }),
    Card({
      title: "Storage",
      children: KeyValues({ value: storage }),
    }),
    Card({
      title: "GitHub API",
      status: String(githubApi.status ?? "UNKNOWN"),
      children: KeyValues({ value: objectValue(githubApi.data) }),
    }),
  );
}

