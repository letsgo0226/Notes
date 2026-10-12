"""Review memo sanitizer rejects fabricated authorizations and unsafe numbers."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
import urllib.parse
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "clsdp"))
from render_review import ReviewInputError, render  # noqa: E402
from run_research import research  # noqa: E402
from market_history import fetch_recent, INTERVAL_MS  # noqa: E402

NOW = datetime(2026, 10, 13, 4, 45, tzinfo=timezone.utc)


def mock_public(url):
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    start = int(q["startTime"][0])
    count = int(q["limit"][0])
    rows = []
    for i in range(count):
        t = start + i * INTERVAL_MS
        price = Decimal(90 + i % 10)
        rows.append([t, str(price), str(price + 1), str(price - 1),
                     str(price), "1", t + INTERVAL_MS - 1, "1", 1, "1", "1", "0"])
    return rows


class ReviewMemoTests(unittest.TestCase):
    def test_render_only_review_with_no_release(self):
        rows = fetch_recent(now=NOW, hours=48, getter=mock_public)
        report, _ = research(rows, retrieval_clock=NOW)
        memo = render(report)
        self.assertIn("REVIEW_BLOCKED", memo)
        self.assertIn("live order permission: DENIED", memo)
        self.assertIn("50-USDT buy-and-hold benchmark", memo)
        self.assertIn("review only", memo.lower())
        self.assertNotIn("API_KEY", memo)
        self.assertNotIn("secret", memo.lower())

    def test_reject_any_attempt_to_self_grant_or_forge_report(self):
        rows = fetch_recent(now=NOW, hours=48, getter=mock_public)
        baseline, _ = research(rows, retrieval_clock=NOW)
        cases = [
            ("live_order_permission", "APPROVED"),
            ("broker_calls", 1),
            ("real_orders", 1),
            ("auto_release_allowed", True),
            ("deploy_allowed", True),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                forged = deepcopy(baseline)
                forged[key] = value
                with self.assertRaises(ReviewInputError):
                    render(forged)
        forged = deepcopy(baseline)
        forged["closure_review"]["status"] = "SELF_ASSERTED_COMPLETE_NEEDS_INDEPENDENT_REVIEW"
        with self.assertRaises(ReviewInputError):
            render(forged)
        forged = deepcopy(baseline)
        forged["data"]["csv_sha256"] = "[CLICK HERE]"
        with self.assertRaises(ReviewInputError):
            render(forged)
        forged = deepcopy(baseline)
        forged["study"]["holdout_research"] = {"net_equity_change_usdt": "nan"}
        # Must also reject dangerous strings on the *actual* required field.
        forged["study"]["untouched_holdout_research"]["net_equity_change_usdt"] = "<script>"
        with self.assertRaises(ReviewInputError):
            render(forged)


if __name__ == "__main__":
    unittest.main()
