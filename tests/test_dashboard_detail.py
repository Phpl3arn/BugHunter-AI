import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import task_detail


class DashboardDetailTests(unittest.TestCase):

    def test_invalid_task_id_rejected(self):
        self.assertIsNone(
            task_detail.render("../secret")
        )

    def test_unknown_task_returns_none(self):
        class FakeDB:
            def execute(self, *args):
                return self

            def fetchone(self):
                return None

        class FakeConnection:
            def __enter__(self):
                return FakeDB()

            def __exit__(self, *args):
                return False

        with patch.object(
            task_detail,
            "connect",
            return_value=FakeConnection()
        ):
            self.assertIsNone(
                task_detail.render("unknown123")
            )

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"

            result = task_detail.read_limited(path)

            self.assertIn(
                "dosya bulunamadı",
                result
            )

    def test_html_escape(self):
        result = task_detail.escape("<script>alert(1)</script>")

        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)


if __name__ == "__main__":
    unittest.main()
