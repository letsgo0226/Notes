"""Review-only semantic-adapter tests; fixtures are not generated audio."""
import json
import tempfile
import unittest
from pathlib import Path

from hsi_notes_review import git_blob_sha1
from hsi_notes_domains import DOCUMENT_RULES, EXPECTED_SOURCES, ReviewError, make_plan


class DomainPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = {'source_repo': 'letsgo0226/Notes', 'source_commit': 'f' * 40, 'entries': []}
        samples = {path: (a + ' ' + b + '\n').encode('utf-8') for path, _, (a, b), _ in DOCUMENT_RULES}
        for i in range(8):
            samples[f'Notes/HSI_Prime_Analytic_2KB_Release/reference{i}'] = f'audit-{i}\n'.encode()
        for i in range(4):
            samples[f'Notes/HSI_Sub2K_Program_Synthesizer/reference{i}'] = f'synth-audit-{i}\n'.encode()
        for i in range(EXPECTED_SOURCES - 16):
            samples[f'Notes/Dolphin_Logos_Riemann_Feedback/reference{i}'] = f'feedback-audit-{i}\n'.encode()
        for path, raw in samples.items():
            dest = self.root / path
            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.write_bytes(raw)
            self.lock['entries'].append({'path': path, 'bytes': len(raw), 'git_blob_sha1': git_blob_sha1(raw)})

    def test_plan_is_deterministic(self):
        a = make_plan(self.root, self.lock)
        b = make_plan(self.root, self.lock)
        self.assertEqual(a, b)
        self.assertEqual(a['plan_status'], 'READY_FOR_HUMAN_REVIEW_NOT_DEPLOYED')
        self.assertEqual(a['source_count'], EXPECTED_SOURCES)
        self.assertEqual(len(a['documents']), 4)

    def test_four_documents_and_locked_reference_sources(self):
        a = make_plan(self.root, self.lock)
        self.assertEqual(sum(x['role'] == 'concept_source' for x in a['all_source_files']), 4)
        self.assertEqual(sum(x['role'] == 'reference_and_audit_source' for x in a['all_source_files']), EXPECTED_SOURCES - 4)

    def test_all_domains_remain_unexecuted(self):
        a = make_plan(self.root, self.lock)
        self.assertTrue(all(x == 'NOT_EXECUTED_NOT_DEPLOYED' for x in a['domain_gates'].values()))
        self.assertEqual(len(a['domain_gates']), 6)
        self.assertFalse(a['claims']['remote_deployment'])
        self.assertFalse(a['claims']['generated_audio'])
        self.assertFalse(a['claims']['executed_orders'])

    def test_music_outputs_are_proposals(self):
        p = make_plan(self.root, self.lock)['domain_plans']
        self.assertIn('prime', p['music_native']['candidate_keywords'])
        self.assertFalse(p['music_corpus']['rights_verified'])
        self.assertEqual(p['music_ai_bridge']['external_api_calls'], 0)
        self.assertFalse(p['music_native']['audio_generated'])

    def test_trader_cannot_authorize_orders(self):
        t = make_plan(self.root, self.lock)['domain_plans']['trader_42']
        self.assertEqual(t['mode'], 'PAPER_ONLY')
        self.assertEqual(t['broker_calls'], 0)
        self.assertFalse(t['live_trading_authorized'])

    def test_utm_word_is_bounded_binary(self):
        w = make_plan(self.root, self.lock)['domain_plans']['utm']['finite_word']
        self.assertEqual(len(w), 32)
        self.assertLessEqual(set(w), {'0', '1'})

    def test_source_drift_fails_closed(self):
        (self.root / 'Notes/1').write_text('modified', encoding='utf-8')
        with self.assertRaises(ReviewError):
            make_plan(self.root, self.lock)

    def test_changed_heading_even_with_new_lock_rejected(self):
        p = self.root / 'Notes/2'
        data = b'something unrelated\n'
        p.write_bytes(data)
        for row in self.lock['entries']:
            if row['path'] == 'Notes/2':
                row.update(bytes=len(data), git_blob_sha1=git_blob_sha1(data))
        with self.assertRaisesRegex(ReviewError, 'heading'):
            make_plan(self.root, self.lock)

    def test_extra_file_fails_closed(self):
        (self.root / 'Notes/new').write_bytes(b'x')
        with self.assertRaises(ReviewError):
            make_plan(self.root, self.lock)

    def test_missing_file_fails_closed(self):
        (self.root / 'Notes/4').unlink()
        with self.assertRaises(ReviewError):
            make_plan(self.root, self.lock)

    def test_removed_reference_sources_fails(self):
        self.lock['entries'] = self.lock['entries'][:4]
        for p in (self.root / 'Notes/HSI_Prime_Analytic_2KB_Release').iterdir():
            p.unlink()
        with self.assertRaises(ReviewError):
            make_plan(self.root, self.lock)

    def test_missing_commit_pin_fails(self):
        self.lock['source_commit'] = ''
        with self.assertRaises(ReviewError):
            make_plan(self.root, self.lock)

    def test_plan_serializes(self):
        self.assertIsInstance(json.loads(json.dumps(make_plan(self.root, self.lock))), dict)

if __name__ == '__main__':
    unittest.main()
