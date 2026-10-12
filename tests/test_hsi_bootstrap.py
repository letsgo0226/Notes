"""Verify bundle completeness and reject corruption before launching code."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hsi_bootstrap

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def fetch(self, url):
        if 'api.github.com' in url:
            return json.dumps({'sha': 'a' * 40}).encode()
        path = url.split('/' + 'a' * 40 + '/', 1)[1]
        return (ROOT / path).read_bytes()

    def test_complete_bundle_reused_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(hsi_bootstrap, 'fetch', side_effect=self.fetch):
            installed = hsi_bootstrap.install(tmp, 'fixture')
            self.assertTrue((installed / 'Notes/4').is_file())
            self.assertTrue((installed / 'hsi_render_policy.json').is_file())
            self.assertTrue((installed / 'hsi_bundle.lock.json').is_file())
            self.assertEqual(hsi_bootstrap.install(tmp, 'fixture'), installed)
            (installed / 'Notes/1').write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                hsi_bootstrap.install(tmp, 'fixture')

    def test_path_escape_is_rejected_before_download(self):
        lock = json.loads((ROOT / 'hsi_bundle.lock.json').read_text())
        lock['files'][0]['path'] = '../escape'
        def malicious(url):
            return json.dumps({'sha': 'a' * 40}).encode() if 'api.github.com' in url else json.dumps(lock).encode()
        with tempfile.TemporaryDirectory() as tmp, patch.object(hsi_bootstrap, 'fetch', side_effect=malicious):
            with self.assertRaises(ValueError):
                hsi_bootstrap.install(tmp, 'fixture')

    def test_full_commit_pin_needs_no_branch_resolution(self):
        def pinned_fetch(url):
            if 'api.github.com' in url:
                raise AssertionError('Pinned SHA must not consume a ref-resolution request')
            return self.fetch(url)
        with tempfile.TemporaryDirectory() as tmp, patch.object(hsi_bootstrap, 'fetch', side_effect=pinned_fetch):
            installed = hsi_bootstrap.install(tmp, 'a' * 40)
            self.assertTrue((installed / 'Notes/4').is_file())

    def test_deployment_syntax_validation_never_modifies_notes(self):
        from hsi_deploy import validate_target
        before = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in (ROOT / 'Notes').rglob('*') if p.is_file()}
        self.assertTrue(all(validate_target('self', ROOT).values()))
        after = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in (ROOT / 'Notes').rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(len(after), 32)


if __name__ == '__main__':
    unittest.main()
