import { fetchAdaptationExplain } from "../api";
import { Card, DataTable, KeyValues } from "../components/data";
import { h, sdk } from "../sdk";
import { arrayValue, objectValue } from "./helpers";

export function AdaptationView({ data }: { data: Record<string, unknown> }): unknown {
  const { useEffect, useState } = sdk().hooks;
  const recommendations = arrayValue(data.recommendations);
  const policies = arrayValue(data.policies);
  const rollbacks = arrayValue(data.rollbacks);
  const canaries = objectValue(data.canaries);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

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
    fetchAdaptationExplain(objectId)
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
            kill_switch: data.kill_switch,
          },
        }),
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
            fixture_qualification: "separate from production",
          },
        }),
      }),
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
          { key: "production_promotable", label: "prod?" },
        ],
        empty: "No recommendations.",
        onSelect: setSelected,
      }),
    }),
    Card({
      title: "Policies",
      children: DataTable({
        rows: policies,
        columns: [
          { key: "policy_id", label: "policy" },
          { key: "policy_version", label: "version" },
          { key: "scope", label: "scope" },
          { key: "policy_hash", label: "hash" },
        ],
        empty: "No compiled policies.",
        onSelect: setSelected,
      }),
    }),
    Card({
      title: "Canary / rollback",
      children: KeyValues({
        value: {
          plans: Array.isArray(canaries.plans) ? (canaries.plans as unknown[]).length : 0,
          auto_promote: "no",
          rollbacks: rollbacks.length,
        },
      }),
    }),
    selected
      ? Card({
          title: "WHY",
          children: KeyValues({
            value: {
              kind: detail?.kind,
              reason: why.reason || selected.reason,
              classification: why.classification || selected.classification,
              conclusion: why.conclusion,
              production_promotable: why.production_promotable,
              deploy_now: "no",
            },
          }),
        })
      : null,
    h("p", { className: "eos-note" }, "Read-only. PRODUCTION ADAPTATION DISABLED. No deploy, approve, or auto-optimize controls."),
  );
}
