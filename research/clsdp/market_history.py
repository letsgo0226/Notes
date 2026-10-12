#!/usr/bin/env python3
"""Public-only BTCUSDT historical candles, bounded and fail-closed.

No private Binance endpoints, order routes, API keys, account calls or
production permission. Reads only public Spot market klines via HTTPS.
Data retrieval does not authenticate completeness or predictive advantage.
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://data-api.binance.vision/api/v3/klines"
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
INTERVAL_MS = 3600000
PAGE_SIZE = 500
DEFAULT_HOURS = 720
MAX_HOURS = 960
MAX_RESPONSE = 1_000_000
DECIMAL_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")


class HistoryError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise HistoryError("PUBLIC_HISTORY_REDIRECT_REJECTED")


def _decimal(text, allow_zero=False):
    if (type(text) is not str or len(text) > 40 or
            not DECIMAL_RE.fullmatch(text)):
        raise HistoryError("INVALID_PRICE_FORMAT")
    value = Decimal(text)
    if not value.is_finite() or value < 0 or (not allow_zero and value == 0):
        raise HistoryError("INVALID_PRICE_RANGE")
    return value


def get_public_klines(url):
    """The ONLY function allowed to perform an HTTPS request in CLSDP."""
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "data-api.binance.vision"
            or parts.path != "/api/v3/klines" or parts.fragment
            or any(k not in {"symbol", "interval", "startTime", "endTime", "limit"}
                   for k, _ in urllib.parse.parse_qsl(parts.query))
            or parts.username or parts.password):
        raise HistoryError("UNAPPROVED_PUBLIC_MARKET_URL")
    req = urllib.request.Request(url, method="GET",
                                 headers={"Accept": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise HistoryError("PUBLIC_MARKET_GET_FAILED") from exc
    if len(raw) > MAX_RESPONSE:
        raise HistoryError("PUBLIC_RESPONSE_TOO_LARGE")
    try:
        return json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(
            HistoryError("INVALID_MARKET_JSON_NUMBER")))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise HistoryError("INVALID_PUBLIC_MARKET_JSON") from exc


def fetch_recent(*, now, hours=DEFAULT_HOURS, getter=get_public_klines):
    """Fetch fixed completed hourly interval, no gaps or duplicate opens.

    Includes one-hour completion safety margin: at 04:xx UTC, latest
    accepted candle opens at 02:00 and closes at 03:00. No current bar.
    """
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None or now.utcoffset().total_seconds() != 0
            or type(hours) is not int or hours < 48 or hours > MAX_HOURS):
        raise HistoryError("INVALID_RESEARCH_WINDOW")
    floor_hour = int(now.timestamp() * 1000) // INTERVAL_MS * INTERVAL_MS
    last_open_ms = floor_hour - 2 * INTERVAL_MS
    first_open_ms = last_open_ms - (hours - 1) * INTERVAL_MS
    if first_open_ms < 0:
        raise HistoryError("INVALID_RESEARCH_WINDOW")
    out = []
    for offset in range(0, hours, PAGE_SIZE):
        count = min(PAGE_SIZE, hours - offset)
        first = first_open_ms + offset * INTERVAL_MS
        last = first + (count - 1) * INTERVAL_MS
        q = urllib.parse.urlencode({
            "symbol": SYMBOL, "interval": INTERVAL,
            "startTime": first, "endTime": last, "limit": count,
        })
        rows = getter(ENDPOINT + "?" + q)
        if not isinstance(rows, list) or len(rows) != count:
            raise HistoryError("INCOMPLETE_PUBLIC_KLINE_PAGE")
        for i, row in enumerate(rows):
            required_open = first + i * INTERVAL_MS
            if (not isinstance(row, list) or len(row) != 12
                    or type(row[0]) is not int
                    or type(row[6]) is not int
                    or row[0] != required_open
                    or row[6] != required_open + INTERVAL_MS - 1):
                raise HistoryError("INVALID_OR_NONCONTIGUOUS_KLINE")
            opening, high, low, closing = (_decimal(row[j]) for j in (1, 2, 3, 4))
            _decimal(row[5], allow_zero=True)  # volume
            if high < max(opening, closing) or low > min(opening, closing) or low > high:
                raise HistoryError("INCONSISTENT_KLINE_OHLC")
            if row[0] > last_open_ms:
                raise HistoryError("UNFINISHED_KLINE_REJECTED")
            stamp = datetime.fromtimestamp(row[0] / 1000, timezone.utc)
            out.append({
                "time": stamp,
                "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": opening, "close": closing,
            })
    if len(out) != hours:
        raise HistoryError("MISSING_HISTORICAL_ROWS")
    return out


def encode_csv(candles):
    """Return a bounded, immutable-format local candle snapshot."""
    import csv
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(("timestamp", "open", "close"))
    for row in candles:
        writer.writerow((row["timestamp"], format(row["open"], "f"),
                         format(row["close"], "f")))
    result = buf.getvalue().encode("utf-8")
    if len(result) > 2_000_000:
        raise HistoryError("CANDLE_CSV_TOO_LARGE")
    return result


def summary(candles, contents):
    """Hash equality authenticates neither venue nor independent provenance."""
    return {
        "source_endpoint": ENDPOINT,
        "symbol": SYMBOL, "interval": INTERVAL,
        "count": len(candles),
        "first_utc": candles[0]["timestamp"],
        "last_utc": candles[-1]["timestamp"],
        "csv_sha256": hashlib.sha256(contents).hexdigest(),
        "network_method": "PUBLIC_HTTPS_GET_ONLY",
        "signed_requests": 0,
        "exchange_origin_independently_authenticated": False,
        "historical_completeness_beyond_requested_window_verified": False,
        "live_order_permission": "DENIED",
    }
