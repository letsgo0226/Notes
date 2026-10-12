"""Bounded, read-only Binance Spot account snapshot for human risk review.

Operator-authenticated service route only. Broker uses signed GETs for
account, API restrictions, open orders and a 24h-or-less trade window.
No order creation, order testing, cancel, persistence or live authorization.
No fill history or balances are returned to the caller. Synthetic tests only.
"""
from datetime import datetime, timezone
from decimal import Decimal
import re
import time

from hsi_spot_risk import MAX_DAILY_REALIZED_LOSS_USDT
from hsi_spot_trade_digest import PROTOCOL as DIGEST_PROTOCOL, normalized_trade, digest_trades

PROTOCOL = "HSI-TRADER42-BINANCE-READONLY-AUDIT/1"
SYMBOL = "BTCUSDT"
MAX_TRADES = 1000
MILLISECONDS_DAY = 86400000
_DECIMAL = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")


class ReviewFailure(ValueError):
    pass


def _denied(reason, requests=0):
    return {
        "protocol": PROTOCOL,
        "status": "UNKNOWN_FAIL_CLOSED",
        "reason": reason,
        "symbol": SYMBOL,
        "daily_realized_loss_stop_usdt": str(MAX_DAILY_REALIZED_LOSS_USDT),
        "signed_reads": requests,
        "broker_reconciled": False,
        "daily_pnl_verified": False,
        "live_order_permission": "DENIED",
        "real_order_submissions": 0,
    }


def _amount(raw, zero=True):
    if not isinstance(raw, str) or len(raw) > 40 or not _DECIMAL.fullmatch(raw):
        raise ReviewFailure("INVALID_DECIMAL")
    value = Decimal(raw)
    if not value.is_finite() or value < 0 or value > Decimal("1e18") or (not zero and value == 0):
        raise ReviewFailure("INVALID_AMOUNT")
    return value


def _nonnegative_int(value):
    if type(value) is not int or not 0 <= value < 10**18:
        raise ReviewFailure("INVALID_INTEGER")
    return value


