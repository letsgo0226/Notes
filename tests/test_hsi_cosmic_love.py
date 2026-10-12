"""Tests for the exact HSI COSMIC_LOVE cycle; no trading or remote calls."""
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

from hsi_cosmic_love import (
    PROGRAM, MARKER, EXPECTED_TABLE, decode, transition, verify,
)

ROOT = Path(__file__).resolve().parents[1]


class CosmicLoveTwoStepTests(unittest.TestCase):
    def test_exact_integer_decoding(self):
        d = decode(PROGRAM)
        self.assertEqual(
            (d["diagonal"], d["code"], d["k"], d["radix"]),
            (10493, 10492, 2, 12),
        )

    def test_transition_table_is_exhaustive(self):
        self.assertEqual(len(decode(PROGRAM)["table"]), 4)
        self.assertEqual(decode(PROGRAM)["table"], EXPECTED_TABLE)
        for q in (0, 1):
            for a in (0, 1):
                self.assertEqual(EXPECTED_TABLE[(q, a)], (1-q, a, 1-2*q))

    def test_all_eight_local_cases(self):
        self.assertEqual(verify()["local_cycles_checked"], 8)
        self.assertEqual(verify()["rules_checked"], 4)

    def test_arbitrary_negative_and_shifted_heads(self):
        r = random.Random(20261013)
        positions = [-1000, -17, -1, 0, 1, 23, 1001]
        for head in positions:
            for q in (0, 1):
                for _ in range(12):
                    tape = {x: 1 for x in range(head-15, head+16)
                            if r.randrange(2)}
                    # Preserve implicit zero cells when comparing tape dictionaries.
                    start = (q, head)
                    once = transition(start, tape, EXPECTED_TABLE)
                    twice = transition(*once, EXPECTED_TABLE)
                    self.assertEqual(twice, (start, tape))

    def test_first_step_is_not_identity(self):
        for q in (0, 1):
            new, _ = transition((q, 0), {0: 1}, EXPECTED_TABLE)
            self.assertNotEqual(new, (q, 0))

    def test_reject_mismatched_program_and_invalid_tapes(self):
        with self.assertRaises(ValueError):
            verify(1829)
        with self.assertRaises(ValueError):
            decode(-1)
        with self.assertRaises(ValueError):
            transition((2, 0), {})
        with self.assertRaises(ValueError):
            transition((0, 0), {0: 2})

    def test_marker_cli(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "hsi_cosmic_love.py")],
            capture_output=True, text=True, timeout=15, check=True,
        )
        self.assertEqual(result.stdout.strip(), MARKER)
        self.assertEqual(result.stderr, "")

    def test_certificate_is_explicit_about_claim_scope(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "hsi_cosmic_love.py"), "--json"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        c = json.loads(result.stdout)
        self.assertEqual(c["finite_validation"], "PASSED")
        self.assertFalse(c["live_trading_authorized"])
        self.assertEqual(c["broker_calls"], 0)
        self.assertIn("not from testing infinitely many tapes", c["limitations"])


if __name__ == "__main__":
    unittest.main()
