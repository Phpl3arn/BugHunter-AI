import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dashboard import server
from dashboard import v2_actions
from integration import research_suite as rs
from integration import lab_verifier


class DashboardV2Tests(unittest.TestCase):
    def test_scenario_start_and_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_create = rs.create
            with patch.object(rs, 'DATA', root), patch('dashboard.v2_actions.rs.create', side_effect=lambda scenario, use_ollama=False: original_create(scenario, root, use_ollama=use_ollama)) as maker:
                path = v2_actions.apply('/research/start', {'scenario': ['xss']})
                task_id = path.split('/')[-1]
                maker.assert_called_once()
                self.assertEqual(rs.status(task_id, root)['review_status'], 'draft')
                original_transition = rs.transition
                with patch('dashboard.v2_actions.rs.transition', side_effect=lambda tid, action, reviewer, note: original_transition(tid, action, reviewer, note, root)):
                    self.assertEqual(v2_actions.apply('/research/review', {
                        'task_id': [task_id], 'action': ['submit'],
                        'reviewer': ['Researcher'], 'note': ['Reviewed synthetic case']
                    }), path)
                self.assertEqual(rs.status(task_id, root)['review_status'], 'in_review')

    def test_invalid_scenario_rejected(self):
        with self.assertRaises(ValueError):
            v2_actions.apply('/research/start', {'scenario': ['external']})
        with self.assertRaises(ValueError):
            v2_actions.apply('/research/start', {'scenario': ['xss', 'ssrf']})

    def test_local_verifier_no_redirect(self):
        with self.assertRaises(ValueError):
            lab_verifier.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com')

    def test_dashboard_renders_new_controls(self):
        with patch.object(server, 'get_tasks', return_value=[]), patch('integration.healthcheck.check_all', return_value={}), patch('dashboard.research_view.listing', return_value='LOCAL_RESEARCH_LIST'):
            page = server.page()
        self.assertIn('LOCAL_RESEARCH_LIST', page)
        self.assertIn('action="/research/start"', page)


if __name__ == '__main__':
    unittest.main()
