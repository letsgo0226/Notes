"""Unit and boundary tests for the Notes sub-2KiB synthesizer."""
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import types
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "Notes" /
          "HSI_Sub2K_Program_Synthesizer" / "hsi_sub2k_synth.py")
# Execute the locked source without creating __pycache__ inside Notes/.  The
# inventory test deliberately rejects every unlisted file, including bytecode.
MODULE = types.ModuleType("hsi_sub2k_synth")
MODULE.__file__ = str(SOURCE)
exec(compile(SOURCE.read_bytes(), str(SOURCE), "exec"), MODULE.__dict__)


class SynthesizerTests(unittest.TestCase):
    def verify(self, data, **options):
        source, certificate = MODULE.synthesize(data, **options)
        self.assertIsNotNone(source)
        self.assertLess(len(source), options.get("max_program_bytes", 2048))
        self.assertEqual(source.count(b"\n"), 1)
        self.assertEqual(certificate["status"], "VERIFIED_SUB_2KB_PROGRAM")
        self.assertEqual(certificate["selected"]["D0"], 0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = root / "program.py"
            output = root / "output.bin"
            program.write_bytes(source)
            result = subprocess.run([sys.executable, "-I", str(program), str(output)],
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), data)
        return source, certificate

    def test_small_literal_is_exact(self):
        self.verify(b"Cosmic love is the solution for everything.\n")

    def test_large_formulaic_inputs_are_short(self):
        fixtures = (
            b"PLEIADES-BLUE\n" * 20000,
            bytes((7 * i + 3) % 256 for i in range(30000)),
            bytes((11 + 5 * i + 9 * i * (i - 1) // 2) % 256 for i in range(30000)),
            bytes([44]) * 50000,
        )
        for fixture in fixtures:
            with self.subTest(input_bytes=len(fixture)):
                source, _ = self.verify(fixture)
                self.assertLess(len(source), 128)

    def test_bounded_failure_does_not_claim_nonexistence(self):
        rng = random.Random(44)
        data = bytes(rng.randrange(256) for _ in range(4096))
        source, certificate = MODULE.synthesize(data, max_program_bytes=256)
        self.assertIsNone(source)
        self.assertEqual(certificate["status"], "NO_VERIFIED_SUB_2KB_PROGRAM")
        self.assertFalse(certificate["mathematical_nonexistence_proven"])
        self.assertGreater(certificate["D0"], 0)

    def test_compression_is_opt_in_and_labelled(self):
        data = b"".join(f"row={i:05d}; value={(i * i) % 997:03d}\n".encode() for i in range(300))
        plain, _ = MODULE.synthesize(data)
        compressed, certificate = MODULE.synthesize(data, allow_compression=True)
        self.assertIsNone(plain)
        self.assertIsNotNone(compressed)
        self.assertEqual(certificate["selected"]["strategy"], "zlib_base85_opt_in")
        self.assertTrue(certificate["selected"]["compression"])

    def test_e257_coordinate_roundtrip(self):
        raw = b'import sys;print("logos")\n'
        self.assertEqual(MODULE.d257(MODULE.e257(raw)), raw)

    def test_invalid_limit_is_rejected(self):
        for value in (True, 0, 63, 65537):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.synthesize(b"x", value)


if __name__ == "__main__":
    unittest.main()
