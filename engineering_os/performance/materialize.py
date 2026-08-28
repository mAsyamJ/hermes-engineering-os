"""Persist Phase 5 performance materializations. Fail-open toward Hermes."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from engineering_os.analytics.db import advisory_unlock, connect, try_advisory_lock
from engineering_os.performance import (
    ADVISORY_LOCK_KEY,
    ANALYTICS_LOCK_KEY,
    CONTRACT_VERSION,
    EVALUATION_LOCK_KEY,
)
from engineering_os.performance.cohorts import canonical_hash
from engineering_os.performance.engine import enrich_population, load_configs, run_engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonb(value: Any) -> Any:
    from psycopg.types.json import Json

    return Json(value)


def advisory_held(connection: Any, key: int) -> bool:
    row = connection.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_locks
            WHERE locktype = 'advisory'
              AND classid = 0
              AND objid = %s
              AND granted
        ) AS held
        """,
        (key,),
    ).fetchone()
    return bool(row and row["held"])


def load_population(connection: Any) -> list[dict[str, Any]]:
    tasks = list(
        connection.execute(
            """
            SELECT o.*, t.profile, t.title, t.status, t.workspace_path, t.created_at_source,
                   t.started_at_source, t.completed_at_source, t.cohort AS fact_cohort,
                   g.repository_id
            FROM task_outcomes o
            JOIN task_facts t ON t.board = o.board AND t.task_id = o.task_id
            LEFT JOIN git_facts g ON g.board = o.board AND g.task_id = o.task_id
            """
        ).fetchall()
    )
    traces = list(connection.execute("SELECT * FROM trace_facts").fetchall())
    trace_by_task = {}
    for row in traces:
        if row.get("board") and row.get("task_id"):
            trace_by_task[(row["board"], row["task_id"])] = row
    evals = list(
        connection.execute(
            """
            SELECT r.board, r.task_id, r.cohort, r.eligibility, r.execution_status,
                   r.contract_version, r.is_current, s.quality_vector, s.summary_state
            FROM evaluation_runs r
            LEFT JOIN evaluation_summaries s ON s.evaluation_run_id = r.evaluation_run_id
            WHERE r.is_current
            """
        ).fetchall()
    )
    eval_by_task: dict[tuple[str, str], dict[str, Any]] = {}
    for row in evals:
        eval_by_task[(row["board"], row["task_id"])] = dict(row)
    runs = list(connection.execute("SELECT board, run_id, task_id, qualifying FROM run_facts").fetchall())
    models = list(connection.execute("SELECT * FROM run_model_usage").fetchall())
    skills = list(connection.execute("SELECT * FROM run_skill_usage").fetchall())
    prepared = []
    for row in tasks:
        item = dict(row)
        trace = trace_by_task.get((row["board"], row["task_id"]))
        if trace:
            item["token_total"] = trace.get("token_total")
            item["token_prompt"] = trace.get("token_prompt")
            item["token_completion"] = trace.get("token_completion")
            if item.get("trace_wall_seconds") is None:
                item["trace_wall_seconds"] = trace.get("trace_wall_seconds")
            if item.get("llm_call_count") is None:
                item["llm_call_count"] = trace.get("llm_call_count")
            if item.get("tool_call_count") is None:
                item["tool_call_count"] = trace.get("tool_call_count")
            if item.get("error_count") is None:
                item["error_count"] = trace.get("error_count")
        evaluation = eval_by_task.get((row["board"], row["task_id"]))
        if evaluation:
            vector = evaluation.get("quality_vector")
            if isinstance(vector, str):
                vector = json.loads(vector)
            evaluation = dict(evaluation)
            evaluation["quality_vector"] = vector or {}
            item["evaluation"] = evaluation
            item["evaluation_cohort"] = evaluation.get("cohort")
        prepared.append(item)
    return enrich_population(prepared, list(models), list(skills), list(runs))


