import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from integration import task_manager as tm


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        base = Path(self.tmp.name)

        self.patches = [
            patch.object(tm, "DATA", base),
            patch.object(tm, "DB", base / "tasks.sqlite3"),
            patch.object(tm, "LOGS", base / "logs"),
        ]

        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def records(self):
        with tm.connect() as db:
            return db.execute(
                "SELECT status, error, log_path FROM tasks"
            ).fetchall()

    def test_add_creates_queued_task(self):
        with contextlib.redirect_stdout(io.StringIO()):
            tm.add()

        self.assertEqual(self.records()[0][0], "queued")

    def test_successful_task(self):
        with contextlib.redirect_stdout(io.StringIO()):
            tm.add()

        with patch.object(
            tm.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0)
        ) as runner:
            with contextlib.redirect_stdout(io.StringIO()):
                tm.run_next()

        self.assertEqual(self.records()[0][0], "completed")
        self.assertTrue(Path(self.records()[0][2]).exists())
        runner.assert_called_once()

    def test_failed_subprocess(self):
        with contextlib.redirect_stdout(io.StringIO()):
            tm.add()

        with patch.object(
            tm.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1)
        ):
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(io.StringIO()):
                    tm.run_next()

        self.assertEqual(self.records()[0][0], "failed")

    def test_timeout(self):
        with contextlib.redirect_stdout(io.StringIO()):
            tm.add()

        with patch.object(
            tm.subprocess,
            "run",
            side_effect=tm.subprocess.TimeoutExpired(
                cmd="lab_pipeline", timeout=180
            )
        ):
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(io.StringIO()):
                    tm.run_next()

        status, error, _ = self.records()[0]
        self.assertEqual(status, "failed")
        self.assertIn("timed out", error)

    def test_empty_queue(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            tm.run_next()

        self.assertIn("No queued tasks", output.getvalue())

    def test_completed_task_not_repeated(self):
        with contextlib.redirect_stdout(io.StringIO()):
            tm.add()

        with patch.object(
            tm.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0)
        ) as runner:
            with contextlib.redirect_stdout(io.StringIO()):
                tm.run_next()
                tm.run_next()

        self.assertEqual(runner.call_count, 1)


if __name__ == "__main__":
    unittest.main()
