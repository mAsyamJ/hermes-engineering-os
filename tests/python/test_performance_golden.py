"""Golden performance engine corpus. Expected outputs are authored, not inferred."""

from __future__ import annotations

import unittest

from engineering_os.performance.attribution import classify_model_attribution, classify_skill_attribution
from engineering_os.performance.cohorts import is_fixture_task, load_cohorts, matches_cohort
from engineering_os.performance.compare import pairwise
from engineering_os.performance.engine import enrich_population, load_configs, run_engine
from engineering_os.performance.failures import labels_for, taxonomy
from engineering_os.performance.metrics import compute_metric, group_by
from engineering_os.performance.tiers import load_tiers
from engineering_os.performance.trends import trend


def task(
    task_id: str,
    *,
    board: str = "retropick-markets-release",
    production: bool = True,
    lifecycle: str = "DONE",
    verification: str = "UNKNOWN",
    outcome: str = "COMPLETED_UNVERIFIED",
    first_pass: str = "PASS",
    retry: int | None = 0,
    rework: str = "NOT_DETECTED",
    human: str = "UNKNOWN",
    profile: str = "rp-web",
    repository_id: str | None = None,
    workspace: str = "/opt/retropick/.worktrees/x",
    **extra,
) -> dict:
    row = {
        "board": board,
        "task_id": task_id,
        "production_cohort": production,
        "lifecycle_state": lifecycle,
        "verification_state": verification,
        "final_outcome": outcome,
        "first_pass_state": first_pass,
        "retry_count": retry,
        "rework_status": rework,
        "human_intervention_state": human,
        "profile": profile,
        "profile_name": profile,
        "repository_id": repository_id,
        "workspace_path": workspace,
        "ruleset_version": extra.pop("ruleset_version", "phase3-v1"),
        "cost_status": extra.pop("cost_status", "UNKNOWN"),
        "created_at_source": extra.pop("created_at_source", 1_000),
        "completed_at_source": extra.pop("completed_at_source", 2_000),
    }
    row.update(extra)
    return row


class AttributionTests(unittest.TestCase):
    def test_single_and_mixed_model(self) -> None:
        single = classify_model_attribution(
            [{"provider": "openai-codex", "model": "gpt-5.6-sol", "source": "trace"}]
        )
        self.assertEqual(single["attribution"], "SINGLE_MODEL")
        mixed = classify_model_attribution(
            [
                {"provider": "openai-codex", "model": "gpt-5.6-sol", "source": "trace"},
                {"provider": "cli", "model": "gpt-5.6-sol", "source": "trace"},
            ]
        )
        self.assertEqual(mixed["attribution"], "MIXED_MODEL")
        self.assertEqual(classify_model_attribution([])["attribution"], "UNKNOWN")

    def test_multi_skill_preserved(self) -> None:
        multi = classify_skill_attribution(
            [{"skill_name": "a", "source": "trace"}, {"skill_name": "b", "source": "trace"}]
        )
        self.assertEqual(multi["attribution"], "MULTI_SKILL")
        self.assertEqual([item["skill_name"] for item in multi["skills"]], ["a", "b"])

    def test_mixed_model_not_in_single_slice(self) -> None:
        tasks = enrich_population(
            [task("t1"), task("t2")],
            model_rows=[
                {"board": "retropick-markets-release", "run_id": 1, "model": "a", "provider": "p", "source": "trace"},
                {"board": "retropick-markets-release", "run_id": 2, "model": "a", "provider": "p", "source": "trace"},
                {"board": "retropick-markets-release", "run_id": 2, "model": "b", "provider": "q", "source": "trace"},
            ],
            skill_rows=[],
            run_rows=[
                {"board": "retropick-markets-release", "run_id": 1, "task_id": "t1", "qualifying": True},
                {"board": "retropick-markets-release", "run_id": 2, "task_id": "t2", "qualifying": True},
            ],
        )
        grouped = group_by(tasks, "model")
        self.assertIn("p/a", grouped)
        self.assertEqual([row["task_id"] for row in grouped["p/a"]], ["t1"])
        self.assertTrue(all(row["model_attribution"] == "SINGLE_MODEL" for row in grouped["p/a"]))


class DenominatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tiers = load_tiers()

    def test_unknown_excluded_from_first_pass_denom(self) -> None:
        members = [
            task("a", first_pass="PASS"),
            task("b", first_pass="FAIL"),
            task("c", first_pass="UNKNOWN"),
            task("d", first_pass="NOT_APPLICABLE"),
        ]
        agg = compute_metric("first_pass_rate", members, self.tiers)
        self.assertEqual(agg["population_n"], 4)
        self.assertEqual(agg["known_n"], 2)
        self.assertEqual(agg["unknown_n"], 1)
        self.assertEqual(agg["na_n"], 1)
        self.assertEqual(agg["value"], 0.5)

    def test_zero_quality_coverage_is_insufficient_not_zero(self) -> None:
        members = [task("a"), task("b")]
        agg = compute_metric("quality_tests_pass_rate", members, self.tiers)
        self.assertEqual(agg["known_n"], 0)
        self.assertIsNone(agg["value"])
        self.assertEqual(agg["interpretation"], "INSUFFICIENT_DATA")
        self.assertEqual(agg["evidence_tier"], "NO_DATA")

    def test_partial_and_full_quality(self) -> None:
        members = [
            task(
                "eval1",
                evaluation={
                    "cohort": "production",
                    "eligibility": "ELIGIBLE",
                    "execution_status": "COMPLETE",
                    "quality_vector": {"tests": "PASS", "build": "PASS"},
                },
            ),
            task(
                "eval2",
                evaluation={
                    "cohort": "production",
                    "eligibility": "ELIGIBLE",
                    "execution_status": "COMPLETE",
                    "quality_vector": {"tests": "FAIL", "build": "UNKNOWN"},
                },
            ),
            task(
                "hist",
                evaluation={
                    "cohort": "production",
                    "eligibility": "INSUFFICIENT_EVIDENCE",
                    "execution_status": "COMPLETE",
                    "quality_vector": {"tests": "UNKNOWN"},
                },
            ),
        ]
        tests = compute_metric("quality_tests_pass_rate", members, self.tiers)
        self.assertEqual(tests["evaluated_n"], 2)
        self.assertEqual(tests["known_n"], 2)
        self.assertEqual(tests["value"], 0.5)
        self.assertNotIn("hist", tests["known_ids"][0] if False else "x")
        self.assertTrue(all("hist" not in ident for ident in tests["known_ids"]))

    def test_na_exclusion_verified_success(self) -> None:
        members = [
            task("a", verification="NOT_APPLICABLE", outcome="COMPLETED_UNVERIFIED"),
            task("b", verification="PASS", outcome="VERIFIED_SUCCESS"),
        ]
        agg = compute_metric("verified_success_rate", members, self.tiers)
        self.assertEqual(agg["known_n"], 1)
        self.assertEqual(agg["na_n"], 1)
        self.assertEqual(agg["value"], 1.0)


class FixtureAndCohortTests(unittest.TestCase):
    def test_fixture_excluded_from_production(self) -> None:
        config = load_cohorts()
        cohort = next(item for item in config["cohorts"] if item["cohort_id"] == "production_all")
        fixture = task("t_eval_canary_a", production=False, board="eos-phase2-obs")
        self.assertTrue(is_fixture_task(fixture, config))
        ok, reason = matches_cohort(fixture, cohort, config)
        self.assertFalse(ok)
        self.assertEqual(reason, "fixture_excluded")

    def test_engine_drops_canaries(self) -> None:
        tasks = [
            task("prod1"),
            task("t_eval_canary_b", production=False, board="eos-phase2-obs"),
        ]
        result = run_engine(enrich_population(tasks), metric_ids=["lifecycle_completion_rate"], cohort_ids=["production_all"])
        members = result["membership"]["production_all"]
        self.assertEqual(members, ["retropick-markets-release:prod1"])


class ComparabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tiers = load_tiers()

    def _agg(self, members, metric="lifecycle_completion_rate"):
        return compute_metric(metric, members, self.tiers)

    def test_ruleset_mismatch_not_comparable(self) -> None:
        left = [task("a", ruleset_version="phase3-v1") for _ in range(12)]
        right = [task("b", ruleset_version="phase3-v0", lifecycle="NOT_DONE") for _ in range(12)]
        compared = pairwise(
            "A",
            "B",
            left,
            right,
            "lifecycle_completion_rate",
            left_aggregate=self._agg(left),
            right_aggregate=self._agg(right),
            tier_config=self.tiers,
            comparison_config=self.tiers,
            left_ruleset="phase3-v1",
            right_ruleset="phase3-v0",
        )
        self.assertEqual(compared["interpretation"], "NOT_COMPARABLE")
        self.assertIsNone(compared["absolute_difference"])
        self.assertIsNone(compared["winner"])

    def test_evaluation_contract_mismatch(self) -> None:
        left = [task("a") for _ in range(12)]
        right = [task("b") for _ in range(12)]
        compared = pairwise(
            "A",
            "B",
            left,
            right,
            "quality_tests_pass_rate",
            left_aggregate=self._agg(left, "quality_tests_pass_rate"),
            right_aggregate=self._agg(right, "quality_tests_pass_rate"),
            tier_config=self.tiers,
            comparison_config=self.tiers,
            left_ruleset="phase3-v1",
            right_ruleset="phase3-v1",
            left_eval_contract="phase4-eval-v1",
            right_eval_contract="phase4-eval-v0",
            stratifiers=[],
        )
        self.assertEqual(compared["comparability"], "NOT_COMPARABLE")

    def test_confounded_repository(self) -> None:
        left = [task(f"l{i}", repository_id="retropick", profile="rp-web") for i in range(12)]
        right = [task(f"r{i}", repository_id="retropick-android", profile="rp-android", lifecycle="NOT_DONE") for i in range(12)]
        compared = pairwise(
            "rp-web",
            "rp-android",
            left,
            right,
            "lifecycle_completion_rate",
            left_aggregate=self._agg(left),
            right_aggregate=self._agg(right),
            tier_config=self.tiers,
            comparison_config=self.tiers,
            left_ruleset="phase3-v1",
            right_ruleset="phase3-v1",
            stratifiers=["repository_id"],
        )
        self.assertEqual(compared["interpretation"], "CONFOUNDED")

    def test_simpson_reversal(self) -> None:
        # Global B > A, but A > B inside each repository.
        left = (
            [task(f"a1{i}", repository_id="repoX", profile="A", lifecycle="DONE") for i in range(8)]
            + [task(f"a1f{i}", repository_id="repoX", profile="A", lifecycle="NOT_DONE") for i in range(2)]
            + [task(f"a2{i}", repository_id="repoY", profile="A", lifecycle="DONE") for i in range(2)]
            + [task(f"a2f{i}", repository_id="repoY", profile="A", lifecycle="NOT_DONE") for i in range(8)]
        )
        right = (
            [task(f"b1{i}", repository_id="repoX", profile="B", lifecycle="DONE") for i in range(70)]
            + [task(f"b1f{i}", repository_id="repoX", profile="B", lifecycle="NOT_DONE") for i in range(30)]
            + [task(f"b2{i}", repository_id="repoY", profile="B", lifecycle="DONE") for i in range(1)]
            + [task(f"b2f{i}", repository_id="repoY", profile="B", lifecycle="NOT_DONE") for i in range(9)]
        )
        compared = pairwise(
            "A",
            "B",
            left,
            right,
            "lifecycle_completion_rate",
            left_aggregate=self._agg(left),
            right_aggregate=self._agg(right),
            tier_config=self.tiers,
            comparison_config=self.tiers,
            left_ruleset="phase3-v1",
            right_ruleset="phase3-v1",
            stratifiers=["repository_id"],
        )
        self.assertTrue(compared["unsafe_global"] or compared["interpretation"] == "CONFOUNDED")
        self.assertTrue(any(item.get("simpson_reversal") for item in compared["strata"]))
        self.assertGreaterEqual(compared["strata"][0]["populated_strata"], 2)


class FailureAndTrendTests(unittest.TestCase):
    def test_multi_label_taxonomy(self) -> None:
        row = task(
            "x",
            lifecycle="NOT_DONE",
            evaluation={
                "eligibility": "INSUFFICIENT_EVIDENCE",
                "quality_vector": {"tests": "FAIL", "build": "FAIL"},
            },
        )
        labels = labels_for(row)
        self.assertIn("LIFECYCLE_INCOMPLETE", labels)
        self.assertIn("INSUFFICIENT_EVIDENCE", labels)
        self.assertIn("TEST_FAILURE", labels)
        self.assertIn("BUILD_FAILURE", labels)

    def test_no_llm_labels(self) -> None:
        row = task("x", title="frontend security architecture rewrite")
        self.assertEqual(labels_for(row), [])

    def test_failure_known_n_is_population_not_count(self) -> None:
        members = [task(f"done-{i}", lifecycle="DONE") for i in range(77)] + [
            task(f"open-{i}", lifecycle="NOT_DONE") for i in range(23)
        ]
        rows = taxonomy(members, load_tiers())
        incomplete = next(row for row in rows if row["label"] == "LIFECYCLE_INCOMPLETE")
        self.assertEqual(incomplete["count"], 23)
        self.assertEqual(incomplete["known_n"], 100)
        self.assertEqual(incomplete["population_n"], 100)
        self.assertEqual(incomplete["evidence_tier"], "SUPPORTED")
        self.assertNotEqual(incomplete["known_n"], incomplete["count"])

    def test_trend_insufficient(self) -> None:
        members = [task("only")]
        payload = trend(
            members,
            "lifecycle_completion_rate",
            cohort_id="production_all",
            tier_config=load_tiers(),
            comparison_config=load_tiers(),
            ruleset="phase3-v1",
            eval_contract=None,
            mode="rolling",
            size=30,
        )
        self.assertEqual(payload["state"], "INSUFFICIENT_DATA")
        self.assertFalse(payload["auto_action"])


class DurationOutlierTests(unittest.TestCase):
    def test_outlier_wall_time(self) -> None:
        members = [
            task("a", task_wall_seconds=1),
            task("b", task_wall_seconds=2),
            task("c", task_wall_seconds=3),
            task("d", task_wall_seconds=4),
            task("e", task_wall_seconds=1000),
        ]
        agg = compute_metric("task_wall_seconds", members, load_tiers())
        self.assertEqual(agg["value"], 3)
        self.assertGreater(agg["mean_supplemental"], agg["value"])


class PromptAndProfileTests(unittest.TestCase):
    def test_prompt_unsupported(self) -> None:
        result = run_engine(
            enrich_population([task("a") for _ in range(3)]),
            metric_ids=["lifecycle_completion_rate"],
            cohort_ids=["production_all"],
        )
        self.assertEqual(result["prompt_version_performance"]["prompt_version_performance"], "UNSUPPORTED_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
