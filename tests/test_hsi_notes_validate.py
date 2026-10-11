"""Negative checks for execution boundaries and independent WAV validation."""
from array import array
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

from hsi_notes_domains import ReviewError
from hsi_notes_validate import ROOT, check_parameters, clean_environment, d257, measure_wav, run_validation, verify_runtime


class AudioValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'test.wav'

    def write_audio(self, values, channels=1):
        samples = array('h', values)
        if sys.byteorder != 'little':
            samples.byteswap()
        with wave.open(str(self.path), 'wb') as output:
            output.setnchannels(channels)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(samples.tobytes())

    def test_real_pcm_is_measured_without_certificate_flags(self):
        self.write_audio([1000, -1000] * 4000)
        metrics = measure_wav(self.path, 8000)
        self.assertEqual(metrics['frames'], 8000)
        self.assertEqual(metrics['duration_seconds'], 1)
        self.assertAlmostEqual(metrics['rms'], 1000 / 32768)

    def test_silence_rejected(self):
        self.write_audio([0] * 8000)
        with self.assertRaises(ReviewError):
            measure_wav(self.path, 8000)

    def test_clipped_audio_rejected(self):
        self.write_audio([32767, -32768] * 4000)
        with self.assertRaises(ReviewError):
            measure_wav(self.path, 8000)

    def test_truncated_frames_rejected(self):
        self.write_audio([1000, -1000] * 4000)
        self.path.write_bytes(self.path.read_bytes()[:-10])
        with self.assertRaises(ReviewError):
            measure_wav(self.path, 8000)

    def test_wrong_channel_count_rejected(self):
        self.write_audio([1000, -1000] * 4000, channels=2)
        with self.assertRaises(ReviewError):
            measure_wav(self.path, 8000)

    def test_bad_e257_digits_and_types_rejected(self):
        for value in (0, -1, True, 257, '1'):
            with self.subTest(value=value), self.assertRaises(ReviewError):
                d257(value)


class ExecutionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'root'
        self.root.mkdir()
        for name in ('Notes', 'validation_snapshots'):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ('hsi_native_renderer.py', 'hsi_notes_runtime.lock.json', 'hsi_notes_review.lock.json'):
            shutil.copyfile(ROOT / name, self.root / name)
        self.out = self.base / 'output'

    def assert_no_execution(self):
        with patch('hsi_notes_validate.render_native') as native:
            with self.assertRaises(ReviewError):
                run_validation(self.root, self.out)
            native.assert_not_called()

    def test_notes_drift_rejected_before_render(self):
        p = self.root / 'Notes/1'
        p.write_bytes(p.read_bytes() + b'changed')
        self.assert_no_execution()

    def test_renderer_drift_rejected_before_render(self):
        p = self.root / 'hsi_native_renderer.py'
        p.write_bytes(p.read_bytes() + b'changed')
        self.assert_no_execution()

    def test_common_gate_drift_rejected_before_render(self):
        p = self.root / 'validation_snapshots/hsi_three_system_core.py'
        p.write_bytes(p.read_bytes() + b'changed')
        self.assert_no_execution()

    def test_existing_output_is_preserved(self):
        self.out.mkdir()
        self.assert_no_execution()
        self.assertEqual(list(self.out.iterdir()), [])

    def test_symlink_runtime_is_rejected(self):
        p = self.root / 'hsi_native_renderer.py'
        p.unlink()
        p.symlink_to(ROOT / 'hsi_native_renderer.py')
        self.assert_no_execution()

    def test_bad_runtime_lock_protocol_rejected(self):
        p = self.root / 'hsi_notes_runtime.lock.json'
        lock = json.loads(p.read_text())
        lock['protocol'] = 'UNKNOWN'
        with self.assertRaises(ReviewError):
            verify_runtime(self.root, lock)

    def test_host_hsi_state_and_unbounded_limit_are_removed(self):
        with patch.dict(os.environ, {'HSI_LIMIT': '0', 'HSI_STATE': '/existing/state', 'HSI_CAND': 'bad'}):
            env = clean_environment(HSI_LIMIT='32')
        self.assertEqual(env['HSI_LIMIT'], '32')
        self.assertNotIn('HSI_STATE', env)
        self.assertNotIn('HSI_CAND', env)

    def test_resource_parameters_are_bounded(self):
        for values in ((8000, 0, 4), (96000, 120, 4), (8000, 120, 999), (True, 120, 4)):
            with self.subTest(values=values), self.assertRaises(ReviewError):
                check_parameters(*values)


if __name__ == '__main__':
    unittest.main()