def persist(connection: Any, result: dict[str, Any], run_id: str, mode: str) -> dict[str, Any]:
    connection.execute("UPDATE performance_aggregates SET is_current = FALSE WHERE is_current")
    connection.execute("UPDATE performance_comparisons SET is_current = FALSE WHERE is_current")
    connection.execute("UPDATE performance_insights SET is_current = FALSE WHERE is_current")
    written = 0
    agg_ids: dict[tuple[Any, ...], str] = {}
    for agg in result["aggregates"]:
        aggregate_id = str(uuid.uuid4())
        extras = {
            "successes": agg.get("successes"),
            "evaluated_n": agg.get("evaluated_n"),
            "mean_supplemental": agg.get("mean_supplemental"),
            "label": agg.get("label"),
            "quality_evaluated_n": agg.get("quality_evaluated_n"),
            "cost_effectiveness": agg.get("cost_effectiveness"),
            "prompt_version_performance": agg.get("prompt_version_performance"),
            "observational": agg.get("observational", True),
        }
        source_hash = canonical_hash(
            {
                "metric": agg["metric_id"],
                "cohort": agg["cohort_id"],
                "dimension": [agg["dimension_type"], agg["dimension_value"]],
                "known_ids": agg.get("known_ids") or [],
                "value": agg.get("value"),
            }
        )
        connection.execute(
            """
            INSERT INTO performance_aggregates (
                aggregate_id, materialization_id, contract_version, phase3_ruleset_version,
                phase4_contract_version, cohort_id, cohort_version, cohort_hash,
                dimension_type, dimension_value, metric_id, population_n, known_n, unknown_n,
                na_n, coverage, value, unit, uncertainty, evidence_tier, interpretation,
                source_hash, extras, is_current
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, TRUE
            )
            """,
            (
                aggregate_id,
                run_id,
                agg.get("contract_version") or CONTRACT_VERSION,
                agg.get("phase3_ruleset_version") or "phase3-v1",
                agg.get("phase4_contract_version"),
                agg["cohort_id"],
                agg.get("cohort_version") or "v1",
                agg.get("cohort_hash") or "",
                agg["dimension_type"],
                agg["dimension_value"],
                agg["metric_id"],
                int(agg.get("population_n") or 0),
                int(agg.get("known_n") or 0),
                int(agg.get("unknown_n") or 0),
                int(agg.get("na_n") or 0),
                agg.get("coverage"),
                agg.get("value"),
                agg.get("unit"),
                _jsonb(agg.get("uncertainty") or {}),
                agg.get("evidence_tier") or "NO_DATA",
                agg.get("interpretation"),
                source_hash,
                _jsonb(extras),
            ),
        )
        agg_ids[(agg["cohort_id"], agg["dimension_type"], agg["dimension_value"], agg["metric_id"])] = aggregate_id
        written += 1
    compared_n = 0
    for cmp in result["comparisons"]:
        comparison_id = str(uuid.uuid4())
        left_id = agg_ids.get((cmp.get("cohort_id"), "profile_name", cmp["left_identity"], cmp["metric_id"]))
        if left_id is None:
            left_id = agg_ids.get((cmp.get("cohort_id"), "model", cmp["left_identity"], cmp["metric_id"]))
        if left_id is None:
            left_id = agg_ids.get((cmp.get("cohort_id"), "skill", cmp["left_identity"], cmp["metric_id"]))
        right_id = agg_ids.get((cmp.get("cohort_id"), "profile_name", cmp["right_identity"], cmp["metric_id"]))
        if right_id is None:
            right_id = agg_ids.get((cmp.get("cohort_id"), "model", cmp["right_identity"], cmp["metric_id"]))
        if right_id is None:
            right_id = agg_ids.get((cmp.get("cohort_id"), "skill", cmp["right_identity"], cmp["metric_id"]))
        connection.execute(
            """
            INSERT INTO performance_comparisons (
                comparison_id, materialization_id, comparison_set, contract_version, metric_id,
                left_aggregate_id, right_aggregate_id, left_identity, right_identity,
                left_n, right_n, left_estimate, right_estimate, absolute_difference,
                relative_difference, uncertainty, coverage, left_tier, right_tier,
                comparability, confounding_status, interpretation, strata, is_current
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, TRUE
            )
            """,
            (
                comparison_id,
                run_id,
                cmp.get("comparison_set") or "",
                CONTRACT_VERSION,
                cmp["metric_id"],
                left_id,
                right_id,
                cmp["left_identity"],
                cmp["right_identity"],
                cmp.get("left_n"),
                cmp.get("right_n"),
                cmp.get("left_estimate"),
                cmp.get("right_estimate"),
                cmp.get("absolute_difference"),
                cmp.get("relative_difference"),
                _jsonb(cmp.get("uncertainty") or {}),
                _jsonb(cmp.get("coverage") or {}),
                cmp.get("left_tier"),
                cmp.get("right_tier"),
                cmp["comparability"],
                cmp["confounding_status"],
                cmp["interpretation"],
                _jsonb(cmp.get("strata") or []),
            ),
        )
        compared_n += 1
        insight_id = str(uuid.uuid4())
        body = next(
            (item["body"] for item in result["insights"] if item.get("kind") == "comparison" and item.get("metric_id") == cmp["metric_id"] and cmp["left_identity"] in item["body"] and cmp["right_identity"] in item["body"]),
            None,
        )
        if body:
            connection.execute(
                """
                INSERT INTO performance_insights (
                    insight_id, materialization_id, comparison_id, kind, body, causal, is_current
                ) VALUES (%s,%s,%s,'comparison',%s, FALSE, TRUE)
                """,
                (insight_id, run_id, comparison_id, body),
            )
    for insight in result["insights"]:
        if insight.get("kind") != "aggregate":
            continue
        connection.execute(
            """
            INSERT INTO performance_insights (
                insight_id, materialization_id, kind, body, causal, is_current
            ) VALUES (%s,%s,%s,%s, FALSE, TRUE)
            """,
            (str(uuid.uuid4()), run_id, insight["kind"], insight["body"]),
        )
    for fail in result.get("failures") or []:
        aggregate_id = str(uuid.uuid4())
        connection.execute(
            """
            INSERT INTO performance_aggregates (
                aggregate_id, materialization_id, contract_version, phase3_ruleset_version,
                phase4_contract_version, cohort_id, cohort_version, cohort_hash,
                dimension_type, dimension_value, metric_id, population_n, known_n, unknown_n,
                na_n, coverage, value, unit, uncertainty, evidence_tier, interpretation,
                source_hash, extras, is_current
            ) VALUES (
                %s,%s,%s,'phase3-v1', 'phase4-eval-v1', %s,'v1','',
                'failure', %s, %s, %s,%s,0,0,%s,%s,'proportion',%s,%s,NULL,%s,%s, TRUE
            )
            """,
            (
                aggregate_id,
                run_id,
                CONTRACT_VERSION,
                fail.get("cohort_id") or "production_all",
                fail["label"],
                f"failure_{fail['label']}",
                int(fail.get("population_n") or 0),
                int(fail.get("known_n") or fail.get("population_n") or 0),
                fail.get("coverage"),
                fail.get("value"),
                _jsonb(fail.get("uncertainty") or {}),
                fail.get("evidence_tier") or "NO_DATA",
                canonical_hash(fail),
                _jsonb(
                    {
                        "examples": fail.get("examples") or [],
                        "observational": True,
                        "count": fail.get("count") or 0,
                    }
                ),
            ),
        )
        written += 1
    for tr in result.get("trends") or []:
        comparison_id = str(uuid.uuid4())
        cmp = tr.get("comparison") or {}
        connection.execute(
            """
            INSERT INTO performance_comparisons (
                comparison_id, materialization_id, comparison_set, contract_version, metric_id,
                left_identity, right_identity, left_n, right_n, left_estimate, right_estimate,
                absolute_difference, relative_difference, uncertainty, coverage, left_tier,
                right_tier, comparability, confounding_status, interpretation, strata, is_current
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, TRUE
            )
            """,
            (
                comparison_id,
                run_id,
                f"trend:{tr.get('window')}",
                CONTRACT_VERSION,
                tr.get("metric_id"),
                f"prior:{tr.get('window')}",
                f"current:{tr.get('window')}",
                cmp.get("left_n"),
                cmp.get("right_n"),
                cmp.get("left_estimate"),
                cmp.get("right_estimate"),
                cmp.get("absolute_difference"),
                cmp.get("relative_difference"),
                _jsonb(cmp.get("uncertainty") or {}),
                _jsonb(cmp.get("coverage") or {}),
                cmp.get("left_tier"),
                cmp.get("right_tier"),
                cmp.get("comparability") or "INSUFFICIENT_DATA",
                tr.get("state") or "INSUFFICIENT_DATA",
                cmp.get("interpretation") or "INSUFFICIENT_DATA",
                _jsonb({"auto_action": False, "state": tr.get("state")}),
            ),
        )
        compared_n += 1
    return {"aggregates_written": written, "comparisons_written": compared_n}


