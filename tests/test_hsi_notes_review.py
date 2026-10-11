import hashlib
import tempfile
import unittest
from pathlib import Path

from hsi_notes_review import PROTOCOL, audit, git_blob_sha1, valid_path


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Notes').mkdir()
        self.file = self.root / 'Notes' / '1'
        self.file.write_bytes(b'hello')
        self.lock = {
            'protocol': PROTOCOL,
            'entries': [{'path': 'Notes/1', 'bytes': 5, 'git_blob_sha1': git_blob_sha1(b'hello')}]
        }

    def test_clean_inventory(self):
        a = audit(self.root, self.lock)
        self.assertEqual(a['inventory_status'], 'SOURCE_INVENTORY_VERIFIED')
        self.assertEqual(a['observed']['Notes/1']['sha256'], hashlib.sha256(b'hello').hexdigest())
        self.assertTrue(all(v == 'NOT_TESTED_NOT_DEPLOYED' for v in a['domain_gates'].values()))

    def test_changed_file_rejected(self):
        self.file.write_bytes(b'HELLO')
        a = audit(self.root, self.lock)
        self.assertEqual(a['inventory_status'], 'REVIEW_REQUIRED')
        self.assertIn('source_mismatch', {x['type'] for x in a['issues']})

    def test_extra_file_rejected(self):
        (self.root / 'Notes' / 'extra').write_text('x')
        self.assertIn('unlocked_file', {x['type'] for x in audit(self.root, self.lock)['issues']})

    def test_missing_file_rejected(self):
        self.file.unlink()
        self.assertIn('missing_file', {x['type'] for x in audit(self.root, self.lock)['issues']})

    def test_duplicate_lock_entry_rejected(self):
        self.lock['entries'].append(dict(self.lock['entries'][0]))
        self.assertIn('invalid_lock_entry', {x['type'] for x in audit(self.root, self.lock)['issues']})

    def test_path_escape_rejected(self):
        for value in ('../Notes/1', 'Notes/../private', '/Notes/1', 'Notes\\file'):
            self.assertFalse(valid_path(value))

    def test_symlink_file_rejected(self):
        (self.root / 'outside').write_bytes(b'x')
        self.file.unlink()
        self.file.symlink_to(self.root / 'outside')
        self.assertIn('unsafe_file', {x['type'] for x in audit(self.root, self.lock)['issues']})

    def test_symlink_directory_rejected(self):
        (self.root / 'elsewhere').mkdir()
        (self.root / 'Notes' / 'linked').symlink_to(self.root / 'elsewhere', target_is_directory=True)
        self.assertIn('symlink_directory', {x['type'] for x in audit(self.root, self.lock)['issues']})


if __name__ == '__main__':
    unittest.main()
