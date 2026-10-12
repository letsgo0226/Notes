"""Offline signed backup / detached anchor / isolated recovery negative tests."""
import json
from pathlib import Path
import tempfile
import unittest

from cosmic_love import closure_worker as worker
from cosmic_love import provenance as prov
from cosmic_love import recovery as rec


class SignedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)
        self.private=self.p/'not-for-git.key'
        self.public=self.p/'trusted.pub'
        self.snapshot=self.p/'snap.json'
        self.anchor=self.p/'anchor.json'
        self.w=self.p/'cosmic-love.jsonl'
        self.s=self.p/'source-receipts.jsonl'
        rec.keygen(self.private,self.public)
        self.assertEqual(self.private.stat().st_mode & 0o777,0o600)
        worker.advance(self.w,4)
        worker.advance(self.w,4)
        self.s.write_bytes(b'')

    def take(self):
        rec.snapshot(self.w,self.s,self.private,self.snapshot,self.anchor)

    def test_signature_and_isolated_restore(self):
        self.take()
        v,raw=rec.verify(self.snapshot,self.anchor,self.public)
        self.assertEqual(v['worker_stages'],2)
        self.assertEqual(v['source_events'],0)
        self.assertFalse(v['globally_complete'])
        self.assertFalse(v['externally_published_anchor_checked'])
        restored=rec.restore(self.snapshot,self.anchor,self.public,self.p/'restored')
        self.assertEqual(restored['status'],'RESTORED_IN_ISOLATED_DIRECTORY')
        self.assertEqual((self.p/'restored/cosmic-love.jsonl').read_bytes(),self.w.read_bytes())
        self.assertEqual((self.p/'restored/source-receipts.jsonl').read_bytes(),self.s.read_bytes())
        self.assertEqual(worker.load((self.p/'restored/cosmic-love.jsonl').read_bytes())[-1]['k'],4)

    def test_source_chain_snapshotted_and_revalidated(self):
        reason=self.p/'reason.txt';reason.write_text('bounded counterexample, not proven refutation')
        prov.propose(self.s,'a'*64,'b'*64,'c'*64,reason)
        self.take()
        r, _=rec.verify(self.snapshot,self.anchor,self.public)
        self.assertEqual(r['source_events'],1)
        recovered=rec.restore(self.snapshot,self.anchor,self.public,self.p/'restored')
        self.assertEqual(recovered['source_events'],1)
        self.assertEqual(len(prov.parse_journal((self.p/'restored/source-receipts.jsonl').read_bytes())),1)

    def test_snapshot_tamper_detected(self):
        self.take()
        doc=json.loads(self.snapshot.read_text())
        doc['body']['journals']['worker']['sha256']='0'*64
        self.snapshot.write_bytes(rec.canonical(doc)+b'\n')
        with self.assertRaises(ValueError):rec.verify(self.snapshot,self.anchor,self.public)

    def test_anchor_tamper_detected(self):
        self.take()
        doc=json.loads(self.anchor.read_text());doc['body']['worker_head']='a'*64
        self.anchor.write_bytes(rec.canonical(doc)+b'\n')
        with self.assertRaises(ValueError):rec.verify(self.snapshot,self.anchor,self.public)

    def test_mismatched_detached_anchor_detected(self):
        self.take()
        other=self.p/'other.json';another=self.p/'another.json'
        # Make the second snapshot genuinely different rather than merely renamed.
        reason=self.p/'reason-2.txt';reason.write_text('independent finite candidate')
        prov.propose(self.s,'a'*64,'b'*64,'c'*64,reason)
        rec.snapshot(self.w,self.s,self.private,other,another)
        with self.assertRaises(ValueError):rec.verify(self.snapshot,another,self.public)

    def test_wrong_trusted_public_key_detected(self):
        self.take()
        rec.keygen(self.p/'untrusted.key',self.p/'untrusted.pub')
        with self.assertRaises(ValueError):rec.verify(self.snapshot,self.anchor,self.p/'untrusted.pub')

    def test_refuse_existing_recovery_directory(self):
        self.take()
        out=self.p/'restored';out.mkdir()
        (out/'important.txt').write_text('do not touch')
        with self.assertRaises(ValueError):rec.restore(self.snapshot,self.anchor,self.public,out)
        self.assertEqual((out/'important.txt').read_text(),'do not touch')

    def test_no_overwrite_of_snapshot_or_anchor(self):
        self.take()
        with self.assertRaises(ValueError):self.take()

    def test_reject_partial_worker_ledger(self):
        self.w.write_bytes(self.w.read_bytes().rstrip(b'\n'))
        with self.assertRaises(ValueError):self.take()

    def test_refuse_world_readable_private_key(self):
        self.private.chmod(0o644)
        with self.assertRaises(ValueError):self.take()

    def test_refuse_journal_symlink(self):
        link=self.p/'alias.jsonl';link.symlink_to(self.w)
        with self.assertRaises(OSError):rec.snapshot(link,self.s,self.private,self.snapshot,self.anchor)

    def test_keeps_original_journal_unchanged_during_restore(self):
        self.take()
        before=self.w.read_bytes()
        rec.restore(self.snapshot,self.anchor,self.public,self.p/'copy')
        self.assertEqual(self.w.read_bytes(),before)
        self.assertFalse((self.p/'copy/RESTORE_REPORT.json').is_symlink())

if __name__ == '__main__':unittest.main()
