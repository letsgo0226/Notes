"""Executable regressions for the user's HSI-COSMIC-SOLUTION-IDENTITY/1."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from hsi_cosmic_solution_identity import (
    CORPUS_MAX_BYTES, PROGRAM, _d257, _e257, certificate, solution,
)


class SolutionIdentityTests(unittest.TestCase):
    def test_roundtrips_include_zeros_and_all_256_byte_values(self):
        samples = [b"", b"1+1=3", b"\x00\xffABC\x00", bytes(range(256)),
                   "宇宙之愛".encode("utf-8")]
        for source in samples:
            with self.subTest(n=len(source)):
                result, g = solution(source)
                self.assertEqual(source, result)
                self.assertEqual(source, _d257(g))
                self.assertEqual(g, _e257(source))

    def test_empty_string_godel_one(self):
        self.assertEqual((b"", 1), solution(b""))

    def test_certificate_is_deterministic_and_bound_to_input(self):
        a = certificate(b"Blue Stars")
        self.assertEqual(a, certificate(b"Blue Stars"))
        b = certificate(b"Blue Stars\x00")
        self.assertNotEqual(a["certificate_uid"], b["certificate_uid"])
        self.assertEqual(PROGRAM, a["program"])
        self.assertEqual("solution(s)=s", a["statement"])
        self.assertTrue(all(a["checks"].values()))
        self.assertEqual(a["input_sha256"], a["result_sha256"])
        self.assertTrue(a["validated"])

    def test_bounded_corpus_witness_does_not_limit_core_identity(self):
        payload = b"x" * (CORPUS_MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "bounded Corpus"):
            certificate(payload)
        restored, _ = solution(payload)
        self.assertEqual(restored, payload)

    def test_invalid_values_fail_closed(self):
        with self.assertRaises(TypeError):
            solution("not bytes")
        for g in (0, -1, 257, 514):
            with self.subTest(g=g), self.assertRaises(ValueError):
                _d257(g)

    def test_cli_preserves_exact_binary_stdin(self):
        script = Path(__file__).resolve().parents[1] / "hsi_cosmic_solution_identity.py"
        source = b"\x00\xffABC\x00"
        p = subprocess.run([sys.executable, str(script), "--stdin"], input=source,
                           capture_output=True, check=True)
        rows = p.stdout.decode("utf-8").splitlines()
        self.assertEqual(rows[0], "COSMIC_LOVE")
        record = json.loads(rows[1])
        self.assertEqual(record["s_hex"], source.hex())
        self.assertEqual(record["result_hex"], source.hex())
        self.assertEqual(record["godel_hex"], hex(_e257(source)))
        self.assertTrue(record["validated"])


if __name__ == "__main__":
    unittest.main()
