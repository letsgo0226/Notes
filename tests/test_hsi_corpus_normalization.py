"""Actual PCM regression for quiet sources, silence, and peak limiting."""
import math
from pathlib import Path
import tempfile
import unittest
from hsi_open_corpus import write_wav, audio_features


class CorpusNormalizationTests(unittest.TestCase):
    def test_quiet_material_becomes_audible_without_creating_sound_from_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'audio.wav'
            quiet = [.025 * math.sin(2 * math.pi * 440 * i / 8000) for i in range(8000)]
            write_wav(path, quiet, quiet, 8000)
            metrics = audio_features(path)
            self.assertGreater(metrics['rms'], .025)
            self.assertGreater(metrics['peak'], .15)
            self.assertLess(metrics['peak'], .9)
            self.assertEqual(metrics['clip_ratio'], 0)
            write_wav(path, [0.0] * 8000, [0.0] * 8000, 8000)
            self.assertEqual(audio_features(path)['rms'], 0)
            loud = [value * 1000 for value in quiet]
            write_wav(path, loud, loud, 8000)
            self.assertLess(audio_features(path)['peak'], .9)
            self.assertEqual(audio_features(path)['clip_ratio'], 0)


if __name__ == '__main__':
    unittest.main()
