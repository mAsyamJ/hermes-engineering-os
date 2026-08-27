from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from engineering_os.correlation import CorrelationIds
from engineering_os.models import EvidenceStatus
from engineering_os.redaction import redact
from integrations.github.client import FixtureTransport, public_repository
from integrations.github.correlation import correlate_task
from integrations.github.local_git import repository_status
from integrations.hermes.kanban import connect_read_only


class AdapterTests(unittest.TestCase):
    def test_correlation_namespaces_do_not_alias(self) -> None:
        ids = CorrelationIds(
            hermes_kanban_task_id="t_kanban",
            hermes_runtime_task_id="runtime-task",
            hermes_kanban_run_id=7,
        ).to_dict()
        self.assertEqual(ids["hermes_kanban_task_id"], "t_kanban")
        self.assertEqual(ids["hermes_runtime_task_id"], "runtime-task")
        self.assertNotEqual(ids["hermes_kanban_task_id"], ids["hermes_runtime_task_id"])

    def test_redaction_is_recursive(self) -> None:
        fake = "ghp_abcdefghijklmnopqrstuvwxyz123456"
        value = redact({"nested": [{"authorization": fake}], "line": f"Bearer {fake}"})
        encoded = json.dumps(value)
        self.assertNotIn(fake, encoded)
        self.assertIn("[REDACTED]", encoded)

    def test_sqlite_connection_denies_writes_and_preserves_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "kanban.db"
            writer = sqlite3.connect(path)
            writer.executescript(
                "CREATE TABLE tasks(id TEXT PRIMARY KEY, status TEXT);"
                "INSERT INTO tasks VALUES('t_fixture','todo');"
            )
            writer.commit()
            writer.close()
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            connection = connect_read_only(path)
            self.assertEqual(
                connection.execute("SELECT status FROM tasks").fetchone()["status"], "todo"
            )
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute("UPDATE tasks SET status='done'")
            connection.close()
            after = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(before, after)

    def test_fixture_github_transport(self) -> None:
        transport = FixtureTransport({"org/repo": {"id": 1, "default_branch": "main"}})
        evidence = public_repository("org/repo", transport)
        self.assertEqual(evidence.status, EvidenceStatus.AVAILABLE)
        self.assertEqual(evidence.data["id"], 1)

    def test_missing_metadata_correlation_is_unknown(self) -> None:
        result = correlate_task({"id": "t_fixture"})
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)

    def test_repository_id_is_allowlisted(self) -> None:
        with self.assertRaises(KeyError):
            repository_status("../../arbitrary")


if __name__ == "__main__":
    unittest.main()

