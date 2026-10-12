"""All-synthetic risk ledger tests: no credentials, broker API, or orders."""
from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path
import unittest

from hsi_spot_ledger import replay_day, review_file, MAX_INPUT_BYTES

DAY = int(datetime(2026, 10, 13, tzinfo=timezone.utc).timestamp() * 1000)


def trade(trade_id, offset_ms, side, quantity, price, fee="0", asset="USDT"):
    return {
        "trade_id": trade_id, "time_ms": DAY + offset_ms,
        "symbol": "BTCUSDT", "side": side, "quantity": quantity,
        "price": price, "commission": fee, "commission_asset": asset,
    }


def fixture(fills=None, lots=None):
    return {
        "utc_day": "2026-10-13",
        "as_of_ms": DAY + 90000, "observed_at_ms": DAY + 90001,
        "opening_lots": [{"quantity": "0.01", "cost_usdt": "100"}]
            if lots is None else lots,
        "fills": [] if fills is None else fills,
    }


class TestSpotFifoReplay(unittest.TestCase):
    def test_loss_crosses_threshold_even_if_later_recovered(self):
        f = [
            trade(1, 1000, "SELL", "0.005", "9800", "0.2"),
            trade(2, 2000, "SELL", "0.005", "9600", "0.1"),
            trade(3, 3000, "BUY", "0.01", "9000"),
            trade(4, 4000, "SELL", "0.01", "9900"),
        ]
        r = replay_day(fixture(f))
        self.assertEqual(r["status"], "LOCAL_REPLAY_ONLY")
        self.assertEqual(r["candidate_daily_realized_pnl_usdt"], "5.7")
        self.assertEqual(r["worst_intraday_running_realized_pnl_usdt"], "-3.3")
        self.assertTrue(r["stop_threshold_reached_during_replay"])
        self.assertFalse(r["broker_reconciled"])
        self.assertEqual(r["live_order_permission"], "DENIED")
        self.assertEqual(r["broker_requests"], 0)

    def test_fractional_loss_just_below_stop_is_not_rounded_to_two(self):
        """Do not report -2 when the exact candidate loss is still above -2."""
        record = fixture([
            trade(1, 1000, "SELL", "0.01",
                  "9800.0000000000000000000000000001")
        ])
        result = replay_day(record)
        self.assertEqual(result["status"], "LOCAL_REPLAY_ONLY")
        self.assertEqual(
            result["candidate_daily_realized_pnl_usdt"],
            "-1.999999999999999999999999999999")
        self.assertEqual(
            result["worst_intraday_running_realized_pnl_usdt"],
            "-1.999999999999999999999999999999")
        self.assertFalse(result["stop_threshold_reached_during_replay"])
        self.assertEqual(result["live_order_permission"], "DENIED")

    def test_exact_two_dollar_stop_still_triggers(self):
        record = fixture([trade(1, 1000, "SELL", "0.01", "9800")])
        result = replay_day(record)
        self.assertEqual(result["candidate_daily_realized_pnl_usdt"], "-2")
        self.assertTrue(result["stop_threshold_reached_during_replay"])

    def test_fee_in_btc_reduces_buy_quantity(self):
        r = replay_day(fixture([
            trade(1, 1000, "BUY", "0.01", "10000", "0.0001", "BTC"),
            trade(2, 2000, "SELL", "0.0099", "9900", "0.1", "USDT"),
        ], lots=[]))
        self.assertEqual(r["status"], "LOCAL_REPLAY_ONLY")
        self.assertEqual(r["candidate_daily_realized_pnl_usdt"], "-2.09")
        self.assertTrue(r["stop_threshold_reached_during_replay"])

    def test_sell_fee_in_btc_uses_extra_cost_basis(self):
        r = replay_day(fixture([trade(1, 1000, "SELL", "0.009", "10000", "0.001", "BTC")]))
        self.assertEqual(r["status"], "LOCAL_REPLAY_ONLY")
        self.assertEqual(r["candidate_daily_realized_pnl_usdt"], "-10")

    def test_prev_day_sale_not_in_today_pnl(self):
        r = replay_day(fixture([
            trade(1, -1000, "SELL", "0.01", "9000"),
            trade(2, 1000, "SELL", "0.01", "9900"),
        ], lots=[{"quantity": "0.02", "cost_usdt": "200"}]))
        self.assertEqual(r["candidate_daily_realized_pnl_usdt"], "-1")
        self.assertFalse(r["stop_threshold_reached_during_replay"])

    def test_unpriced_fees_missing_history_and_duplicates_fail_closed(self):
        cases = [
            fixture([trade(1, 1000, "SELL", "0.01", "9900", "0.1", "BNB")]),
            fixture([trade(1, 1000, "SELL", "0.02", "9900")]),
            fixture([trade(1, 1000, "SELL", "0.005", "9900"),
                     trade(1, 2000, "SELL", "0.005", "9900")]),
            fixture([trade(2, 2000, "BUY", "0.01", "9900"),
                     trade(1, 1000, "SELL", "0.005", "9900")]),
            fixture([trade(1, 1000, "SELL", "NaN", "9900")]),
        ]
        for case in cases:
            with self.subTest(case=case):
                result = replay_day(case)
                self.assertEqual(result["status"], "UNKNOWN_FAIL_CLOSED")
                self.assertEqual(result["live_order_permission"], "DENIED")

    def test_stale_record_and_too_many_fills_fail_closed(self):
        row = fixture()
        row["observed_at_ms"] = row["as_of_ms"] + 60001
        self.assertEqual(replay_day(row)["reason"], "STALE_OBSERVATION")
        row = fixture()
        row["fills"] = [trade(i + 1, i, "BUY", "0.001", "100") for i in range(2001)]
        self.assertEqual(replay_day(row)["reason"], "BOUNDED_INPUT_EXCEEDED")

    def test_reproducible_hash_and_local_file(self):
        row = fixture([trade(1, 1000, "BUY", "0.01", "10000")])
        self.assertEqual(replay_day(row)["replay_sha256"], replay_day(row)["replay_sha256"])
        with tempfile.TemporaryDirectory() as path:
            file = Path(path) / "fixture.json"
            file.write_text(json.dumps(row), encoding="utf-8")
            self.assertEqual(review_file(file)["status"], "LOCAL_REPLAY_ONLY")
            self.assertEqual(review_file(Path(path) / "missing.json")["status"], "UNKNOWN_FAIL_CLOSED")
            file.write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
            self.assertEqual(review_file(file)["reason"], "FILE_MISSING_OR_TOO_LARGE")

if __name__ == "__main__":
    unittest.main()
