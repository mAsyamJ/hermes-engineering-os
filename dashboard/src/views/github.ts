import { h } from "../sdk";
import { Card, DataTable, KeyValues } from "../components/data";
import { arrayValue, evidenceData, objectValue } from "./helpers";

export function GitHubView({ data }: { data: Record<string, unknown> }): unknown {
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
      h("span", { className: "eos-lock" }, "Mutation disabled"),
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
          { key: "dirty", label: "Dirty" },
        ],
        empty: "No allowlisted repositories are available.",
      }),
    }),
    Card({
      title: "GitHub API",
      status: String(apiEvidence.status ?? "UNKNOWN"),
      children: KeyValues({
        value: {
          ...objectValue(apiEvidence.data),
          detail: apiEvidence.detail,
        },
      }),
    }),
  );
}

