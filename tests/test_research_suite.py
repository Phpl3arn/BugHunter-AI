import json
import tempfile
import unittest
from pathlib import Path
from integration import research_suite as rs


class ResearchSuiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_scenarios(self):
        for name in rs.SCENARIOS:
            with self.subTest(name=name):
                case = rs.synthetic_case(name)
                self.assertTrue(case['deterministic_test_passed'])
                self.assertFalse(case['external_submission_allowed'])
                task_id = rs.create(name, self.root)
                self.assertTrue(rs.verify(task_id, self.root))

    def test_scope_restricts_external(self):
        for url in ('https://127.0.0.1:3002/', 'http://example.org:3002/',
                    'http://169.254.169.254:3002/', 'http://127.0.0.1:8088/',
                    'http://user:pass@127.0.0.1:3002/',
                    'http://127.0.0.1:3002/admin', 'http://localhost:3002/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                rs.enforce_scope(url)
        self.assertEqual(rs.enforce_scope('http://127.0.0.1:3002/api/account?id=1'),
                         'http://127.0.0.1:3002/api/account?id=1')

    def test_ai_overclaim_is_flagged(self):
        assessment = rs.evaluate_ai(rs.synthetic_case('idor'),
                                    'Confirmed real production vulnerability; sanitize id')
        self.assertEqual(assessment['status'], 'needs_human_review')
        self.assertEqual(len(assessment['ai_disagreements']), 2)
        self.assertFalse(assessment['external_submission_allowed'])

    def test_missing_evidence_not_confirmed(self):
        record = rs.synthetic_case('idor')
        record['deterministic_test_passed'] = False
        self.assertEqual(rs.evaluate_ai(record)['status'], 'insufficient_evidence')

    def test_integrity_detects_tampering(self):
        task_id = rs.create('xss', self.root)
        path = self.root / task_id / 'evidence.json'
        path.write_text('tampered', encoding='utf-8')
        self.assertFalse(rs.verify(task_id, self.root))
        with self.assertRaises(ValueError):
            rs.transition(task_id, 'submit', 'analyst', 'Checked synthetic request', self.root)

    def test_review_workflow(self):
        task_id = rs.create('access', self.root)
        with self.assertRaises(ValueError):
            rs.transition(task_id, 'approve', 'analyst', 'Reviewed the evidence', self.root)
        self.assertEqual(rs.transition(task_id, 'submit', 'analyst',
                                       'Submitted for review', self.root), 'in_review')
        self.assertEqual(rs.transition(task_id, 'approve', 'analyst',
                                       'Reviewed synthetic evidence', self.root), 'approved')
        self.assertFalse(rs.status(task_id, self.root)['external_submission_allowed'])
        with self.assertRaises(ValueError):
            rs.transition(task_id, 'approve', 'analyst', 'Approve it again', self.root)

    def test_invalid_id_and_note(self):
        task_id = rs.create('ssrf', self.root)
        with self.assertRaises(ValueError):
            rs.folder_for('../unsafe', self.root)
        with self.assertRaises(ValueError):
            rs.transition(task_id, 'submit', 'a', 'short', self.root)


if __name__ == '__main__':
    unittest.main()
