"""Offline, finite tests: no network, credentials, brokerage or writes."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator import build, digest, TARGETS


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'atgc_auto').mkdir()
        shutil.copy2(Path(__file__).resolve().parents[1] / 'atgc_self.sh', self.root / 'atgc_auto/atgc_self.sh')
        (self.root / 'Notes').mkdir()
        (self.root / 'Notes/1').write_bytes(b'one')
        for paths in TARGETS.values():
            for rel in paths:
                p = self.root / rel
                if rel == 'peace_av':
                    p.mkdir(parents=True, exist_ok=True)
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text('offline fixture\n', encoding='utf-8')
        (self.root / 'hsi_notes_review.py').write_text(
            "PROTOCOL='HSI-NOTES-FOUR-SYSTEM-REVIEW/0.1'\n"
            "def audit(root, lock):\n"
            " from pathlib import Path\n"
            " p=Path(root)/'Notes/1'\n"
            " return dict(inventory_status='SOURCE_INVENTORY_VERIFIED' if p.read_bytes()==b'one' else 'REVIEW_REQUIRED', expected_count=1, observed_count=1, issues=[])\n")
        (self.root / 'hsi_notes_review.lock.json').write_text(
            json.dumps({'protocol': 'HSI-NOTES-FOUR-SYSTEM-REVIEW/0.1'}))

    def test_self_recovers_and_no_authority(self):
        r = build(self.root)
        self.assertTrue(r['core']['self_reconstructed'], r['core'])
        self.assertEqual(r['core']['gc'], '1/2')
        self.assertEqual(r['decision'], 'REVIEW_READY_NOT_DEPLOYED')
        self.assertFalse(r['production_deployed'])
        self.assertFalse(any(v for k, v in r['permissions'].items() if k != 'read_repository'))
        self.assertEqual(len(r['certificate_sha256']), 64)

    def test_missing_component_blocks(self):
        (self.root / 'hsi_binance_orders.py').unlink()
        r = build(self.root)
        self.assertEqual(r['decision'], 'HOLD_REVIEW_REQUIRED')
        self.assertEqual(r['targets']['trader_42_research']['status'], 'HOLD')

    def test_notes_drift_blocks(self):
        (self.root / 'Notes/1').write_text('different')
        self.assertEqual(build(self.root)['decision'], 'HOLD_REVIEW_REQUIRED')

    def test_tamper_core_blocks(self):
        (self.root / 'atgc_auto/atgc_self.sh').write_text('exit 1\n')
        self.assertEqual(build(self.root)['decision'], 'HOLD_REVIEW_REQUIRED')


if __name__ == '__main__':
    unittest.main()
