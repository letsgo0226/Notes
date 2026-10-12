"""Trader_42: SQLite-backed, DENY-ONLY UTC daily loss stop review.

This is intentionally not an execution authorization engine. No signed
exchange history, trustworthy opening basis or live reconciler is available.
A supplied offline FIFO replay MAY trigger a conservative review halt; it
can never clear a halt or approve a real Binance order.

The only normal call from BinanceOrders.submit() is enforce_pretrade():
it ALWAYS raises, independently of the separate assert_live_release() block.
Broker requests: 0; order requests: 0.
"""
from datetime import datetime, timezone
from decimal import Decimal
import re
import time

from hsi_spot_risk import MAX_DAILY_REALIZED_LOSS_USDT

PROTOCOL = "HSI-TRADER42-UTC-LOSS-LATCH-REVIEW/1"
SOURCE = "UNVERIFIED_LOCAL_FIFO"
MIN_TIME_MS = 1600000000000
MAX_TIME_MS = 4102444800000
REPLAY_PROTOCOL = "HSI-BINANCE-SPOT-FIFO-REPLAY/1"
_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?\Z")


class PretradeRejected(ValueError):
    """Explicit rejection; no automatic release or order submission."""


def utc_day(now_ms):
    if type(now_ms) is not int or not MIN_TIME_MS <= now_ms < MAX_TIME_MS:
        raise PretradeRejected("RISK_UNKNOWN_INVALID_UTC_CLOCK")
    return datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).date().isoformat()


def ensure_schema(connection):
    """Separate table, in the SAME journal database as manual order tickets."""
    connection.execute(
        "CREATE TABLE IF NOT EXISTS spot_utc_loss_latch ("
        "utc_day TEXT PRIMARY KEY, "
        "source TEXT NOT NULL CHECK(source = 'UNVERIFIED_LOCAL_FIFO'), "
        "worst_pnl_usdt TEXT NOT NULL, "
        "observed_at_ms INTEGER NOT NULL)"
    )


def _latched(connection, day):
    ensure_schema(connection)
    return connection.execute(
        "SELECT source FROM spot_utc_loss_latch WHERE utc_day = ?", (day,)
    ).fetchone() is not None


def status(connection, now_ms=None):
    """A conservative state report, never a green pretrade assessment."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    try:
        day = utc_day(now_ms)
        halted = _latched(connection, day)
        return {
            "protocol": PROTOCOL, "utc_day": day,
            "status": "HALT_DAILY_LOSS_REVIEW_LATCHED" if halted else "UNKNOWN_FAIL_CLOSED",
            "broker_reconciled": False, "live_order_permission": "DENIED",
            "reason": ("Offline stop evidence was latched; manual review required"
                       if halted else
                       "No authenticated, complete broker-derived daily PnL"),
            "daily_realized_loss_threshold_usdt": str(MAX_DAILY_REALIZED_LOSS_USDT),
        }
    except (ValueError, OverflowError):
        return {
            "protocol": PROTOCOL, "status": "UNKNOWN_FAIL_CLOSED",
            "reason": "Invalid UTC clock", "broker_reconciled": False,
            "live_order_permission": "DENIED",
        }


def observe_offline_loss(connection, replay, *, now_ms):
    """Conservative diagnostic: only creates or keeps a STOP latch.

    Strictly accepts the *unverified* local-replay protocol; source data
    cannot self-declare exchange provenance or automatic release. Even a
    below-limit replay leaves status UNKNOWN_FAIL_CLOSED. A negative
    replay that crossed the threshold can persist a block for the day.
    This method is not exposed by the HTTP service.
    """
    day = utc_day(now_ms)
    if not isinstance(replay, dict):
        raise PretradeRejected("RISK_UNKNOWN_INVALID_OFFLINE_EVIDENCE")
    if (replay.get("protocol") != REPLAY_PROTOCOL
            or replay.get("status") != "LOCAL_REPLAY_ONLY"
            or replay.get("utc_day") != day
            or replay.get("broker_reconciled") is not False
            or replay.get("live_order_permission") != "DENIED"
            or replay.get("broker_requests") != 0
            or type(replay.get("snapshot_ms")) is not int
            or not 0 <= now_ms - replay["snapshot_ms"] <= 60000):
        raise PretradeRejected("RISK_UNKNOWN_UNTRUSTED_OR_STALE_EVIDENCE")
    value = replay.get("worst_intraday_running_realized_pnl_usdt")
    if (type(value) is not str or len(value) > 48
            or not _DECIMAL.fullmatch(value)):
        raise PretradeRejected("RISK_UNKNOWN_INVALID_PNL")
    worst = Decimal(value)
    if not worst.is_finite() or abs(worst) > Decimal("1e18"):
        raise PretradeRejected("RISK_UNKNOWN_INVALID_PNL")
    flag = replay.get("stop_threshold_reached_during_replay")
    if type(flag) is not bool or flag != (worst <= -MAX_DAILY_REALIZED_LOSS_USDT):
        raise PretradeRejected("RISK_UNKNOWN_INCONSISTENT_STOP_FLAG")
    if flag:
        ensure_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO spot_utc_loss_latch"
            "(utc_day, source, worst_pnl_usdt, observed_at_ms) VALUES (?,?,?,?)",
            (day, SOURCE, value, now_ms),
        )
    # Never classify offline input as exchange-reconciled.
    return status(connection, now_ms=now_ms)


def enforce_pretrade(connection, *, now_ms=None):
    """Unconditionally DENY until separate broker-reconciled live release.

    Called by manual submit BEFORE any broker filter/order request. A
    persisted daily halt gives a specific rejection reason. Missing,
    changed, or non-reconciled evidence is also rejected. A future
    authorized implementation must be a separately reviewed code change.
    """
    try:
        review = status(connection, now_ms=now_ms)
    except Exception as exc:
        raise PretradeRejected("RISK_UNKNOWN_LEDGER_UNAVAILABLE") from None
    if review["status"] == "HALT_DAILY_LOSS_REVIEW_LATCHED":
        raise PretradeRejected("HALT_DAILY_LOSS_REVIEW_LATCHED")
    raise PretradeRejected("RISK_UNKNOWN_BROKER_RECONCILIATION_REQUIRED")
