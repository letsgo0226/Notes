import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'scripts/runtime_guard.py'
if not GUARD.exists():
    GUARD = ROOT / 'hsi_runtime_guard.py'
spec = importlib.util.spec_from_file_location('runtime_guard_under_test', GUARD)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RuntimeGuardTests(unittest.TestCase):
    def daemon(self):
        return dict(timestamp='2026-10-15T00:00:00Z', release_commit='abc',
                    runtime_generation='new', cycle=3, core_ok=True,
                    controller_ok=True, daemon_healthy=True, errors=0)

    def check(self, state):
        return m.check_daemon(state, 'abc', 'new', 1792022405, 180)

    def test_fresh_daemon_cycle_is_ready(self):
        self.assertTrue(self.check(self.daemon())['healthy'])

    def test_previous_child_and_stale_or_future_certificates_are_rejected(self):
        for change in ({'runtime_generation': 'old'}, {'timestamp': '2026-10-14T23:00:00Z'},
                       {'timestamp': '2026-10-16T00:00:00Z'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check({**self.daemon(), **change})

    def test_core_success_cannot_hide_stage_failure_or_wrong_release(self):
        for change in ({'controller_ok': False}, {'errors': 1}, {'release_commit': 'wrong'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check({**self.daemon(), **change})

    def test_native_preview_hash_and_release_are_checked(self):
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            wav.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\x01\x01' * 80)
        audio = output.getvalue()
        health = dict(ok=True, selftest='PASSED', role='MUSIC', notes={'release_commit': 'abc'})
        evidence = dict(notes={'release_commit': 'abc'}, result={'native': {
            'status': 'LOCAL_AUDIO_VERIFIED', 'audio_sha256': hashlib.sha256(audio).hexdigest(),
            'metrics': {'rms': .01}}})
        self.assertTrue(m.check_notes(health, evidence, audio, 'abc')['audio_verified'])
        with self.assertRaises(ValueError):
            m.check_notes(health, evidence, audio + b'corrupt', 'abc')
        with self.assertRaises(ValueError):
            m.check_notes(health, evidence, audio, 'wrong')

    def test_restart_budget_exhausts_and_only_recovers_after_window(self):
        budget = m.Budget()
        self.assertEqual([budget.take(t) for t in (0, 10, 20, 30, 3599, 3600)],
                         [True, True, True, False, False, True])

    def test_dead_child_cannot_pass_from_cached_success(self):
        guard = m.Guard('daemon', [])
        child = unittest.mock.Mock()
        child.poll.return_value = 1
        guard.child = child
        self.assertFalse(guard.probe()['healthy'])

    def test_repeated_failure_restarts_once_and_healthy_recovery_resets_counter(self):
        guard = m.Guard('notes', ['unused'], interval=0, startup=0, failures=3)
        guard.child = unittest.mock.Mock()
        guard.child.poll.return_value = None
        guard.stop = unittest.mock.Mock()
        guard.stop.is_set.side_effect = [False] * 5 + [True]
        guard.stop.wait.return_value = False
        outcomes = [{'healthy': False}] * 3 + [{'healthy': True}, {'healthy': False}]
        with patch.object(guard, 'launch') as launch, patch.object(guard, 'terminate'), \
             patch.object(guard, 'log'), patch.object(guard, 'probe', side_effect=outcomes):
            self.assertEqual(guard.run(), 0)
        self.assertEqual(launch.call_count, 2)

    def test_restart_budget_exhaustion_fails_instead_of_looping(self):
        guard = m.Guard('notes', ['unused'], interval=0, startup=0, failures=1)
        guard.child = unittest.mock.Mock()
        guard.child.poll.return_value = 1
        guard.stop = unittest.mock.Mock()
        guard.stop.is_set.return_value = False
        guard.stop.wait.return_value = False
        with patch.object(guard, 'launch') as launch, patch.object(guard, 'terminate'), \
             patch.object(guard, 'log'), patch.object(guard, 'probe', return_value={'healthy': False}):
            self.assertEqual(guard.run(), 1)
        self.assertEqual(launch.call_count, 4)  # initial start plus three repairs

    def test_daemon_http_readiness_returns_503_then_200(self):
        guard = m.Guard('daemon', [])
        guard.port = 0
        with patch.object(guard, 'probe', return_value={'healthy': False}):
            server = guard.serve_daemon_health()
            try:
                url = f'http://127.0.0.1:{server.server_port}/health'
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(url)
                self.assertEqual(error.exception.code, 503)
                with patch.object(guard, 'probe', return_value={'healthy': True, 'release_commit': 'abc'}):
                    with urllib.request.urlopen(url) as response:
                        self.assertTrue(json.load(response)['healthy'])
            finally:
                server.shutdown()
                server.server_close()

    def test_termination_reaps_real_child(self):
        guard = m.Guard('notes', [sys.executable, '-c', 'import time; time.sleep(30)'])
        with patch.object(guard, 'log'):
            guard.launch()
        self.assertIsNone(guard.child.poll())
        guard.terminate()
        self.assertIsNotNone(guard.child.poll())


if __name__ == '__main__':
    unittest.main()
