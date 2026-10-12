import json
from pathlib import Path
import tempfile
import unittest
from cosmic_love import provenance as p

class ProofScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.src=self.folder/'chat.txt';self.src.write_text('Sensitive chat body',encoding='utf8')
        self.consent=self.folder/'consent.json';self.journal=self.folder/'ledger.jsonl'
        self.cons={
            'protocol':p.CONSENT,'source_sha256':p.digest(self.src.read_bytes()),
            'source_type':'CHAT_EXPORT','purpose':'FINITE_RESEARCH_REVIEW',
            'granted':True,'raw_retention':'NONE'
        }
        self.consent.write_bytes(p.canonical(self.cons))
    def test_exact_consent_and_digest_only(self):
        row=p.observe(self.src,self.consent,self.journal)
        self.assertEqual(row['kind'],'SOURCE_OBSERVATION')
        ledger=self.journal.read_bytes();self.assertNotIn(b'Sensitive chat body',ledger)
        result=p.verify(p.parse_journal(ledger))
        self.assertEqual(result['events'],1)
        self.assertFalse(result['user_consent_identity_authenticated'])
    def test_denied_consent(self):
        self.cons['granted']=False;self.consent.write_bytes(p.canonical(self.cons))
        with self.assertRaises(ValueError):p.observe(self.src,self.consent,self.journal)
    def test_wrong_source_revision(self):
        self.src.write_bytes(b'changed')
        with self.assertRaises(ValueError):p.observe(self.src,self.consent,self.journal)
    def test_malformed_manifest(self):
        self.cons['extra']='x';self.consent.write_bytes(p.canonical(self.cons))
        with self.assertRaises(ValueError):p.observe(self.src,self.consent,self.journal)
    def test_wrong_purpose(self):
        self.cons['purpose']='AI_TRAINING';self.consent.write_bytes(p.canonical(self.cons))
        with self.assertRaises(ValueError):p.observe(self.src,self.consent,self.journal)
    def test_symlink_rejected(self):
        fake=self.folder/'alias';fake.symlink_to(self.src)
        with self.assertRaises(ValueError):p.observe(fake,self.consent,self.journal)
    def test_proposal_stays_unenacted(self):
        text=self.folder/'reason';text.write_text('candidate has bounded counterexample')
        event=p.propose(self.journal,'a'*64,'b'*64,'c'*64,text)
        self.assertEqual(event['payload']['status'],'REVIEW_REQUIRED')
        self.assertFalse(event['payload']['auto_deploy'])
        self.assertFalse(p.verify(p.parse_journal(self.journal.read_bytes()))['logic_updates_enacted'])
    def test_forged_enactment_rejected_even_rehashed(self):
        reason=self.folder/'reason';reason.write_text('counterexample')
        p.propose(self.journal,'a'*64,'b'*64,'c'*64,reason)
        row=json.loads(self.journal.read_text());row['payload']['enacted']=True
        row['digest']=p.digest(p.canonical({k:v for k,v in row.items() if k!='digest'}))
        with self.assertRaises(ValueError):p.parse_journal(p.canonical(row)+b'\n')
    def test_chain_reorder_rejected(self):
        p.observe(self.src,self.consent,self.journal)
        reason=self.folder/'reason';reason.write_text('counterexample')
        p.propose(self.journal,'a'*64,'b'*64,'c'*64,reason)
        lines=self.journal.read_bytes().splitlines()
        with self.assertRaises(ValueError):p.parse_journal(lines[1]+b'\n'+lines[0]+b'\n')
    def test_partial_write_rejected(self):
        p.observe(self.src,self.consent,self.journal)
        with self.assertRaises(ValueError):p.parse_journal(self.journal.read_bytes().rstrip(b'\n'))
    def test_boolean_index_rejected(self):
        p.observe(self.src,self.consent,self.journal)
        row=json.loads(self.journal.read_text());row['index']=True
        row['digest']=p.digest(p.canonical({k:v for k,v in row.items() if k!='digest'}))
        with self.assertRaises(ValueError):p.parse_journal(p.canonical(row)+b'\n')
    def test_no_global_proof(self):
        v=p.verify([])
        self.assertFalse(v['source_truth_proven']);self.assertFalse(v['externally_anchored'])
    def test_nonutf8_contents_hashed_without_copy(self):
        self.src.write_bytes(b'\x00\xff\xf0')
        self.cons['source_sha256']=p.digest(self.src.read_bytes())
        self.consent.write_bytes(p.canonical(self.cons))
        p.observe(self.src,self.consent,self.journal)
        self.assertEqual(p.parse_journal(self.journal.read_bytes())[0]['payload']['byte_length'],3)

if __name__=='__main__':unittest.main()
