"""Fail-closed BTCUSDT Spot risk profile, independent of Railway variables.

The daily loss threshold is a *stop threshold* once reconciled, NOT a
guarantee that market losses cannot exceed 2 USDT. No real order release
exists in this revision: separate human-approved deployment is required.
"""
from decimal import Decimal
import json
from pathlib import Path

SYMBOL = "BTCUSDT"
MAX_ORDER_QUOTE_USDT = Decimal("50")
MAX_DAILY_REALIZED_LOSS_USDT = Decimal("2")
PROFILE = "HSI-TRADER42-SPOT-RISK/1"


def restricted_order_limit(configured_limit):
    """An environment variable may tighten but never expand the policy."""
    from hsi_binance_orders import amount
    return min(amount(configured_limit), MAX_ORDER_QUOTE_USDT)


def enforce_order(symbol, price, quantity, configured_limit):
    from hsi_binance_orders import amount
    if symbol != SYMBOL:
        raise ValueError("Spot risk policy only permits BTCUSDT")
    notional = amount(price) * amount(quantity)
    if notional > restricted_order_limit(configured_limit):
        raise ValueError("order exceeds effective BTCUSDT risk limit")
    return notional


def evaluate_daily_loss(realized_pnl_usdt=None, verified=False, fresh=False):
    """Diagnostics only; never authorizes a live order."""
    from hsi_binance_orders import amount
    if not verified or not fresh or realized_pnl_usdt is None:
        return {"status": "UNKNOWN_FAIL_CLOSED", "reason": "reconciled daily PnL unavailable"}
    try:
        pnl = Decimal(str(realized_pnl_usdt))
    except (ValueError, ArithmeticError):
        return {"status": "UNKNOWN_FAIL_CLOSED", "reason": "invalid daily PnL"}
    if not pnl.is_finite():
        return {"status": "UNKNOWN_FAIL_CLOSED", "reason": "invalid daily PnL"}
    if pnl <= -MAX_DAILY_REALIZED_LOSS_USDT:
        return {"status": "HALT_DAILY_LOSS", "reason": "daily realized loss threshold reached"}
    return {"status": "BELOW_STOP_THRESHOLD_REVIEW_ONLY",
            "reason": "past PnL cannot bound the loss on a future order"}


def assert_live_release():
    """Hard release gate: intentionally no environment-only bypass.

    Deployment variables, operator token and order confirmation are necessary
    but NOT sufficient. Actual live release must be a separate reviewed code
    change implementing independently reconciled positions/PnL, risk budgets,
    and explicit operator authorization.
    """
    raise ValueError("LIVE_BLOCKED: separately approved broker-reconciled risk engine not deployed")


def review_report():
    return {"protocol": PROFILE,
            "exchange": "Binance", "market": "Spot", "symbol": SYMBOL,
            "max_order_quote_usdt": str(MAX_ORDER_QUOTE_USDT),
            "max_daily_realized_loss_usdt": str(MAX_DAILY_REALIZED_LOSS_USDT),
            "daily_loss": evaluate_daily_loss(),
            "live_release": "BLOCKED_SEPARATE_APPROVAL_REQUIRED",
            "auto_mode": "REVIEW_ONLY_NO_STRATEGY_PROMOTION",
            "requirements": [
                "independent authenticated Binance account and fill checks",
                "verified UTC daily realized PnL with opening cost basis and all fees",
                "reconciled inventory, open orders, crash recovery and external fills",
                "human-reviewed strategy change before production",
                "exchange constraints and exposure-aware pretrade checks",
            ],
            "no_guarantee": "a 2 USDT stop threshold cannot guarantee a 2 USDT maximum market loss"}


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    report = review_report()
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
