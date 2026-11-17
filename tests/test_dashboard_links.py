import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import server


class DashboardLinkTests(unittest.TestCase):

    def test_valid_task_id(self):
        self.assertIsNotNone(
            server.TASK_ID.fullmatch("c550db637f61")
        )

    def test_invalid_task_ids(self):
        for value in (
            "../secret",
            "invalid/id",
            "hello world",
            "a" * 65,
        ):
            with self.subTest(value=value):
                self.assertIsNone(
                    server.TASK_ID.fullmatch(value)
                )

    def test_completed_task_has_report_link(self):
        task_id = "c550db637f61"

        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            folder = runs / task_id
            folder.mkdir()
            (folder / "report.md").write_text(
                "# Synthetic test report",
                encoding="utf-8",
            )

            tasks = [
                (
                    task_id,
                    "local_idor_lab",
                    "completed",
                    "2026-11-17T00:00:00+00:00",
                )
            ]

            with (
                patch.object(server, "RUNS", runs),
                patch.object(
                    server,
                    "get_tasks",
                    return_value=tasks,
                ),
                patch(
                    "integration.healthcheck.check_all",
                    return_value={
                        "vulnerable_lab": True,
                        "safe_lab": True,
                        "ollama": True,
                    },
                ),
            ):
                html = server.page()

            self.assertIn(
                f'/report/{task_id}',
                html,
            )
            self.assertIn("Raporu Aç", html)


if __name__ == "__main__":
    unittest.main()
