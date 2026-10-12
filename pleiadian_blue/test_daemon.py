"""Regression tests for finite and safe 1-second heartbeat."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from pleiadian_blue import daemon


class TestDaemon(unittest.TestCase):
    def setUp(self):
        daemon.STOP = False
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_finite_feedback_and_missing_is_unknown(self):
        self.assertEqual(daemon.load_source(self.root / "missing.json")[1],
                         "UNKNOWN_NO_SOURCE")
        self.assertAlmostEqual(daemon.dirichlet([1]).real, 1)
        (self.root / "observation.json").write_text(
            json.dumps({"review": [{"residual": 1.5}, {"residual": 0.0}]}))
        vals, status, sha = daemon.load_source(self.root / "observation.json")
        self.assertEqual(status, "LOCAL_EVIDENCE_ONLY")
        self.assertEqual(vals, [1.5, 0.0])
        self.assertEqual(len(sha), 64)

    def test_finite_rejects_unbounded_input(self):
        (self.root / "bad.json").write_text(
            json.dumps({"review": [{"residual": -1}]}))
        self.assertEqual(daemon.load_source(self.root / "bad.json")[1],
                         "UNKNOWN_INVALID_SOURCE")

    def test_resumable_sqlite(self):
        db = self.root / "state.sqlite3"
        status = self.root / "status.json"
        daemon.serve(db, status, None, 0.01, 2)
        daemon.serve(db, status, None, 0.01, 3)
        result = json.loads(status.read_text())
        self.assertEqual(result["ticks"], 5)
        self.assertEqual(result["orders"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["source_status"], "UNKNOWN_NO_SOURCE")
        with sqlite3.connect(db) as c:
            self.assertEqual(c.execute(
                "SELECT ticks FROM heartbeat WHERE id=1").fetchone()[0], 5)


if __name__ == "__main__":
    unittest.main()
