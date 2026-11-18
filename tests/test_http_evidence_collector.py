import unittest

from integration.http_evidence_collector import collect


class HTTPEvidenceCollectorTests(unittest.TestCase):

    def test_xss_evidence(self):
        result = collect("xss")
        self.assertTrue(result["deterministic_test_passed"])
        self.assertIn(
            "<script>",
            result["vulnerable"]["response"]["body"],
        )

    def test_ssrf_evidence(self):
        result = collect("ssrf")
        self.assertTrue(result["deterministic_test_passed"])
        self.assertEqual(
            result["safe"]["response"]["status"], 403
        )

    def test_access_evidence(self):
        result = collect("access")
        self.assertTrue(result["deterministic_test_passed"])
        self.assertEqual(
            result["vulnerable"]["response"]["status"], 200
        )

    def test_external_scenario_rejected(self):
        with self.assertRaises(ValueError):
            collect("https://example.com")


if __name__ == "__main__":
    unittest.main()