def read_only_audit(broker, *, enabled=False, now_ms=None):
    """Audit one UTC day using up to four allowlisted signed GETs.

    The broker signature is broker(path, params, method, signed). In production
    this is BinanceOrders.broker; in CI it is a strict mock. This never infers
    full history, transfers, positions or verified opening cost basis.
    """
    if enabled is not True:
        return _denied("EXPLICIT_READ_APPROVAL_REQUIRED")
    calls = 0
    try:
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        now_ms = _nonnegative_int(now_ms)
        if not 1600000000000 <= now_ms < 4102444800000:
            raise ReviewFailure("INVALID_CLOCK")
        midnight = now_ms - now_ms % MILLISECONDS_DAY
        # Only these four USER_DATA endpoints may be read. No POST method.
        def read(path, params=None):
            nonlocal calls
            if path not in ("/api/v3/account",
                            "/sapi/v1/account/apiRestrictions",
                            "/api/v3/openOrders",
                            "/api/v3/myTrades"):
                raise ReviewFailure("ENDPOINT_NOT_ALLOWED")
            if calls >= 4:
                raise ReviewFailure("READ_BUDGET_EXCEEDED")
            calls += 1
            return broker(path, params or {}, "GET", True)

        account = read("/api/v3/account", {"omitZeroBalances": "true"})
        if not isinstance(account, dict) or account.get("accountType") != "SPOT" or type(account.get("canTrade")) is not bool:
            raise ReviewFailure("INVALID_SPOT_ACCOUNT")
        balances = account.get("balances")
        if not isinstance(balances, list):
            raise ReviewFailure("MISSING_BALANCES")
        btc_nonzero = False
        for row in balances:
            if not isinstance(row, dict) or not isinstance(row.get("asset"), str):
                raise ReviewFailure("INVALID_BALANCE")
            if row["asset"] == "BTC":
                btc_nonzero = bool(_amount(row.get("free")) + _amount(row.get("locked")))
        restrictions = read("/sapi/v1/account/apiRestrictions")
        if not isinstance(restrictions, dict) or type(restrictions.get("enableSpotAndMarginTrading")) is not bool:
            raise ReviewFailure("INVALID_KEY_RESTRICTIONS")
        trading_permission = restrictions["enableSpotAndMarginTrading"]
        if trading_permission:
            # Stop immediately when the API key unexpectedly permits trading.
            # Never proceed to balances-independent trade history in this state.
            return {**_denied("SPOT_TRADING_PERMISSION_ENABLED", calls),
                    "api_spot_trading_enabled": True}

        open_orders = read("/api/v3/openOrders", {"symbol": SYMBOL})
        if not isinstance(open_orders, list):
            raise ReviewFailure("INVALID_OPEN_ORDERS")
        if any(not isinstance(x, dict) or x.get("symbol") != SYMBOL for x in open_orders):
            raise ReviewFailure("MISMATCHED_OPEN_ORDER")

        # Binance permits this pair of time filters and limits it to <=24h.
        # This is explicitly today's UTC window, not historical coverage.
        trades = read("/api/v3/myTrades", {
            "symbol": SYMBOL, "startTime": midnight,
            "endTime": now_ms, "limit": MAX_TRADES
        })
        if not isinstance(trades, list):
            raise ReviewFailure("INVALID_TRADE_LIST")
        if len(trades) >= MAX_TRADES:
            raise ReviewFailure("POSSIBLY_TRUNCATED_HISTORY")
        keys = set()
        previous = None
        unsupported_fee_assets = set()
        side_counts = {"BUY": 0, "SELL": 0}
        digest_rows = []
        for row in trades:
            if not isinstance(row, dict) or row.get("symbol") != SYMBOL or type(row.get("isBuyer")) is not bool:
                raise ReviewFailure("INVALID_TRADE")
            id_ = _nonnegative_int(row.get("id"))
            timestamp = _nonnegative_int(row.get("time"))
            _nonnegative_int(row.get("orderId"))
            if not midnight <= timestamp <= now_ms:
                raise ReviewFailure("TRADE_OUTSIDE_UTC_WINDOW")
            if previous is not None and (timestamp, id_) <= previous:
                raise ReviewFailure("UNORDERED_OR_DUPLICATE_TRADE")
            previous = (timestamp, id_)
            if id_ in keys:
                raise ReviewFailure("DUPLICATE_TRADE")
            keys.add(id_)
            qty = _amount(row.get("qty"), zero=False)
            price = _amount(row.get("price"), zero=False)
            quote = _amount(row.get("quoteQty"), zero=False)
            fee = _amount(row.get("commission"))
            asset = row.get("commissionAsset")
            if not isinstance(asset, str) or not asset or len(asset) > 20:
                raise ReviewFailure("INVALID_FEE_ASSET")
            if fee and asset not in ("BTC", "USDT"):
                unsupported_fee_assets.add(asset)
            # Binance price/qty and quoteQty decimal rounding tolerance.
            tolerance = max(Decimal("0.00000001"), qty * price * Decimal("0.000000001"))
            if abs(qty * price - quote) > tolerance:
                raise ReviewFailure("INCONSISTENT_QUOTE_QUANTITY")
            side = "BUY" if row["isBuyer"] else "SELL"
            side_counts[side] += 1
            digest_rows.append(normalized_trade(id_, timestamp, side, qty, price, fee, asset))
        proof = digest_trades(digest_rows)
        return {
            "protocol": PROTOCOL, "status": "READ_ONLY_SNAPSHOT_UNVERIFIED",
            "symbol": SYMBOL, "utc_day": datetime.fromtimestamp(midnight / 1000, timezone.utc).date().isoformat(),
            "snapshot_ms": now_ms, "trade_count": len(trades),
            "buy_fill_count": side_counts["BUY"], "sell_fill_count": side_counts["SELL"],
            "trade_fingerprint_sha256": proof,
            "trade_fingerprint_scheme": DIGEST_PROTOCOL,
            "api_spot_trading_enabled": trading_permission,
            "account_can_trade": account["canTrade"],
            "btc_inventory_present": btc_nonzero,
            "open_orders_present": bool(open_orders),
            "open_order_count": len(open_orders),
            "non_usdt_btc_fee_present": bool(unsupported_fee_assets),
            "broker_reconciled": False, "daily_pnl_verified": False,
            "opening_cost_basis_verified": False,
            "full_trade_history_verified": False,
            "transfers_and_non_btcusdt_activity_verified": False,
            "signed_reads": calls,
            "daily_realized_loss_stop_usdt": str(MAX_DAILY_REALIZED_LOSS_USDT),
            "live_order_permission": "DENIED",
            "real_order_submissions": 0,
            "reason": "Signed reads can observe a bounded UTC day, not verify lifetime FIFO basis or all account movements."
        }
    except (ValueError, TypeError, KeyError, OverflowError, ArithmeticError) as exc:
        return _denied(str(exc) if isinstance(exc, ReviewFailure) else "INVALID_BROKER_RESPONSE", calls)
    except Exception:
        # Never propagate broker URLs, keys, balances, or raw response payloads.
        return _denied("BROKER_READ_FAILED", calls)
