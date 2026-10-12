"""Offline crosscheck tests: mock signed GETs only, no Binance network."""
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

from hsi_binance_readonly_audit import read_only_audit
from hsi_spot_ledger import replay_day
from hsi_spot_reconcile import crosscheck
from hsi_spot_trade_digest import normalized_trade, digest_trades

DAY = int(datetime(2026, 10, 13, tzinfo=timezone.utc).timestamp() * 1000)
NOW = DAY + 123000


def make_pair(*, no_trades=False):
    raw = [] if no_trades else [
        {"symbol": "BTCUSDT", "id": 501, "orderId": 44,
         "price": "10000.00", "qty": "0.00500", "quoteQty": "50.000",
         "commission": "0.0000050", "commissionAsset": "BTC",
         "time": DAY + 10000, "isBuyer": True},
        {"symbol": "BTCUSDT", "id": 502, "orderId": 45,
         "price": "9900", "qty": "0.005", "quoteQty": "49.50",
         "commission": "0.1", "commissionAsset": "USDT",
         "time": DAY + 20000, "isBuyer": False},
    ]
    replies = [
        {"accountType": "SPOT", "canTrade": True,
         "balances": [{"asset": "BTC", "free": "0.01", "locked": "0"}]},
        {"enableSpotAndMarginTrading": False}, [], raw
    ]
    broker = Mock(side_effect=replies)
    snapshot = read_only_audit(broker, enabled=True, now_ms=NOW)
    assert snapshot["status"] == "READ_ONLY_SNAPSHOT_UNVERIFIED", snapshot
    assert all(call.args[2:] == ("GET", True) for call in broker.call_args_list)
    fields = [] if no_trades else [
        {"symbol": "BTCUSDT", "trade_id": 501, "time_ms": DAY + 10000,
         "side": "BUY", "price": "10000", "quantity": "0.005",
         "commission": "0.000005", "commission_asset": "BTC"},
        {"symbol": "BTCUSDT", "trade_id": 502, "time_ms": DAY + 20000,
         "side": "SELL", "price": "9900.000", "quantity": "0.005000",
         "commission": "0.10", "commission_asset": "USDT"},
    ]
    replay = replay_day({"utc_day": "2026-10-13", "as_of_ms": NOW,
                         "observed_at_ms": NOW + 1,
                         "opening_lots": [{"quantity": "0.01", "cost_usdt": "100"}],
                         "fills": fields})
    assert replay["status"] == "LOCAL_REPLAY_ONLY", replay
    return snapshot, replay


class SpotBoundedCrosscheckTests(unittest.TestCase):
    def test_matching_summaries_never_grant_execution(self):
        snapshot, replay = make_pair()
        result = crosscheck(snapshot, replay)
        self.assertEqual(result["status"], "BOUNDED_DIGEST_MATCH_ONLY_NOT_RECONCILED")
        self.assertTrue(result["bounded_window_digest_matches"])
        self.assertFalse(result["broker_reconciled"])
        self.assertFalse(result["daily_pnl_verified"])
        self.assertFalse(result["exchange_origin_authenticated_by_this_file"])
        self.assertEqual(result["live_order_permission"], "DENIED")
        self.assertEqual(result["real_order_submissions"], 0)
        self.assertEqual(result["matching_fill_count"], 2)

    def test_canonical_numeric_forms_match(self):
        self.assertEqual(digest_trades([
            normalized_trade(1, NOW, "BUY", "0.01", "10000.000", "0", "BTC")
        ]), digest_trades([
            normalized_trade(1, NOW, "BUY", "0.0100", "10000", "0.000", "BTC")
        ]))

    def test_full_decimal_precision_never_rounds_hashes_together(self):
        left = "0.123456789012345678901234567891"
        right = "0.123456789012345678901234567892"
        self.assertNotEqual(
            digest_trades([normalized_trade(1, NOW, "BUY", left, "10000", "0", "BTC")]),
            digest_trades([normalized_trade(1, NOW, "BUY", right, "10000", "0", "BTC")]),
        )

    def test_empty_trades_match_but_not_authorize(self):
        snapshot, replay = make_pair(no_trades=True)
        result = crosscheck(snapshot, replay)
        self.assertTrue(result["bounded_window_digest_matches"])
        self.assertEqual(result["live_order_permission"], "DENIED")
        self.assertFalse(result["opening_cost_basis_verified"])

    def test_disagreement_staleness_and_anomalies_fail_closed(self):
        for field, value, reason, group in [
            ("trade_fingerprint_sha256", "f" * 64, "TRADE_FINGERPRINT_MISMATCH", "snapshot"),
            ("utc_day", "2026-10-12", "MISMATCHED_SYMBOL_OR_UTC_DAY", "snapshot"),
            ("trade_fingerprint_scheme", "UNKNOWN", "INCOMPATIBLE_FINGERPRINT_SCHEME", "replay"),
            ("snapshot_ms", NOW + 1, "MISMATCHED_SNAPSHOT_TIME", "replay"),
            ("signed_reads", 0, "INCONSISTENT_READ_ONLY_ATTESTATIONS", "snapshot"),
            ("api_spot_trading_enabled", True, "SPOT_TRADE_PERMISSION_MUST_REMAIN_DISABLED", "snapshot"),
            ("open_orders_present", True, "OPEN_ORDERS_NOT_RECONCILED", "snapshot"),
            ("non_usdt_btc_fee_present", True, "UNPRICED_COMMISSION_ASSETS", "snapshot"),
            ("all_fills_in_requested_utc_day", False, "INCONSISTENT_DAILY_FILL_COVERAGE", "replay"),
            ("trade_count", 3, "INCONSISTENT_DAILY_FILL_COVERAGE", "snapshot"),
            ("status", "UNKNOWN_FAIL_CLOSED", "UNRESOLVED_EVIDENCE", "snapshot"),
        ]:
            with self.subTest(field=field, group=group):
                a, b = make_pair()
                if group == "snapshot":
                    a[field] = value
                else:
                    b[field] = value
                result = crosscheck(a, b)
                self.assertEqual(result["status"], "UNKNOWN_FAIL_CLOSED")
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["live_order_permission"], "DENIED")

    def test_never_treat_operator_summaries_as_crypto_attestation(self):
        # Both sources could be forged by a local caller, so a match never
        # upgrades independent trust or completeness claims.
        snapshot, replay = make_pair()
        bad = copy.deepcopy(snapshot)
        bad["broker_reconciled"] = True
        self.assertEqual(crosscheck(bad, replay)["reason"], "INCONSISTENT_READ_ONLY_ATTESTATIONS")
        bad = copy.deepcopy(replay)
        bad["live_order_permission"] = "APPROVED"
        self.assertEqual(crosscheck(snapshot, bad)["reason"], "INCONSISTENT_READ_ONLY_ATTESTATIONS")

    def test_cli_local_json_files_only(self):
        snapshot, replay = make_pair()
        with tempfile.TemporaryDirectory() as d:
            first, second = Path(d) / "snapshot.json", Path(d) / "replay.json"
            first.write_text(json.dumps(snapshot), encoding="utf-8")
            second.write_text(json.dumps(replay), encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "hsi_spot_reconcile",
                                   "--snapshot", str(first),
                                   "--ledger-report", str(second)],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"],
                             "BOUNDED_DIGEST_MATCH_ONLY_NOT_RECONCILED")


if __name__ == "__main__":
    unittest.main()
