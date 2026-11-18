import unittest
from integration.ai_evidence_validator import validate, report_section


def evidence():
    alice = '{"id":1,"owner":"alice","balance":120}'
    return {
        'environment': 'local_lab', 'authorized': True, 'synthetic_data': True,
        'deterministic_test_passed': True,
        'vulnerable_lab': {
            'alice': {'status': 200, 'body': alice},
            'bob': {'status': 200, 'body': alice},
            'anonymous': {'status': 401, 'body': ''}},
        'safe_lab': {
            'alice': {'status': 200, 'body': alice},
            'bob': {'status': 403, 'body': ''},
            'anonymous': {'status': 401, 'body': ''}},
    }


class ValidatorTests(unittest.TestCase):
    def test_correct_evidence_is_supported(self):
        result = validate(evidence(), {'explanation': 'Bob sends X-Demo-User: bob for Alice object; safe version denies.'})
        self.assertTrue(result['evidence_supported'])
        self.assertEqual(result['ai_claims_flagged'], [])
        self.assertFalse(result['external_submission_allowed'])

    def test_identity_hallucination_is_flagged(self):
        result = validate(evidence(), {'explanation': 'Bob accesses Alice by X-Demo-User: alice'})
        self.assertTrue(any('identity' in v for v in result['ai_claims_flagged']))
        self.assertFalse(result['ai_narrative_usable_without_correction'])

    def test_sanitization_is_flagged(self):
        result = validate(evidence(), {'explanation': 'Sanitize id parameter to fix IDOR'})
        self.assertTrue(any('sanitization' in v for v in result['ai_claims_flagged']))

    def test_external_overclaim_flagged(self):
        result = validate(evidence(), {'explanation': 'This is confirmed production vulnerability'})
        self.assertTrue(any('external verification' in v for v in result['ai_claims_flagged']))

    def test_failed_evidence_never_confirmed(self):
        record = evidence()
        record['safe_lab']['bob']['status'] = 200
        result = validate(record, {'explanation': 'Looks like IDOR'})
        self.assertFalse(result['evidence_supported'])
        self.assertEqual(result['status'], 'insufficient_evidence')

    def test_report_section_has_warning(self):
        result = validate(evidence(), {'explanation': 'Bob uses X-Demo-User: alice'})
        section = report_section(result)
        self.assertIn('Human approval required', section)
        self.assertIn('requiring correction', section)


if __name__ == '__main__':
    unittest.main()
