import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integration import evidence_integrity as ei


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.root = Path(self.tmp.name)
        self.task_id = "test123abc"
        self.folder = self.root / self.task_id
        self.folder.mkdir()

        self.patcher = patch.object(ei, "RUNS", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        for name in ei.FILES:
            (self.folder / name).write_text(
                f"Original content: {name}",
                encoding="utf-8",
            )

    def seal(self):
        with contextlib.redirect_stdout(io.StringIO()):
            ei.seal(self.task_id)

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return ei.verify(self.task_id)

    def test_valid_evidence_passes(self):
        self.seal()
        self.assertTrue(self.verify())

    def test_modified_evidence_fails(self):
        self.seal()

        (self.folder / "evidence.json").write_text(
            "Modified evidence",
            encoding="utf-8",
        )

        self.assertFalse(self.verify())

    def test_deleted_evidence_fails(self):
        self.seal()

        (self.folder / "report.md").unlink()

        self.assertFalse(self.verify())

    def test_existing_seal_cannot_be_overwritten(self):
        self.seal()

        with self.assertRaises(FileExistsError):
            self.seal()

    def test_incomplete_evidence_cannot_be_sealed(self):
        (self.folder / "report.md").unlink()

        with self.assertRaises(ValueError):
            self.seal()


if __name__ == "__main__":
    unittest.main()
