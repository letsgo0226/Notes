"""Finite, offline COSMIC_LOVE heartbeat unit tests (no network or broker)."""
import json
from pathlib import Path
import tempfile
import unittest

from hsi_cosmic_love import transition
from hsi_cosmic_love_heartbeat import (
    MARKER, PROTOCOL, _snapshot, _write, check_heartbeat, run_heartbeat,
)


class CosmicLoveHeartbeatTests(unittest.TestCase):
    def test_five_cycles_return_to_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            out = run_heartbeat(path, cycles=5, interval=0, checkpoint_every=2,
                                sleeper=lambda _: None)
            self.assertEqual(out["protocol"], PROTOCOL)
            self.assertEqual(out["status"], "STOPPED")
            self.assertEqual(out["cycles_completed"], 5)
            self.assertEqual(out["transitions_completed"], 10)
            self.assertEqual((out["q"], out["head"], out["tape"]), (0, 0, {}))
            self.assertEqual(out["broker_calls"], 0)
            self.assertFalse(out["live_trading_authorized"])
            self.assertFalse(check_heartbeat(path)["healthy"])

    def test_checkpoint_corruption_is_not_automatically_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            run_heartbeat(path, cycles=2, interval=0, sleeper=lambda _: None)
            record = json.loads(path.read_text(encoding="utf-8"))
            record["cycles_completed"] = 1000
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(check_heartbeat(path)["reason"],
                             "INVALID_OR_MISSING_CHECKPOINT")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run_heartbeat(path, cycles=1, interval=0, resume=True)

    def test_explicit_resume_of_last_committed_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            run_heartbeat(path, cycles=3, interval=0, sleeper=lambda _: None)
            with self.assertRaisesRegex(ValueError, "checkpoint exists"):
                run_heartbeat(path, cycles=1, interval=0, resume=False)
            out = run_heartbeat(path, cycles=4, interval=0, resume=True,
                                sleeper=lambda _: None)
            self.assertEqual(out["cycles_completed"], 7)
            self.assertEqual(out["transitions_completed"], 14)

    def test_single_transient_fault_can_recover(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            attempted = {"calls": 0}

            def fault_once(*args):
                attempted["calls"] += 1
                if attempted["calls"] == 1:
                    raise RuntimeError("transient fault")
                return transition(*args)

            out = run_heartbeat(path, cycles=3, interval=0, max_restarts=2,
                                stepper=fault_once, sleeper=lambda _: None)
            self.assertEqual(out["status"], "STOPPED")
            self.assertEqual(out["cycles_completed"], 3)
            self.assertEqual(out["transitions_completed"], 6)
            self.assertEqual(out["recovery_attempts"], 1)

    def test_persistent_fault_fails_closed_after_bounded_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"

            def fail(*args):
                raise RuntimeError("persistent fault")

            out = run_heartbeat(path, cycles=5, interval=0, max_restarts=2,
                                stepper=fail, sleeper=lambda _: None)
            self.assertEqual(out["status"], "ERROR")
            self.assertEqual(out["cycles_completed"], 0)
            self.assertEqual(out["recovery_attempts"], 3)
            self.assertFalse(check_heartbeat(path)["healthy"])
            with self.assertRaisesRegex(ValueError, "ERROR checkpoint"):
                run_heartbeat(path, cycles=1, interval=0, resume=True)

    def test_stop_file_controls_unbounded_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            stop = Path(tmp) / "STOP"
            count = {"sleeps": 0}

            def sleeper(_):
                count["sleeps"] += 1
                if count["sleeps"] == 7:
                    stop.touch()

            out = run_heartbeat(path, forever=True, interval=0,
                                stop_file=stop, sleeper=sleeper)
            self.assertEqual(out["status"], "STOPPED")
            self.assertEqual(out["cycles_completed"], 4)
            self.assertEqual(out["transitions_completed"], 8)

    def test_check_only_proves_local_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            _write(path, _snapshot(2, 0, "RUNNING", clock=lambda: 1000))
            report = check_heartbeat(path, clock=lambda: 1001)
            self.assertTrue(report["healthy"])
            self.assertEqual(report["reason"],
                             "FRESH_HEARTBEAT_ONLY_NOT_PROCESS_PROOF")
            self.assertEqual(check_heartbeat(path, clock=lambda: 1020)["reason"],
                             "STALE_OR_FUTURE_CHECKPOINT")
            self.assertFalse(check_heartbeat(path, clock=lambda: 900)["healthy"])

    def test_missing_checkpoint_and_invalid_options_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            self.assertEqual(check_heartbeat(path)["reason"],
                             "INVALID_OR_MISSING_CHECKPOINT")
            with self.assertRaises(ValueError):
                run_heartbeat(path, cycles=-1)
            with self.assertRaises(ValueError):
                run_heartbeat(path, interval=-0.1)

    def test_independent_stop_callback_interrupts_at_cycle_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            checks = {"n": 0}

            def stop():
                checks["n"] += 1
                return checks["n"] > 4

            out = run_heartbeat(path, forever=True, interval=0,
                                stop_requested=stop, sleeper=lambda _: None)
            self.assertEqual(out["cycles_completed"], 4)
            self.assertEqual(out["status"], "STOPPED")


if __name__ == "__main__":
    unittest.main()
