import json
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from local_ai.cli import check_evidence, normalize_analysis, connect_db, report

class TestReviewer(unittest.TestCase):
    def setUp(self):
        self.record = {'environment':'local_lab','authorized':True,'target':'localhost','observation':'possible IDOR','evidence':[]}
    def test_reject_external(self):
        self.record['target'] = 'example.org'
        with self.assertRaises(ValueError): check_evidence(self.record)
    def test_reject_unauthorized(self):
        self.record['authorized'] = False
        with self.assertRaises(ValueError): check_evidence(self.record)
    def test_model_cannot_confirm(self):
        a=normalize_analysis({'status':'confirmed','explanation':'sure'}, self.record)
        self.assertEqual(a['status'],'insufficient_evidence')
        self.assertFalse(a['report_ready'])
    def test_report_draft(self):
        with tempfile.TemporaryDirectory() as t:
            with closing(connect_db(Path(t)/'db.sqlite')) as db:
                a = normalize_analysis({'status':'suspected', 'vulnerability_class':'IDOR', 'explanation':'Not proven', 'missing_evidence':[], 'recommended_next_step':'Inspect'}, self.record)
                db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?)', ('abc','now','test.json',json.dumps(self.record),'demo',json.dumps(a),0))
                db.commit()
                p = report(db,'abc',Path(t)/'draft.md')
                self.assertIn('NOT VERIFIED', p.read_text())
if __name__=='__main__': unittest.main()
