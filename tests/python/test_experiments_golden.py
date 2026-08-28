"""Golden experiment engine corpus. Expected outputs are authored, not inferred."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ["EOS_EVAL_SANDBOX"] = "inline"

from engineering_os.experiments.analyze import analyze
from engineering_os.experiments.assignment import assign_blocked, assign_paired
from engineering_os.experiments.config_snapshot import snapshot, strip_secrets, variant_snapshot
from engineering_os.experiments.definitions import DefinitionError, load_id, validate_raw
from engineering_os.experiments.diff import validate_single_factor
from engineering_os.experiments.engine import qualify
from engineering_os.experiments.exposure import record as record_exposure
from engineering_os.experiments.isolation import memory_ok, workspace_ok
from engineering_os.experiments.plan import plan_binary
from engineering_os.experiments.preregister import freeze, reject_mutation
from engineering_os.experiments.stats import independent_binary, paired_binary
from engineering_os.experiments.validity import confirmatory_allowed, evaluate as eval_validity


ROOT = Path(__file__).resolve().parents[2]


class SnapshotTests(unittest.TestCase):
    def test_same_config_same_hash(self) -> None:
        left = snapshot({"model": "a", "profile": {"name": "x"}})
        right = snapshot({"profile": {"name": "x"}, "model": "a"})
        self.assertEqual(left["config_hash"], right["config_hash"])

    def test_meaningful_change_different_hash(self) -> None:
        left = snapshot({"model": "a"})
        right = snapshot({"model": "b"})
        self.assertNotEqual(left["config_hash"], right["config_hash"])

    def test_secret_not_persisted(self) -> None:
        value = strip_secrets({"api_key": "FAKE_PHASE6_SECRET_ABC123", "model": "a"})
        encoded = str(value)
        self.assertNotIn("FAKE_PHASE6_SECRET_ABC123", encoded)
        self.assertEqual(value["api_key"], "[REDACTED]")


class DiffTests(unittest.TestCase):
    def test_aa_identical(self) -> None:
        snap = variant_snapshot(variant_id="a", variant_name="a", treatment_dimension="NONE", artifact={"name": "clean"})
        other = variant_snapshot(variant_id="b", variant_name="b", treatment_dimension="NONE", artifact={"name": "clean"})
        result = validate_single_factor("NONE", snap["snapshot"], other["snapshot"])
        self.assertTrue(result["ok"], result)

    def test_undeclared_dimension_blocked(self) -> None:
        control = variant_snapshot(variant_id="a", variant_name="a", treatment_dimension="MODEL", model={"id": "a"}, artifact={"name": "clean"})
        candidate = variant_snapshot(
            variant_id="b",
            variant_name="b",
            treatment_dimension="MODEL",
            model={"id": "b"},
            artifact={"name": "broken"},
        )
        result = validate_single_factor("MODEL", control["snapshot"], candidate["snapshot"])
        self.assertFalse(result["ok"])
        self.assertIn("artifact", result["diffs"])


class AssignmentTests(unittest.TestCase):
    def test_reproducible_and_order_independent(self) -> None:
        units = [{"unit_id": f"u{i}", "stratum": "s"} for i in range(8)]
        a = assign_blocked(units, "seed-1", "c", "t")
        b = assign_blocked(list(reversed(units)), "seed-1", "c", "t")
        self.assertEqual([row["unit_id"] for row in a], [row["unit_id"] for row in b])
        self.assertEqual([row["variant_role"] for row in a], [row["variant_role"] for row in b])
        c = assign_blocked(units, "seed-2", "c", "t")
        self.assertNotEqual([row["assignment_hash"] for row in a], [row["assignment_hash"] for row in c])

    def test_paired_order_randomized_but_both_arms(self) -> None:
        cases = [{"pair_id": f"p{i}", "case_id": f"c{i}", "stratum": "s"} for i in range(4)]
        rows = assign_paired(cases, "seed-p", "control", "cand")
        self.assertEqual(len(rows), 8)
        by_pair: dict[str, set[str]] = {}
        for row in rows:
            by_pair.setdefault(row["pair_id"], set()).add(row["variant_role"])
        self.assertTrue(all(roles == {"CONTROL", "CANDIDATE"} for roles in by_pair.values()))
        again = assign_paired(cases, "seed-p", "control", "cand")
        self.assertEqual(rows, again)


class PlanTests(unittest.TestCase):
    def test_binary_plan_explicit_alpha_power(self) -> None:
        result = plan_binary(baseline_rate=0.5, mde=0.2, alpha=0.05, power=0.80, max_units=10000)
        self.assertEqual(result["status"], "FEASIBLE")
        self.assertGreater(result["planned_n"], 0)
        self.assertEqual(result["assumptions"]["alpha"], 0.05)
        self.assertEqual(result["assumptions"]["power"], 0.80)
        self.assertFalse(result["shrunk"])

    def test_infeasible_not_shrunk(self) -> None:
        result = plan_binary(baseline_rate=0.5, mde=0.05, alpha=0.05, power=0.80, max_units=10)
        self.assertEqual(result["status"], "INFEASIBLE_BUDGET")
        self.assertGreater(result["planned_n"], 10)
        self.assertFalse(result["shrunk"])

    def test_no_invented_variance(self) -> None:
        result = plan_binary(
            baseline_rate=0.5, mde=0.2, alpha=0.05, power=0.80, outcome_type="continuous"
        )
        self.assertEqual(result["status"], "VARIANCE_REQUIRED")
        self.assertIsNone(result["planned_n"])

    def test_llm_budget_zero(self) -> None:
        result = plan_binary(
            baseline_rate=0.5, mde=0.2, alpha=0.05, power=0.80, max_llm_calls=0, requires_llm=True
        )
        self.assertEqual(result["status"], "INFEASIBLE_BUDGET")


class StatsTests(unittest.TestCase):
    def test_independent_n0(self) -> None:
        result = independent_binary([], [])
        self.assertIsNone(result["absolute_difference"])

    def test_paired_known_effect(self) -> None:
        control = [0] * 8
        candidate = [1] * 8
        result = paired_binary(control, candidate)
        self.assertEqual(result["b_candidate_only"], 8)
        self.assertGreater(result["interval_low"] or -1, 0)


class LoaderTests(unittest.TestCase):
    def test_trusted_definitions_load(self) -> None:
        for name in ("fixture-aa-v1", "fixture-known-effect-v1", "fixture-paired-v1"):
            loaded = load_id(name)
            self.assertEqual(loaded["budget"]["max_llm_calls"], 0)
            freeze(loaded)

    def test_rejects_shell_and_production(self) -> None:
        base = load_id("fixture-aa-v1")
        raw = {k: v for k, v in base.items() if not str(k).startswith("_")}
        with self.assertRaises(DefinitionError):
            validate_raw({**raw, "command": "rm -rf /"})
        with self.assertRaises(DefinitionError):
            validate_raw({**raw, "scope": "PRODUCTION"})
        with self.assertRaises(DefinitionError):
            validate_raw({**raw, "unknown_field": 1})


class FreezeTests(unittest.TestCase):
    def test_mutation_rejected(self) -> None:
        protocol = freeze(load_id("fixture-aa-v1"))
        digest = protocol["pre_registration_hash"]
        reject_mutation(digest, protocol)
        mutated = dict(protocol)
        mutated["primary_metric"] = {"id": "other"}
        with self.assertRaises(PermissionError):
            reject_mutation(digest, mutated)


class IsolationTests(unittest.TestCase):
    def test_shared_memory_fails(self) -> None:
        self.assertFalse(memory_ok("same", "same", fixture=False)["ok"])
        self.assertTrue(memory_ok(None, None, fixture=True)["ok"])

    def test_workspace_same_path_fails(self) -> None:
        path = ROOT / "tests" / "evaluation" / "fixture_src"
        self.assertFalse(workspace_ok(path, path)["ok"])


class AnalysisGuardTests(unittest.TestCase):
    def test_peeking_blocked(self) -> None:
        protocol = freeze(load_id("fixture-aa-v1"))
        assignments = assign_paired(
            [{"pair_id": f"p{i}", "case_id": f"c{i}", "stratum": "s"} for i in range(8)],
            protocol["assignment"]["seed"],
            protocol["control"]["variant_id"],
            protocol["candidate"]["variant_id"],
        )
        observations = [
            {"unit_id": assignments[0]["unit_id"], "metric_id": protocol["primary_metric"]["id"], "value": "PASS"}
        ]
        result = analyze(protocol, assignments, observations, final=True)
        self.assertEqual(result["blocked"], "BLOCKED_HORIZON")
        self.assertEqual(result["conclusion"], "COLLECTING")

    def test_itt_preserves_fallback(self) -> None:
        protocol = freeze(load_id("fixture-known-effect-v1"))
        assignments = [
            {
                "unit_id": "u-cand",
                "variant_role": "CANDIDATE",
                "variant_id": protocol["candidate"]["variant_id"],
                "pair_id": "p1",
            },
            {
                "unit_id": "u-ctrl",
                "variant_role": "CONTROL",
                "variant_id": protocol["control"]["variant_id"],
                "pair_id": "p1",
            },
        ]
        # Expand to horizon 4 pairs with missing others? planned_n=8. Build 8 pairs.
        rows = []
        obs = []
        expos = []
        for i in range(8):
            rows.append(
                {
                    "unit_id": f"p{i}:candidate",
                    "variant_role": "CANDIDATE",
                    "variant_id": protocol["candidate"]["variant_id"],
                    "pair_id": f"p{i}",
                }
            )
            rows.append(
                {
                    "unit_id": f"p{i}:control",
                    "variant_role": "CONTROL",
                    "variant_id": protocol["control"]["variant_id"],
                    "pair_id": f"p{i}",
                }
            )
            # candidate assigned, observed control artifact (FAIL)
            obs.append({"unit_id": f"p{i}:candidate", "metric_id": protocol["primary_metric"]["id"], "value": "FAIL"})
            obs.append({"unit_id": f"p{i}:control", "metric_id": protocol["primary_metric"]["id"], "value": "FAIL"})
            expos.append(
                record_exposure(
                    {**rows[-2], "assigned_config_hash": "cand"},
                    "control-hash",
                    True,
                )
            )
            expos.append(
                record_exposure(
                    {**rows[-1], "assigned_config_hash": "ctrl"},
                    "control-hash",
                    True,
                )
            )
        self.assertEqual(expos[0]["fidelity"], "NONCOMPLIANT")
        self.assertEqual(expos[0]["itt_variant_role"], "CANDIDATE")
        self.assertFalse(expos[0]["reassigned"])
        result = analyze(protocol, rows, obs, expos, final=True)
        self.assertEqual(result["itt_n_candidate"], 8)
        self.assertNotEqual(result["conclusion"], "EVIDENCE_FOR_CANDIDATE")

    def test_missingness_explicit(self) -> None:
        protocol = freeze(load_id("fixture-aa-v1"))
        assignments = assign_paired(
            [{"pair_id": f"p{i}", "case_id": f"c{i}", "stratum": "s"} for i in range(8)],
            protocol["assignment"]["seed"],
            protocol["control"]["variant_id"],
            protocol["candidate"]["variant_id"],
        )
        observations = [
            {"unit_id": row["unit_id"], "metric_id": protocol["primary_metric"]["id"], "value": None, "known": False}
            for row in assignments
        ]
        result = analyze(protocol, assignments, observations, final=True)
        self.assertEqual(result["assigned_n"], 16)
        self.assertEqual(result["missing_n"], 16)
        self.assertIn(result["conclusion"], {"INSUFFICIENT_DATA", "INVALIDATED"})

    def test_validity_not_a_score(self) -> None:
        validity = eval_validity(
            {
                "scope": "FIXTURE",
                "protocol_hash_ok": True,
                "assignment_ok": True,
                "config_ok": True,
                "environment_ok": True,
                "memory_mode": "fixture_executor",
                "workspace_ok": True,
                "coverage_ok": True,
                "evaluator_ok": True,
            }
        )
        self.assertIn("PROTOCOL_INTEGRITY", validity)
        self.assertTrue(confirmatory_allowed(validity, "FIXTURE"))
        validity["CONFIG_INTEGRITY"] = "FAIL"
        self.assertFalse(confirmatory_allowed(validity, "FIXTURE"))


class QualificationTests(unittest.TestCase):
    def test_aa_no_candidate_preference(self) -> None:
        result = qualify(load_id("fixture-aa-v1"), final=True)
        self.assertEqual(result["result"]["conclusion"], "NO_CLEAR_EFFECT")
        self.assertNotEqual(result["result"]["conclusion"], "EVIDENCE_FOR_CANDIDATE")
        self.assertTrue(result["result"]["fixture_validation_only"])
        self.assertFalse(result["result"]["auto_route"])
        self.assertEqual(result["balance"]["integrity"], "PASS")

    def test_known_effect_recovered(self) -> None:
        result = qualify(load_id("fixture-known-effect-v1"), final=True)
        self.assertEqual(result["result"]["conclusion"], "EVIDENCE_FOR_CANDIDATE")
        self.assertTrue(result["result"]["fixture_validation_only"])
        self.assertIn("FIXTURE_VALIDATION_ONLY", result["result"]["reason"])

    def test_paired_identity(self) -> None:
        result = qualify(load_id("fixture-paired-v1"), final=True)
        pair_ids = {row["pair_id"] for row in result["assignments"]}
        self.assertEqual(len(pair_ids), 4)
        self.assertTrue(all(item["workspace_ok"] for item in result["executions"]))
        self.assertEqual(result["result"]["conclusion"], "EVIDENCE_FOR_CANDIDATE")
        workspaces = [item["workspace"] for item in result["executions"]]
        self.assertEqual(len(workspaces), len(set(workspaces)))


if __name__ == "__main__":
    unittest.main()
