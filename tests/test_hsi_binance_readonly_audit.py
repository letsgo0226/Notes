"""Synthetic signed-GET-only Binance snapshot contract; never contacts an exchange."""
from datetime import datetime, timezone
from unittest.mock import Mock
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hsi_binance_readonly_audit import read_only_audit
from hsi_binance_orders import BinanceOrders

NOW = int(datetime(2026, 10, 13, 14, tzinfo=timezone.utc).timestamp() * 1000)


def response():
    return [
        {"accountType": "SPOT", "canTrade": True,
         "uid": 12345678, "balances": [
            {"asset": "BTC", "free": "0.013", "locked": "0"},
            {"asset": "USDT", "free": "999.99", "locked": "0"}]},
        {"enableSpotAndMarginTrading": False,
         "enableWithdrawals": False, "enableReading": True},
        [],
        [
            {"symbol": "BTCUSDT", "id": 101, "orderId": 72,
             "price": "10000.00", "qty": "0.005", "quoteQty": "50.00",
             "commission": "0.000005", "commissionAsset": "BTC",
             "time": NOW - 120000, "isBuyer": True},
            {"symbol": "BTCUSDT", "id": 102, "orderId": 73,
             "price": "9990.00", "qty": "0.005", "quoteQty": "49.95",
             "commission": "0.02", "commissionAsset": "USDT",
             "time": NOW - 60000, "isBuyer": False}
        ],
    ]


def mocked_broker(parts=None):
    return Mock(side_effect=list(parts or response()))


