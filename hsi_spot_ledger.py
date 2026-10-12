"""Offline FIFO replay for BTCUSDT Spot; never grants trading permission.

This reads *provided* historical fills, not authenticated Binance evidence.
It deliberately cannot prove that fills, fees or opening inventory are complete.
It is a finite, read-only diagnostic toward an eventual broker-reconciled ledger.
"""
from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re

from hsi_spot_risk import MAX_DAILY_REALIZED_LOSS_USDT

PROTOCOL = "HSI-BINANCE-SPOT-FIFO-REPLAY/1"
MAX_FILLS = 2000
MAX_LOTS = 512
MAX_INPUT_BYTES = 1024 * 1024
FRESHNESS_MS = 60000
_DECIMAL = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")


class IncompleteLedger(ValueError):
    """Inputs cannot establish a safe, complete realized-PnL history."""


def decimal_number(value, allow_zero=False):
    if not isinstance(value, str) or len(value) > 40 or not _DECIMAL.fullmatch(value):
        raise IncompleteLedger("INVALID_DECIMAL")
    d = Decimal(value)
    if not d.is_finite() or d < 0 or (not allow_zero and d == 0) or d > Decimal("1e18"):
        raise IncompleteLedger("OUT_OF_RANGE_AMOUNT")
    return d


def positive_int(value):
    if type(value) is not int or not 0 < value < 10**16:
        raise IncompleteLedger("INVALID_INTEGER")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _fail(reason):
    return {"protocol": PROTOCOL, "status": "UNKNOWN_FAIL_CLOSED",
            "reason": reason, "live_order_permission": "DENIED",
            "broker_reconciled": False, "broker_requests": 0}


def replay_day(record):
    """Finite UTC-day FIFO. Never authorizes a Binance order.

    Required: utc_day, as_of_ms, observed_at_ms, opening_lots and fills.
    Opening cost basis and all history must later be independently reconciled
    against signed broker records before being used by *any* risk release.
    """
    if not isinstance(record, dict):
        return _fail("INVALID_INPUT")
    try:
        date_str = record["utc_day"]
        if not isinstance(date_str, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            raise IncompleteLedger("INVALID_UTC_DAY")
        start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        day_begin = int(start.timestamp() * 1000)
        day_end = int((start + timedelta(days=1)).timestamp() * 1000)
        as_of = positive_int(record["as_of_ms"])
        observed = positive_int(record["observed_at_ms"])
        if not day_begin <= as_of or observed < as_of:
            raise IncompleteLedger("INVALID_OBSERVATION_WINDOW")
        if observed - as_of > FRESHNESS_MS:
            return _fail("STALE_OBSERVATION")
        raw_lots = record["opening_lots"]
        fills = record["fills"]
        if not isinstance(raw_lots, list) or not isinstance(fills, list):
            raise IncompleteLedger("INVALID_COLLECTION")
        if len(raw_lots) > MAX_LOTS or len(fills) > MAX_FILLS:
            raise IncompleteLedger("BOUNDED_INPUT_EXCEEDED")
        # Opening lots represent BTC inventory before the *first* supplied fill;
        # there is no proof this inventory or the fill history is complete.
        lots = deque()
        for row in raw_lots:
            if not isinstance(row, dict):
                raise IncompleteLedger("INVALID_OPENING_LOT")
            qty = decimal_number(row["quantity"])
            cost = decimal_number(row["cost_usdt"], allow_zero=True)
            lots.append([qty, cost])
        seen = set()
        prev = None
        running = Decimal("0")
        worst = Decimal("0")
        crossed = False
        sells_today = 0
        with localcontext() as ctx:
            ctx.prec = 60
            for row in fills:
                if not isinstance(row, dict) or row.get("symbol") != "BTCUSDT":
                    raise IncompleteLedger("INVALID_SYMBOL")
                trade_id = positive_int(row["trade_id"])
                stamp = positive_int(row["time_ms"])
                if stamp > as_of or (prev is not None and (stamp, trade_id) <= prev):
                    raise IncompleteLedger("UNORDERED_OR_FUTURE_TRADE")
                if trade_id in seen:
                    raise IncompleteLedger("DUPLICATE_TRADE")
                seen.add(trade_id)
                prev = (stamp, trade_id)
                side = row["side"]
                if side not in ("BUY", "SELL"):
                    raise IncompleteLedger("INVALID_SIDE")
                qty = decimal_number(row["quantity"])
                price = decimal_number(row["price"])
                fee = decimal_number(row["commission"], allow_zero=True)
                asset = row["commission_asset"]
                if asset not in ("BTC", "USDT") and fee != 0:
                    raise IncompleteLedger("UNPRICED_FEE_ASSET")
                if side == "BUY":
                    owned = qty - fee if asset == "BTC" else qty
                    if owned <= 0:
                        raise IncompleteLedger("BUY_FEE_EXCEEDS_QUANTITY")
                    cost = qty * price + (fee if asset == "USDT" else 0)
                    lots.append([owned, cost])
                else:
                    disposed = qty + fee if asset == "BTC" else qty
                    proceeds = qty * price - (fee if asset == "USDT" else 0)
                    if proceeds < 0:
                        raise IncompleteLedger("SELL_FEE_EXCEEDS_PROCEEDS")
                    basis = Decimal(0)
                    while disposed > 0:
                        if not lots:
                            raise IncompleteLedger("UNKNOWN_OPENING_COST_BASIS")
                        old_qty, old_cost = lots[0]
                        used = min(disposed, old_qty)
                        part = old_cost if used == old_qty else old_cost * used / old_qty
                        basis += part
                        disposed -= used
                        old_qty -= used
                        if old_qty == 0:
                            lots.popleft()
                        else:
                            lots[0] = [old_qty, old_cost - part]
                    if day_begin <= stamp < day_end:
                        sells_today += 1
                        running += proceeds - basis
                        worst = min(worst, running)
                        crossed = crossed or running <= -MAX_DAILY_REALIZED_LOSS_USDT
        fingerprint = hashlib.sha256(canonical({
            "utc_day": date_str, "as_of_ms": as_of,
            "opening_lots": raw_lots, "fills": fills
        })).hexdigest()
        return {"protocol": PROTOCOL,
                "status": "LOCAL_REPLAY_ONLY",
                "broker_reconciled": False,
                "live_order_permission": "DENIED",
                "broker_requests": 0,
                "utc_day": date_str,
                "fill_count": len(fills), "sell_fills_today": sells_today,
                "candidate_daily_realized_pnl_usdt": str(running),
                "worst_intraday_running_realized_pnl_usdt": str(worst),
                "stop_threshold_reached_during_replay": crossed,
                "replay_sha256": fingerprint,
                "unproven": [
                    "opening BTC cost basis and initial inventory",
                    "Binance account and historical fill completeness",
                    "external orders, deposits, transfers, staking or corporate actions",
                    "all fees including BNB fee conversion to USDT",
                    "current exchange inventory, unsettled orders, account permissions",
                    "trade-history window coverage and clock authenticity"
                ]}
    except (KeyError, TypeError, ValueError, OverflowError, ArithmeticError) as exc:
        reason = str(exc) if isinstance(exc, IncompleteLedger) else "MALFORMED_INPUT"
        return _fail(reason)


def review_file(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        return _fail("FILE_MISSING_OR_TOO_LARGE")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return _fail("INVALID_JSON")
    return replay_day(payload)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, help="optional local, nonsecret JSON ledger fixture")
    a = p.parse_args()
    result = review_file(a.input) if a.input else _fail("NO_BROKER_RECONCILED_INPUT")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
