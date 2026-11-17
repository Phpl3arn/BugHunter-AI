import unittest
from unittest.mock import patch

from dashboard import server


class DashboardIntegrityTests(unittest.TestCase):

    def render(self, integrity):
        tasks = [
            (
                "abc123def456",
                "local_idor_lab",
                "completed",
                "2026-11-17T02:45:00+00:00",
            )
        ]

        with (
            patch.object(server, "get_tasks", return_value=tasks),
            patch(
                "dashboard.task_detail.integrity_status",
                return_value=(integrity, "#4ade80"),
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
            return server.page()

    def test_integrity_pass(self):
        html = self.render("PASS")
        self.assertIn("<th>Bütünlük</th>", html)
        self.assertIn(">PASS</strong>", html)

    def test_integrity_fail(self):
        html = self.render("FAIL")
        self.assertIn(">FAIL</strong>", html)

    def test_unsealed_task(self):
        html = self.render("MÜHÜRLENMEMİŞ")
        self.assertIn("MÜHÜRLENMEMİŞ", html)


if __name__ == "__main__":
    unittest.main()