class BinanceSignedReadAuditTests(unittest.TestCase):
    def test_never_reads_without_explicit_enable(self):
        broker = Mock(side_effect=AssertionError("must never read"))
        result = read_only_audit(broker, enabled=False, now_ms=NOW)
        self.assertEqual(result["status"], "UNKNOWN_FAIL_CLOSED")
        self.assertEqual(result["signed_reads"], 0)
        self.assertEqual(result["live_order_permission"], "DENIED")
        broker.assert_not_called()

    def test_four_signed_gets_only_sanitized_summary(self):
        broker = mocked_broker()
        outcome = read_only_audit(broker, enabled=True, now_ms=NOW)
        self.assertEqual(outcome["status"], "READ_ONLY_SNAPSHOT_UNVERIFIED")
        self.assertEqual(outcome["signed_reads"], 4)
        self.assertFalse(outcome["api_spot_trading_enabled"])
        self.assertEqual(outcome["trade_count"], 2)
        self.assertEqual(outcome["buy_fill_count"], 1)
        self.assertEqual(outcome["sell_fill_count"], 1)
        self.assertTrue(outcome["btc_inventory_present"])
        self.assertFalse(outcome["daily_pnl_verified"])
        self.assertFalse(outcome["broker_reconciled"])
        self.assertEqual(outcome["live_order_permission"], "DENIED")
        self.assertEqual(outcome["real_order_submissions"], 0)
        requests = broker.call_args_list
        self.assertEqual([args.args[0] for args in requests],
            ["/api/v3/account", "/sapi/v1/account/apiRestrictions",
             "/api/v3/openOrders", "/api/v3/myTrades"])
        self.assertTrue(all(args.args[2:] == ("GET", True) for args in requests))
        self.assertEqual(requests[3].args[1]["symbol"], "BTCUSDT")
        self.assertEqual(requests[3].args[1]["limit"], 1000)
        self.assertIn("startTime", requests[3].args[1])
        public = json.dumps(outcome)
        for secret in ["12345678", "999.99", "0.013", "0.000005"]:
            self.assertNotIn(secret, public)

    def test_api_key_trading_enabled_cannot_activate_real_orders(self):
        parts = response()
        parts[1]["enableSpotAndMarginTrading"] = True
        broker = mocked_broker(parts)
        report = read_only_audit(broker, enabled=True, now_ms=NOW)
        self.assertTrue(report["api_spot_trading_enabled"])
        self.assertEqual(report["live_order_permission"], "DENIED")

    def test_unknown_fee_open_orders_are_flagged(self):
        parts = response()
        parts[2] = [{"symbol": "BTCUSDT", "orderId": 777, "status": "NEW"}]
        parts[3][1]["commissionAsset"] = "BNB"
        broker = mocked_broker(parts)
        report = read_only_audit(broker, enabled=True, now_ms=NOW)
        self.assertTrue(report["open_orders_present"])
        self.assertTrue(report["non_usdt_btc_fee_present"])
        self.assertEqual(report["daily_pnl_verified"], False)

    def test_unbounded_missing_duplicate_and_bad_quote_fail_closed(self):
        generators = []
        base = response()
        full = response()
        full[3] = [dict(base[3][0], id=i + 100, time=NOW-120000+i)
                   for i in range(1000)]
        generators.append((full, "POSSIBLY_TRUNCATED_HISTORY"))
        bad = response()
        bad[3].append(dict(bad[3][-1]))
        generators.append((bad, "UNORDERED_OR_DUPLICATE_TRADE"))
        bad = response()
        bad[3][0]["quoteQty"] = "1000"
        generators.append((bad, "INCONSISTENT_QUOTE_QUANTITY"))
        bad = response()
        bad[3][1]["time"] = NOW + 1
        generators.append((bad, "TRADE_OUTSIDE_UTC_WINDOW"))
        bad = response()
        bad[0]["accountType"] = "MARGIN"
        generators.append((bad, "INVALID_SPOT_ACCOUNT"))
        bad = response()
        bad[2] = [{"symbol": "ETHUSDT"}]
        generators.append((bad, "MISMATCHED_OPEN_ORDER"))
        for parts, reason in generators:
            with self.subTest(reason=reason):
                broker=mocked_broker(parts)
                report=read_only_audit(broker, enabled=True, now_ms=NOW)
                self.assertEqual(report["status"], "UNKNOWN_FAIL_CLOSED")
                self.assertEqual(report["reason"], reason)
                self.assertEqual(report["live_order_permission"], "DENIED")

    def test_credential_error_sanitizes_error(self):
        def broker(*args):
            raise RuntimeError("PRIVATE-KEY-NEVER-EXPOSE")
        result = read_only_audit(broker, enabled=True, now_ms=NOW)
        self.assertEqual(result["status"], "UNKNOWN_FAIL_CLOSED")
        self.assertEqual(result["reason"], "BROKER_READ_FAILED")
        self.assertNotIn("PRIVATE-KEY-NEVER-EXPOSE", json.dumps(result))

    def test_service_requires_manifest_kill_and_readonly_optin(self):
        with tempfile.TemporaryDirectory() as home:
            order = BinanceOrders(Path(home) / "orders.sqlite", "test-manifest")
            payload={"notes_manifest_sha256":"test-manifest","acknowledge_read_only":True}
            with patch.dict(os.environ, {"LIVE_ARMED":"0", "LIVE_DRY_RUN":"1",
                "HSI_ORDER_KILL":"1","HSI_READONLY_HISTORY_AUDIT_ENABLED":"0"}), patch.object(order,"broker") as broker:
                self.assertEqual(order.history_audit(payload)["reason"], "EXPLICIT_READ_APPROVAL_REQUIRED")
                broker.assert_not_called()
            with patch.dict(os.environ, {"LIVE_ARMED":"1", "LIVE_DRY_RUN":"0",
                "HSI_ORDER_KILL":"0","HSI_READONLY_HISTORY_AUDIT_ENABLED":"1"}), patch.object(order,"broker") as broker:
                self.assertEqual(order.history_audit(payload)["reason"], "UNSAFE_DEPLOYMENT_CONFIGURATION")
                broker.assert_not_called()
            with patch.dict(os.environ, {"LIVE_ARMED":"0", "LIVE_DRY_RUN":"1",
                "HSI_ORDER_KILL":"1","HSI_READONLY_HISTORY_AUDIT_ENABLED":"1"}), patch("hsi_binance_readonly_audit.time.time", return_value=NOW / 1000), patch.object(order,"broker",side_effect=response()) as broker:
                outcome=order.history_audit(payload)
                self.assertEqual(outcome["status"], "READ_ONLY_SNAPSHOT_UNVERIFIED")
                self.assertEqual(broker.call_count, 4)
            with self.assertRaises(ValueError):
                order.history_audit({"notes_manifest_sha256":"wrong","acknowledge_read_only":True})

if __name__=="__main__":
    unittest.main()
