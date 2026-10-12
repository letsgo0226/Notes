"""Deterministic network-mocked public K-line validation and CLSDP study tests."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.parse
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "clsdp"))
from market_history import (  # noqa: E402
    HistoryError, INTERVAL_MS, ENDPOINT, encode_csv, fetch_recent,
    get_public_klines, summary,
)
from run_research import research  # noqa: E402

NOW = datetime(2026, 10, 13, 4, 45, tzinfo=timezone.utc)


def fake_page(url):
    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme == "https" and parsed.netloc == "data-api.binance.vision"
    assert parsed.path == "/api/v3/klines"
    query = urllib.parse.parse_qs(parsed.query)
    assert query["symbol"] == ["BTCUSDT"]
    assert query["interval"] == ["1h"]
    start = int(query["startTime"][0])
    end = int(query["endTime"][0])
    count = int(query["limit"][0])
    assert count == (end - start) // INTERVAL_MS + 1
    result = []
    for i in range(count):
        stamp = start + i * INTERVAL_MS
        n = (stamp // INTERVAL_MS) % 30
        price = Decimal(100) + Decimal(n)
        close = price - Decimal(5) if n % 7 == 0 else price + Decimal(1)
        result.append([
            stamp, str(price), str(max(price,close)+1),
            str(min(price,close)-1), str(close), "0",
            stamp + INTERVAL_MS - 1, "0", 0, "0", "0", "0",
        ])
    return result


class CLSDPMarketHistoryTests(unittest.TestCase):
    def test_reproducible_closed_only_complete_720_hour_snapshot(self):
        called = []

        def getter(url):
            called.append(url)
            return fake_page(url)

        rows = fetch_recent(now=NOW, hours=720, getter=getter)
        self.assertEqual(len(rows), 720)
        self.assertEqual(len(called), 2)
        self.assertEqual(rows[-1]["timestamp"], "2026-10-13T02:00:00Z")
        for first, second in zip(rows, rows[1:]):
            self.assertEqual((second["time"]-first["time"]).total_seconds(), 3600)
        blob = encode_csv(rows)
        report = summary(rows, blob)
        self.assertEqual(report["symbol"], "BTCUSDT")
        self.assertEqual(report["network_method"], "PUBLIC_HTTPS_GET_ONLY")
        self.assertEqual(report["signed_requests"], 0)
        self.assertFalse(report["exchange_origin_independently_authenticated"])
        self.assertEqual(report["live_order_permission"], "DENIED")
        self.assertEqual(report["csv_sha256"], summary(rows, blob)["csv_sha256"])

    def test_strict_missing_duplicate_out_of_order_bad_ohlc_and_bad_close(self):
        bads = [
            lambda rows: rows.pop(),
            lambda rows: rows.__setitem__(1, rows[0]),
            lambda rows: rows[0].__setitem__(2, "1"),
            lambda rows: rows[0].__setitem__(6, rows[0][0] + INTERVAL_MS),
            lambda rows: rows[0].__setitem__(1, "NaN"),
            lambda rows: rows[0].__setitem__(4, "-1"),
            lambda rows: rows[0].__setitem__(0, True),
        ]
        for mutation in bads:
            def getter(url):
                result = fake_page(url)
                mutation(result)
                return result
            with self.subTest(mutation=str(mutation)), self.assertRaises(HistoryError):
                fetch_recent(now=NOW, hours=48, getter=getter)

    def test_invalid_window_and_untrusted_url_rejected_without_request(self):
        for hours in (0, 47, 961, "48", True):
            with self.subTest(hours=hours), self.assertRaises(HistoryError):
                fetch_recent(now=NOW, hours=hours, getter=fake_page)
        with patch("urllib.request.build_opener") as opener:
            for url in [
                "http://data-api.binance.vision/api/v3/klines",
                "https://api.binance.com/api/v3/klines",
                "https://data-api.binance.vision/api/v3/order",
                "https://data-api.binance.vision.evil.test/api/v3/klines",
            ]:
                with self.subTest(url=url), self.assertRaises(HistoryError):
                    get_public_klines(url)
            opener.assert_not_called()

    def test_fixed_rule_comparison_never_releases_live_trading(self):
        rows = fetch_recent(now=NOW, hours=72, getter=fake_page)
        report, content = research(rows, retrieval_clock=NOW)
        self.assertTrue(content.startswith(b"timestamp,open,close"))
        self.assertEqual(report["study"]["development_bars"], 50)
        self.assertEqual(report["study"]["holdout_bars"], 22)
        self.assertEqual(report["closure_review"]["required_count"], 12)
        self.assertEqual(report["closure_review"]["claimed_pass_count"], 0)
        self.assertEqual(report["closure_review"]["status"], "REVIEW_BLOCKED")
        self.assertEqual(report["live_order_permission"], "DENIED")
        self.assertFalse(report["auto_release_allowed"])
        self.assertFalse(report["deploy_allowed"])
        self.assertEqual(report["broker_calls"], 0)
        self.assertEqual(report["real_orders"], 0)
        self.assertIn("no_trade_equity_change_usdt", report["study"]["baselines"])
        self.assertEqual(len(report["study"]["synthetic_stress"]), 2)
        self.assertNotIn("api_key", json.dumps(report).lower())

    def test_study_is_deterministic_given_identical_public_candles(self):
        rows = fetch_recent(now=NOW, hours=72, getter=fake_page)
        left, a = research(rows, retrieval_clock=NOW)
        right, b = research(deepcopy(rows), retrieval_clock=NOW)
        self.assertEqual(left, right)
        self.assertEqual(a, b)
        self.assertEqual(left["study"]["rule"],
                         "FIXED_3_CLOSE_SMA_TWO_BAR_CONFIRM_NEXT_OPEN")

    def test_source_unavailability_blocks_entire_study(self):
        def missing(_):
            return []
        with self.assertRaisesRegex(HistoryError, "INCOMPLETE_PUBLIC_KLINE_PAGE"):
            fetch_recent(now=NOW, hours=48, getter=missing)
        rows = fetch_recent(now=NOW, hours=48, getter=fake_page)
        with self.assertRaisesRegex(ValueError, "RESEARCH_HISTORY_INSUFFICIENT"):
            research(rows[:20], retrieval_clock=NOW)


if __name__ == "__main__":
    unittest.main()
