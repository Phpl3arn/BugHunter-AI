import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab import compare_idor


class TestLabValidation(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.output = Path(self.temp.name)

        alice = '{"id":1,"owner":"alice","balance":120}'
        bob = '{"id":2,"owner":"bob","balance":250}'

        self.responses = {
            (3002, "alice"): {"status": 200, "body": alice},
            (3002, "bob"): {"status": 200, "body": alice},
            (3002, None): {"status": 401, "body": ""},
            (3003, "alice"): {"status": 200, "body": alice},
            (3003, "bob"): {"status": 403, "body": ""},
            (3003, None): {"status": 401, "body": ""},
        }

        self.bob_account = bob

    def verify(self, expected):
        responses = copy.deepcopy(self.responses)

        def fake_fetch(port, user):
            return responses[(port, user)]

        with (
            patch.object(compare_idor, "fetch", side_effect=fake_fetch),
            patch.object(compare_idor, "OUT", self.output),
            patch.object(sys, "argv", ["compare_idor.py"]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            if expected:
                compare_idor.main()
            else:
                with self.assertRaises(SystemExit) as error:
                    compare_idor.main()
                self.assertEqual(error.exception.code, 1)

        path = self.output / "idor-comparison.json"
        self.assertTrue(path.is_file())

        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertIs(
            record["deterministic_test_passed"],
            expected
        )

        review_path = self.output / "idor-comparison-review.json"
        self.assertEqual(review_path.exists(), expected)

    def test_01_vulnerable_idor_detected(self):
        self.verify(True)

    def test_02_owner_access_denied(self):
        self.responses[(3002, "alice")]["status"] = 403
        self.verify(False)

    def test_03_bob_access_denied(self):
        self.responses[(3002, "bob")]["status"] = 403
        self.verify(False)

    def test_04_anonymous_access_allowed(self):
        self.responses[(3002, None)]["status"] = 200
        self.verify(False)

    def test_05_wrong_account_owner(self):
        self.responses[(3002, "alice")]["body"] = self.bob_account
        self.responses[(3002, "bob")]["body"] = self.bob_account
        self.verify(False)

    def test_06_different_response_bodies(self):
        self.responses[(3002, "bob")]["body"] = self.bob_account
        self.verify(False)

    def test_07_malformed_json(self):
        self.responses[(3002, "alice")]["body"] = "{invalid"
        self.verify(False)

    def test_08_safe_owner_access_denied(self):
        self.responses[(3003, "alice")]["status"] = 403
        self.verify(False)

    def test_09_safe_app_allows_bob(self):
        self.responses[(3003, "bob")]["status"] = 200
        self.verify(False)

    def test_10_safe_anonymous_access_allowed(self):
        self.responses[(3003, None)]["status"] = 200
        self.verify(False)

    def test_11_unexpected_server_error(self):
        self.responses[(3002, "bob")]["status"] = 500
        self.verify(False)


if __name__ == "__main__":
    unittest.main()
