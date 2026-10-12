"""Independent smoke/negative tests for finite proof-gated persistent worker."""
import json
from pathlib import Path
import tempfile
import unittest
from cosmic_love import closure_worker as w

class WorkerTests(unittest.TestCase):
    def test_seed_and_all_rules(self):
        self.assertEqual(w.program(2),55067263)
        old=[]
        for k in (2,4,6,8):
            old=w.prove(k,w.program(k),old)
            self.assertEqual(len(old),2*k)
    def test_persistence_and_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal'
            a=w.advance(p,4);b=w.advance(p,4)
            self.assertEqual([a['k'],b['k']],[2,4])
            self.assertIsNone(w.advance(p,4))
            self.assertEqual(w.verify_rows(w.load(p.read_bytes()))['stages'],2)
    def test_reject_forged_permission_after_rehash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal';w.advance(p,4)
            row=json.loads(p.read_text());row['authorization']['trade']=True
            row['digest']=w.sha(w.canon({x:y for x,y in row.items() if x!='digest'}))
            with self.assertRaises(ValueError):w.load(w.canon(row))
    def test_reject_forged_rule_after_rehash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal';w.advance(p,4)
            row=json.loads(p.read_text());row['rules_sha256']='0'*64
            row['digest']=w.sha(w.canon({x:y for x,y in row.items() if x!='digest'}))
            with self.assertRaises(ValueError):w.load(w.canon(row))
    def test_reject_corrupt_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal';w.advance(p,4);w.advance(p,4)
            rows=p.read_text().splitlines();v=json.loads(rows[1]);v['prev']='f'*64
            v['digest']=w.sha(w.canon({x:y for x,y in v.items() if x!='digest'}))
            with self.assertRaises(ValueError):w.load((rows[0]+'\n'+w.canon(v).decode()).encode())
    def test_no_retroactive_general_truth_claim(self):
        self.assertFalse(w.verify_rows([])['globally_complete'])
        self.assertFalse(w.verify_rows([])['externally_anchored'])
    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d); target=path/'base';target.write_text('')
            (path/'alias').symlink_to(target)
            with self.assertRaises(ValueError):w.advance(path/'alias',4)
if __name__=='__main__':unittest.main()
