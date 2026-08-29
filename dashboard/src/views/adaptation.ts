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
            par_contract: data.par_contract || "par-v1",
            production_evidence: data.production_evidence || data.production_recommendation,
            human_approval_boundary: data.human_approval_boundary || data.production_approval,
            memory_isolation: data.memory_isolation,
            runtime_actuation: data.runtime_actuation || data.runtime_integration,
            production_adaptation: data.production_adaptation || "DISABLED",
            auto_promote: "forbidden",
            kill_switch: data.kill_switch,
            collapsed: "no",
          },
        }),
      }),
      Card({
        title: "PAR readiness cells",
        status: "INDEPENDENT",
        children: KeyValues({
          value: {
            secure_human_authority: objectValue(data.cells).secure_human_authority || "READY_FOR_OPERATOR_BOOTSTRAP",
            runtime_actuation: objectValue(data.cells).runtime_actuation || data.runtime_actuation,
            upstream_actuation: objectValue(data.cells).upstream_actuation || "READY_FOR_UPSTREAM_SUBMISSION",
            memory_isolation: objectValue(data.cells).memory_isolation || data.memory_isolation,
            real_experiment_preflight: objectValue(data.cells).real_experiment_preflight || "READY",
            budget_authorization: objectValue(data.cells).budget_authorization || "READY_FOR_BUDGET_AUTHORIZATION",
            real_experiment: objectValue(data.cells).real_experiment || "READY_FOR_BUDGET_AUTHORIZATION",
            treatment_fidelity: objectValue(data.cells).treatment_fidelity || "BLOCKED_BUDGET",
            real_causal_evidence: objectValue(data.cells).real_causal_evidence || "BLOCKED_BUDGET",
            production_recommendation: objectValue(data.cells).production_recommendation || "BLOCKED_EVIDENCE",
            pag2_readiness: objectValue(data.cells).pag2_readiness || "BLOCKED_EVIDENCE_AND_AUTHORITY",
            production_shadow: objectValue(data.cells).production_shadow || "BLOCKED_EVIDENCE",
            approval_a: objectValue(data.cells).approval_a || "BLOCKED_SECURITY_BOUNDARY",
            canary_package: objectValue(data.cells).canary_package || "BLOCKED_EVIDENCE",
            approval_b: objectValue(data.cells).approval_b || "NOT_EXECUTED",
            production_adaptation: objectValue(data.cells).production_adaptation || "DISABLED",
          },
        }),
      }),
      Card({
        title: "Production adaptation",
        status: "DISABLED",
        children: KeyValues({
          value: {
            evidence: "BLOCKED_EVIDENCE",
            approval: "BLOCKED_SECURITY_BOUNDARY",
            memory: data.memory_isolation || "READY",
            runtime: data.runtime_actuation || "READY_PATCH_NOT_DEPLOYED",
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
