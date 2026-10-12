"""Review-only candidate update gate: ensure no authority is granted by proof."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from cosmic_love import staging_update as u

COMMIT='c026a1f23a0912b083b0df6539dbbc39ebd4fc0d'

class CandidateGateTests(unittest.TestCase):
    def make(self,n=3):
        out=[]
        for _ in range(n):
            out.append(u.next_candidate(out,COMMIT))
        return out

    def test_hsi_seed(self):
        self.assertEqual(u.tm_program(2),55067263)

    def test_valid_certificate_chain(self):
        self.assertEqual(u.verify(self.make(4))['events'],4)

    def test_indefinite_tape_scope_is_formally_restricted(self):
        for k in (2,4,6,8,10):
            p,rows=u.rules(k)
            self.assertEqual(len(rows),2*k)
            self.assertTrue(p>0)

    def test_no_self_deployment_capability(self):
        first=self.make(1)[0]['body']['capabilities']
        self.assertFalse(first['runtime_can_deploy_itself'])
        self.assertEqual(first['scope'],'ISOLATED_STAGING_ONLY')
        self.assertFalse(first['trading'])

    def test_rehash_does_not_authorize_trading(self):
        chain=self.make(2)
        chain[1]['body']['capabilities']['trading']=True
        chain[1]['digest']=u.hashobj(chain[1]['body'])
        with self.assertRaises(ValueError):u.verify(chain)

    def test_rehash_does_not_authorize_deploy(self):
        chain=self.make(1)
        chain[0]['body']['capabilities']['deploy']='AUTOMATIC_ANYWHERE'
        chain[0]['digest']=u.hashobj(chain[0]['body'])
        with self.assertRaises(ValueError):u.verify(chain)

    def test_rehash_does_not_allow_refactor(self):
        chain=self.make(1)
        chain[0]['body']['rules_sha256']='a'*64
        chain[0]['digest']=u.hashobj(chain[0]['body'])
        with self.assertRaises(ValueError):u.verify(chain)

    def test_out_of_order_or_missing_entry_rejected(self):
        chain=self.make(3)
        with self.assertRaises(ValueError):u.verify(chain[1:])
        with self.assertRaises(ValueError):u.verify([chain[0],chain[2]])

    def test_wrong_commit_rejected(self):
        with self.assertRaises(ValueError):u.next_candidate([],'not-a-sha')

    def test_bounded_limit_holds(self):
        chain=self.make(16)
        with self.assertRaises(ValueError):u.next_candidate(chain,COMMIT)

    def test_no_side_effects_of_proposal(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'chain.json'
            path.write_text('[]')
            out=u.main(['--mode','check','--chain',str(path)])
            self.assertEqual(out,0)
            self.assertEqual(path.read_text(),'[]')

    def test_reject_malformed_schema_even_valid_hash(self):
        chain=self.make(1)
        chain[0]['body']['additional']='hidden-authorization'
        chain[0]['digest']=u.hashobj(chain[0]['body'])
        with self.assertRaises(ValueError):u.verify(chain)

if __name__=='__main__':unittest.main()
