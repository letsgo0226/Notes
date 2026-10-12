"""CLSDP formal closure standard: claims never acquire trading privileges."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "clsdp"))
from closure_standard import (  # noqa: E402
    PROTOCOL, PROGRAM, REQUIRED, ClosureInputError, evaluate, inspect_file,
)

NOW = datetime(2026, 10, 13, 3, 0, tzinfo=timezone.utc)


def package(status="PASS", observation=NOW):
    utc = observation.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "protocol": PROTOCOL, "program": PROGRAM,
        "policy": {
            "symbol": "BTCUSDT", "max_order_quote_usdt": "50",
            "utc_daily_realized_loss_stop_usdt": "2",
            "real_trading_enabled": False,
        },
        "assertions": {
            gate: {
                "status": status,
                "issuer_class": kind,
                "observation_utc": utc,
                "evidence_sha256": "a" * 64,
            }
            for gate, kind in REQUIRED.items()
        },
    }


class CLSDPClosureTests(unittest.TestCase):
    def test_all_claimed_pass_still_does_not_authorize_anything(self):
        r = evaluate(package(), as_of=NOW)
        self.assertEqual(r["claimed_pass_count"], len(REQUIRED))
        self.assertEqual(r["status"], "SELF_ASSERTED_COMPLETE_NEEDS_INDEPENDENT_REVIEW")
        self.assertFalse(r["source_authenticated_by_this_program"])
        self.assertFalse(r["broker_reconciled_by_this_program"])
        self.assertFalse(r["production_ready_by_this_program"])
        self.assertFalse(r["can_modify_deployment"])
        self.assertFalse(r["can_change_binance_permissions"])
        self.assertFalse(r["can_grant_order_permission"])
        self.assertEqual(r["live_order_permission"], "DENIED")
        self.assertEqual(r["broker_calls"], 0)
        self.assertEqual(r["real_orders"], 0)

    def test_missing_or_unknown_gate_rejects_incomplete_proof(self):
        for state in ("FAIL", "UNKNOWN"):
            with self.subTest(state=state):
                e = package()
                e["assertions"]["historical_cost_basis_and_transfers"]["status"] = state
                r = evaluate(e, as_of=NOW)
                self.assertEqual(r["status"], "REVIEW_BLOCKED")
                self.assertEqual(r["claimed_pass_count"], len(REQUIRED) - 1)
                self.assertEqual(r["live_order_permission"], "DENIED")
        e = package()
        del e["assertions"]["operator_release_approval"]
        with self.assertRaisesRegex(ClosureInputError, "MISSING_OR_UNKNOWN_GATES"):
            evaluate(e, as_of=NOW)

    def test_rejects_policy_expansion_and_auto_release(self):
        for k, v in [
            ("symbol", "ETHUSDT"),
            ("max_order_quote_usdt", "500"),
            ("utc_daily_realized_loss_stop_usdt", "20"),
            ("real_trading_enabled", True),
        ]:
            with self.subTest(k=k):
                e = package()
                e["policy"][k] = v
                with self.assertRaisesRegex(ClosureInputError, "RISK_POLICY"):
                    evaluate(e, as_of=NOW)

    def test_timestamps_must_be_fresh_nonfuture_and_utc(self):
        for offset in (-90000, 3600):
            e = package(observation=NOW + timedelta(seconds=offset))
            r = evaluate(e, as_of=NOW)
            self.assertEqual(r["claimed_pass_count"], 0)
            self.assertEqual(r["status"], "REVIEW_BLOCKED")
        e = package()
        e["assertions"]["market_data_integrity"]["observation_utc"] = "2026-10-13 03:00"
        with self.assertRaisesRegex(ClosureInputError, "INVALID_UTC"):
            evaluate(e, as_of=NOW)

    def test_false_issuer_or_digest_is_invalid(self):
        e = package()
        e["assertions"]["independent_not_a_gate"] = e["assertions"].pop("market_data_integrity")
        with self.assertRaisesRegex(ClosureInputError, "MISSING_OR_UNKNOWN_GATES"):
            evaluate(e, as_of=NOW)
        e = package()
        e["assertions"]["market_data_integrity"]["issuer_class"] = "self"
        with self.assertRaisesRegex(ClosureInputError, "INVALID_ATTESTATION_CLAIM"):
            evaluate(e, as_of=NOW)
        e = package()
        e["assertions"]["market_data_integrity"]["evidence_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ClosureInputError, "INVALID_ATTESTATION_CLAIM"):
            evaluate(e, as_of=NOW)

    def test_sha256_is_integrity_label_not_issuer_authentication(self):
        e = package()
        r1 = evaluate(e, as_of=NOW)
        e2 = deepcopy(e)
        e2["assertions"]["market_data_integrity"]["evidence_sha256"] = "b" * 64
        r2 = evaluate(e2, as_of=NOW)
        self.assertNotEqual(r1["evidence_sha256"], r2["evidence_sha256"])
        for r in (r1, r2):
            self.assertFalse(r["source_authenticated_by_this_program"])
            self.assertEqual(r["live_order_permission"], "DENIED")

    def test_local_cli_returns_nonzero_on_unknown_and_never_releases(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "evidence.json"
            path.write_text(json.dumps(package()), encoding="utf-8")
            r = inspect_file(path, as_of=NOW)
            self.assertEqual(r["live_order_permission"], "DENIED")
            cmd = [sys.executable, str(ROOT / "research/clsdp/closure_standard.py"),
                   "--input", str(path), "--as-of", "2026-10-13T03:00:00Z"]
            ok = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            self.assertEqual(ok.returncode, 1, ok.stderr)
            self.assertEqual(json.loads(ok.stdout)["live_order_permission"], "DENIED")
            e = package()
            e["assertions"]["operator_release_approval"]["status"] = "UNKNOWN"
            path.write_text(json.dumps(e), encoding="utf-8")
            blocked = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            self.assertEqual(blocked.returncode, 1, blocked.stderr)
            self.assertEqual(json.loads(blocked.stdout)["status"], "REVIEW_BLOCKED")
            path.write_text("{}", encoding="utf-8")
            invalid = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            self.assertEqual(invalid.returncode, 2, invalid.stderr)

    def test_input_errors_fail_closed(self):
        for value in (None, [], {}, {"protocol": PROTOCOL}):
            with self.subTest(value=value), self.assertRaises(ClosureInputError):
                evaluate(value, as_of=NOW)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ClosureInputError):
                inspect_file(Path(d) / "missing", as_of=NOW)


if __name__ == "__main__":
    unittest.main()
