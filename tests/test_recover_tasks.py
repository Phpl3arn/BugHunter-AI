import contextlib
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from integration import recover_tasks as recovery
from integration import task_manager as tm


class RecoveryTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        root = Path(self.tmp.name)

        patches = [
            patch.object(tm, "DATA", root),
            patch.object(tm, "DB", root / "tasks.sqlite3"),
            patch.object(tm, "LOGS", root / "logs"),
        ]

        for p in patches:
            p.start()
            self.addCleanup(p.stop)

        self.task_id = "test-task-001"

    def create_task(self, status, minutes_ago=60):
        started = (
            datetime.now(timezone.utc)
            - timedelta(minutes=minutes_ago)
        ).isoformat()

        with tm.connect() as db:
            db.execute(
                """
                INSERT INTO tasks
                (id, task_type, status, created_at, started_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.task_id,
                    "local_idor_lab",
                    status,
                    started,
                    started,
                ),
            )

    def status(self):
        with tm.connect() as db:
            return db.execute(
                "SELECT status FROM tasks WHERE id = ?",
                (self.task_id,),
            ).fetchone()[0]

    def test_old_running_task_detected(self):
        self.create_task("running", 60)

        with contextlib.redirect_stdout(io.StringIO()):
            count = recovery.recover(30, False)

        self.assertEqual(count, 1)
        self.assertEqual(self.status(), "running")

    def test_old_task_marked_failed(self):
        self.create_task("running", 60)

        with contextlib.redirect_stdout(io.StringIO()):
            count = recovery.recover(30, True)

        self.assertEqual(count, 1)
        self.assertEqual(self.status(), "failed")

    def test_recent_task_not_modified(self):
        self.create_task("running", 5)

        with contextlib.redirect_stdout(io.StringIO()):
            count = recovery.recover(30, True)

        self.assertEqual(count, 0)
        self.assertEqual(self.status(), "running")

    def test_completed_task_not_modified(self):
        self.create_task("completed", 60)

        with contextlib.redirect_stdout(io.StringIO()):
            count = recovery.recover(30, True)

        self.assertEqual(count, 0)
        self.assertEqual(self.status(), "completed")


if __name__ == "__main__":
    unittest.main()
