"""Synthetic, zero-network tests for the UTC risk-latch fail-closed pretrade gate."""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from hsi_binance_orders import BinanceOrders
from hsi_spot_ledger import replay_day
from hsi_spot_pretrade_gate import (
    PretradeRejected, ensure_schema, enforce_pretrade,
    observe_offline_loss, status, utc_day,
)

DAY = int(datetime(2026, 10, 13, tzinfo=timezone.utc).timestamp() * 1000)
MANIFEST = "a" * 64


def replay(price="9800", *, as_of_ms=DAY + 20000, commission="0"):
    fixture = {
        "utc_day": "2026-10-13",
        "as_of_ms": as_of_ms,
        "observed_at_ms": as_of_ms + 1,
        "opening_lots": [{"quantity": "0.01", "cost_usdt": "100"}],
        "fills": [{
            "trade_id": 1, "time_ms": DAY + 10000, "symbol": "BTCUSDT",
            "side": "SELL", "quantity": "0.01", "price": price,
            "commission": commission, "commission_asset": "USDT",
        }],
    }
    return replay_day(fixture)


class UTCDailyStopReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = Path(self.tmp.name) / "orders.sqlite"
        self.orders = BinanceOrders(self.journal, MANIFEST)

    def assess(self, *, now_ms=DAY + 30000, result=None):
        with self.orders.database() as db:
            return observe_offline_loss(
                db, result if result is not None else replay(),
                now_ms=now_ms,
            )

    def test_missing_broker_reconciliation_always_denies(self):
        with self.orders.database() as db:
            report = status(db, now_ms=DAY + 30000)
            self.assertEqual(report["status"], "UNKNOWN_FAIL_CLOSED")
            self.assertFalse(report["broker_reconciled"])
            self.assertEqual(report["live_order_permission"], "DENIED")
            with self.assertRaisesRegex(PretradeRejected, "RISK_UNKNOWN_BROKER_RECONCILIATION"):
                enforce_pretrade(db, now_ms=DAY + 30000)

    def test_threshold_equal_and_below_latches_for_current_utc_day(self):
        for price in ("9800", "9799"):
            with self.subTest(price=price), tempfile.TemporaryDirectory() as folder:
                db_path = Path(folder) / "journal.sqlite"
                with sqlite3.connect(db_path) as db:
                    ensure_schema(db)
                    report = observe_offline_loss(db, replay(price),
                                                  now_ms=DAY + 30000)
                    self.assertEqual(report["status"], "HALT_DAILY_LOSS_REVIEW_LATCHED")
                    with self.assertRaisesRegex(PretradeRejected, "HALT_DAILY_LOSS"):
                        enforce_pretrade(db, now_ms=DAY + 30000)
                # A process restart must not discard today's stop.
                with sqlite3.connect(db_path) as db:
                    self.assertEqual(status(db, now_ms=DAY + 50000)["status"],
                                     "HALT_DAILY_LOSS_REVIEW_LATCHED")
                    self.assertEqual(status(db, now_ms=DAY + 86400000 + 50000)["status"],
                                     "UNKNOWN_FAIL_CLOSED")
                    with self.assertRaisesRegex(PretradeRejected, "RISK_UNKNOWN_BROKER_RECONCILIATION"):
                        enforce_pretrade(db, now_ms=DAY + 86400000 + 50000)

    def test_near_miss_never_rounds_into_a_stop_or_approval(self):
        near_miss = replay("9800.0000000000000000000000000001")
        self.assertEqual(near_miss["status"], "LOCAL_REPLAY_ONLY")
        self.assertFalse(near_miss["stop_threshold_reached_during_replay"])
        out = self.assess(result=near_miss)
        self.assertEqual(out["status"], "UNKNOWN_FAIL_CLOSED")
        self.assertEqual(out["live_order_permission"], "DENIED")

    def test_recovered_pnl_never_clears_stop_in_same_day(self):
        self.assess()
        improved = self.assess(result=replay("9900"))
        self.assertEqual(improved["status"], "HALT_DAILY_LOSS_REVIEW_LATCHED")
        restarted = BinanceOrders(self.journal, MANIFEST)
        with restarted.database() as db:
            self.assertEqual(status(db, now_ms=DAY + 30000)["status"],
                             "HALT_DAILY_LOSS_REVIEW_LATCHED")
            self.assertEqual(db.execute("SELECT count(*) FROM spot_utc_loss_latch").fetchone()[0], 1)

    def test_stale_forged_and_inconsistent_offline_claims_cannot_greenlight(self):
        cases = [
            ({"status": "BROKER_RECONCILED", **{}}, "RISK_UNKNOWN"),
            (dict(replay(), broker_reconciled=True), "RISK_UNKNOWN"),
            (dict(replay(), live_order_permission="APPROVED"), "RISK_UNKNOWN"),
            (dict(replay(), snapshot_ms=DAY), "RISK_UNKNOWN"),
            (dict(replay(), utc_day="2026-10-12"), "RISK_UNKNOWN"),
            (dict(replay(), stop_threshold_reached_during_replay=False), "RISK_UNKNOWN"),
            (dict(replay(), worst_intraday_running_realized_pnl_usdt="NaN"), "RISK_UNKNOWN"),
        ]
        for row, reason in cases:
            with self.subTest(row=row):
                with self.orders.database() as db:
                    with self.assertRaisesRegex(PretradeRejected, reason):
                        observe_offline_loss(db, row, now_ms=DAY + 70000)
        with self.orders.database() as db:
            self.assertEqual(status(db, now_ms=DAY + 70000)["status"], "UNKNOWN_FAIL_CLOSED")

    def test_tampered_local_table_and_invalid_clock_cannot_authorize(self):
        self.assertEqual(utc_day(DAY + 50000), "2026-10-13")
        with self.assertRaises(PretradeRejected):
            utc_day(True)
        with self.orders.database() as db:
            self.assertEqual(status(db, now_ms=0)["status"], "UNKNOWN_FAIL_CLOSED")
            with self.assertRaisesRegex(PretradeRejected, "RISK_UNKNOWN"):
                enforce_pretrade(db, now_ms=0)
            # SQLite failure is still a rejection, never permissive.
            db.execute("DROP TABLE spot_utc_loss_latch")
            db.execute("CREATE TABLE spot_utc_loss_latch (unexpected TEXT)")
            with self.assertRaisesRegex(PretradeRejected, "RISK_UNKNOWN"):
                enforce_pretrade(db, now_ms=DAY + 30000)

    def test_submit_rejects_even_if_code_release_hook_is_mocked(self):
        """This verifies the integration gate is not just another env toggle."""
        with patch.dict(os.environ, {
            "LIVE_ARMED": "1", "LIVE_DRY_RUN": "0", "HSI_ORDER_KILL": "0",
            "HSI_ORDER_JOURNAL_DURABLE": "1", "HSI_ORDER_CONTROL_TOKEN": "mock",
            "BINANCE_API_KEY": "offline", "BINANCE_API_SECRET": "offline",
            "HSI_ORDER_SYMBOL_ALLOWLIST": "BTCUSDT",
            "MAX_QUOTE_PER_ORDER": "50"
        }), patch("os.path.ismount", return_value=True):
            ticket = self.orders.prepare({
                "symbol": "BTCUSDT", "side": "BUY", "price": "10000",
                "quantity": "0.001", "notes_manifest_sha256": MANIFEST,
            })
            with patch("hsi_binance_orders.assert_live_release"), patch.object(
                    self.orders, "broker") as broker:
                with self.assertRaisesRegex(PretradeRejected, "RISK_UNKNOWN"):
                    self.orders.submit({**ticket, "confirm_live_order": True})
                broker.assert_not_called()
            self.assertEqual(self.orders.status()["daily_realized_pnl_status"],
                             "UNKNOWN_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
