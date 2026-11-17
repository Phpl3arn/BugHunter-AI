import unittest
from integration.mock_bridge import convert_mock

REPORT = '''# Engagement report — demo-local

In scope: `localhost`, `127.0.0.1`
## 1. IDOR — high
- **Evidence:** fake test
'''

class TestBridge(unittest.TestCase):
    def test_mock_remains_unverified(self):
        output = convert_mock(REPORT)
        self.assertEqual(output['evidence'], [])
        self.assertEqual(output['target'], 'localhost')
        self.assertIn('MOCK', output['observation'])
    def test_reject_non_demo_report(self):
        with self.assertRaises(ValueError):
            convert_mock(REPORT.replace('demo-local', 'production'))
    def test_reject_no_finding(self):
        with self.assertRaises(ValueError):
            convert_mock('# Engagement report — demo-local')
