"""A shared canonical, non-authorizing BTCUSDT trade fingerprint contract.

Not a signature, not a proof of Binance origin, not a trading permit.
The exact same normalized rows are produced from manually supplied
FIFO-replay inputs and an operator-authorized signed GET snapshot.
"""
from decimal import Decimal
import hashlib
import json

PROTOCOL = "HSI-TRADER42-TRADE-FINGERPRINT/1"


def exact_decimal(value):
    """Normalize spelling but never round using the ambient Decimal context."""
    rendered = format(Decimal(value), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def normalized_trade(trade_id, stamp_ms, side, quantity, price, commission, commission_asset):
    """The caller validates order, origin, amounts, symbols and time bounds."""
    return [
        trade_id, stamp_ms, side,
        exact_decimal(quantity),
        exact_decimal(price),
        exact_decimal(commission),
        commission_asset,
    ]


def digest_trades(rows):
    payload = (PROTOCOL + "\n").encode("utf-8")
    payload += json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