def materialize(
    *,
    dry_run: bool = False,
    cohort: str | None = None,
    metric: str | None = None,
    backfill: bool = False,
    recompute: bool = False,
    since: str | None = None,
) -> dict[str, Any]:
    mode = "dry-run" if dry_run else ("recompute" if recompute else ("backfill" if backfill else "incremental"))
    run_id = str(uuid.uuid4())
    started = _now()
    with connect() as connection:
        if not try_advisory_lock(connection, ADVISORY_LOCK_KEY):
            return {"status": "locked", "contract_version": CONTRACT_VERSION, "detail": "performance lock held"}
        try:
            if advisory_held(connection, ANALYTICS_LOCK_KEY) or advisory_held(connection, EVALUATION_LOCK_KEY):
                return {
                    "status": "locked",
                    "contract_version": CONTRACT_VERSION,
                    "detail": "analytics or evaluation materialization in progress",
                }
            tasks = load_population(connection)
            configs = load_configs()
            result = run_engine(
                tasks,
                configs=configs,
                metric_ids=[metric] if metric else None,
                cohort_ids=[cohort] if cohort else None,
                include_ui_hidden=bool(cohort),
            )
            payload = {
                "status": "success",
                "mode": mode,
                "contract_version": CONTRACT_VERSION,
                "materialization_id": run_id,
                "coverage": result["coverage"],
                "aggregates": len(result["aggregates"]),
                "comparisons": len(result["comparisons"]),
                "insights": len(result["insights"]),
                "failures": len(result["failures"]),
                "prompt_version_performance": result["prompt_version_performance"],
            }
            if dry_run:
                payload["dry_run"] = True
                payload["sample"] = result["aggregates"][:12]
                return payload
            connection.execute(
                """
                INSERT INTO performance_materialization_runs (
                    materialization_id, started_at, contract_version, phase3_ruleset_version,
                    phase4_contract_version, mode, status
                ) VALUES (%s,%s,%s,%s,%s,%s,'running')
                """,
                (
                    run_id,
                    started,
                    CONTRACT_VERSION,
                    "phase3-v1",
                    "phase4-eval-v1",
                    mode,
                ),
            )
            counts = persist(connection, result, run_id, mode)
            source_hash = canonical_hash(result["coverage"])
            connection.execute(
                """
                UPDATE performance_materialization_runs
                SET ended_at = %s, status = 'success', cohorts_scanned = %s,
                    aggregates_written = %s, comparisons_written = %s, source_hash = %s
                WHERE materialization_id = %s
                """,
                (
                    _now(),
                    len(result["membership"]),
                    counts["aggregates_written"],
                    counts["comparisons_written"],
                    source_hash,
                    run_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO performance_checkpoints (source, watermark, source_hash, materialization_id)
                VALUES ('phase5', %s, %s, %s)
                ON CONFLICT (source) DO UPDATE SET
                    watermark = EXCLUDED.watermark,
                    source_hash = EXCLUDED.source_hash,
                    materialization_id = EXCLUDED.materialization_id,
                    updated_at = NOW()
                """,
                (_now().isoformat(), source_hash, run_id),
            )
            connection.commit()
            payload.update(counts)
            return payload
        except Exception as exc:
            connection.rollback()
            return {
                "status": "error",
                "contract_version": CONTRACT_VERSION,
                "detail": f"{type(exc).__name__}: {exc}",
            }
        finally:
            advisory_unlock(connection, ADVISORY_LOCK_KEY)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 performance materializer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cohort")
    parser.add_argument("--metric")
    parser.add_argument("--since")
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = materialize(
        dry_run=args.dry_run,
        cohort=args.cohort,
        metric=args.metric,
        backfill=args.backfill,
        recompute=args.recompute,
        since=args.since,
    )
    if args.json:
        print(json.dumps(result, default=str))
    else:
        print(result.get("status"), result.get("aggregates"), result.get("detail", ""))
    return 0 if result.get("status") in {"success", "locked"} or result.get("dry_run") else 1


if __name__ == "__main__":
    raise SystemExit(main())
