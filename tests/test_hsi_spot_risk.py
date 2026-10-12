"""Offline-only strict Binance Spot risk tests; no real network."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from hsi_spot_risk import (
    MAX_DAILY_REALIZED_LOSS_USDT, MAX_ORDER_QUOTE_USDT, SYMBOL,
    enforce_order, restricted_order_limit, evaluate_daily_loss,
    assert_live_release, review_report,
)


class SpotRiskTests(unittest.TestCase):
    def test_policy_constants_and_manifest(self):
        policy=json.loads((Path(__file__).resolve().parents[1] / "trader42_spot_risk.json").read_text())
        self.assertEqual(SYMBOL,"BTCUSDT")
        self.assertEqual(str(MAX_ORDER_QUOTE_USDT),"50")
        self.assertEqual(str(MAX_DAILY_REALIZED_LOSS_USDT),"2")
        self.assertEqual(policy["allowed_symbols"],["BTCUSDT"])
        self.assertEqual(policy["max_quote_per_order_usdt"],"50")
        self.assertEqual(policy["daily_realized_loss_stop_usdt"],"2")
        self.assertFalse(policy["auto_update"]["automatic_strategy_promotion"])
        self.assertEqual(policy["live_trading"],"BLOCKED_PENDING_SEPARATE_APPROVAL")

    def test_notional_and_symbol_fail_closed(self):
        self.assertEqual(str(enforce_order("BTCUSDT","1000","0.05","1000")),"50.00")
        for sym,pr,qt in [("ETHUSDT","1000","0.01"),("BTCUSDT","1000","0.05001")]:
            with self.assertRaises(ValueError):
                enforce_order(sym,pr,qt,"1000")
        with self.assertRaises(ValueError):
            enforce_order("BTCUSDT","1000","0.02","10")
        self.assertEqual(restricted_order_limit("10000"),MAX_ORDER_QUOTE_USDT)
        self.assertEqual(str(restricted_order_limit("10")),"10")

    def test_daily_stop_is_diagnostic_not_execution_permission(self):
        self.assertEqual(evaluate_daily_loss()["status"],"UNKNOWN_FAIL_CLOSED")
        self.assertEqual(evaluate_daily_loss("-2",True,True)["status"],"HALT_DAILY_LOSS")
        self.assertEqual(evaluate_daily_loss("-2.01",True,True)["status"],"HALT_DAILY_LOSS")
        self.assertEqual(evaluate_daily_loss("-1.9",True,True)["status"],"BELOW_STOP_THRESHOLD_REVIEW_ONLY")
        self.assertEqual(evaluate_daily_loss("-3",False,True)["status"],"UNKNOWN_FAIL_CLOSED")
        self.assertEqual(evaluate_daily_loss("NaN",True,True)["status"],"UNKNOWN_FAIL_CLOSED")


    def test_review_report_never_promotes_local_fifo_to_live(self):
        self.assertEqual(review_report()["fifo_ledger"]["status"],"UNKNOWN_FAIL_CLOSED")
        with tempfile.TemporaryDirectory() as d:
            payload = {"utc_day":"2026-10-13",
                       "as_of_ms":1,
                       "observed_at_ms":2,
                       "opening_lots":[], "fills":[]}
            # Use a calculated UTC epoch rather than depend on the wall clock.
            from datetime import datetime, timezone
            midnight=int(datetime(2026,10,13,tzinfo=timezone.utc).timestamp()*1000)
            payload["as_of_ms"]=midnight+90000
            payload["observed_at_ms"]=midnight+90001
            p=Path(d)/"ledger.json"
            p.write_text(json.dumps(payload))
            report=review_report(p)
            self.assertEqual(report["fifo_ledger"]["status"],"LOCAL_REPLAY_ONLY")
            self.assertFalse(report["fifo_ledger"]["broker_reconciled"])
            self.assertEqual(report["fifo_ledger"]["live_order_permission"],"DENIED")
            self.assertEqual(report["live_release"],"BLOCKED_SEPARATE_APPROVAL_REQUIRED")

    def test_cli_readonly_report_is_available_without_broker(self):
        """No-network CLI smoke test catches incorrect args variable handling."""
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.json"
            from datetime import datetime, timezone
            midnight = int(datetime(2026, 10, 13, tzinfo=timezone.utc).timestamp() * 1000)
            fixture.write_text(json.dumps({
                "utc_day": "2026-10-13",
                "as_of_ms": midnight + 90000,
                "observed_at_ms": midnight + 90001,
                "opening_lots": [],
                "fills": [],
            }), encoding="utf-8")
            proc = subprocess.run([
                sys.executable, "-m", "hsi_spot_risk",
                "--ledger-file", str(fixture)
            ], capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["fifo_ledger"]["status"], "LOCAL_REPLAY_ONLY")
            self.assertEqual(payload["fifo_ledger"]["live_order_permission"], "DENIED")
            self.assertEqual(payload["live_release"], "BLOCKED_SEPARATE_APPROVAL_REQUIRED")

    def test_no_env_can_activate_live_release(self):
        with patch.dict(os.environ,{"LIVE_ARMED":"1","LIVE_DRY_RUN":"0","HSI_ORDER_KILL":"0","MAX_QUOTE_PER_ORDER":"999999"}):
            with self.assertRaisesRegex(ValueError,"LIVE_BLOCKED"):
                assert_live_release()
        self.assertEqual(review_report()["live_release"],"BLOCKED_SEPARATE_APPROVAL_REQUIRED")
        self.assertIn("cannot guarantee",review_report()["no_guarantee"])

if __name__=="__main__":
    unittest.main()
