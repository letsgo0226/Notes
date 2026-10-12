#!/usr/bin/env python3
"""CLSDP public-candle research orchestration, no private endpoints or orders.

Uses a preregistered fixed CLTP hypothesis without parameter fitting.
All outputs are an auditable RESEARCH PACKAGE, never broker authorization.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cltp"))
from cltp import backtest, decimal_string  # noqa: E402
from closure_standard import PROTOCOL, PROGRAM, REQUIRED, evaluate  # noqa: E402
from market_history import (  # noqa: E402
    DEFAULT_HOURS, HistoryError, encode_csv, fetch_recent, summary
)

RESEARCH_PROTOCOL = "HSI-CLSDP-PUBLIC-HISTORY-RESEARCH/1"


def _hold_baseline(candles):
    """Buy-and-hold a 50 USDT-sized synthetic position; 200 stays in cash."""
    with localcontext() as ctx:
        ctx.prec = 90
        first = candles[0]["open"]
        last = candles[-1]["close"]
        fee = Decimal("0.001")
        slippage = Decimal("0.0005")
        exposure = Decimal("50") / (Decimal(1) + fee)
        qty = exposure / (first * (Decimal(1) + slippage))
        remaining_cash = Decimal("250") - exposure * (Decimal(1) + fee)
        return decimal_string(remaining_cash + qty * last - Decimal("250"))


def _gap_stress(candles, multiplier):
    """Artificial adverse gaps; not an empirical model of actual market tails."""
    out = deepcopy(candles)
    for n in range(8, len(out), 12):
        out[n]["open"] *= multiplier
    return backtest(out)


def _brief(backtest_result):
    """Safe, numerical summary; no complex external events retained."""
    return {
        "trade_count": backtest_result["trade_count"],
        "net_equity_change_usdt": backtest_result["net_equity_change_usdt"],
        "max_observed_mark_to_market_drawdown_usdt":
            backtest_result["max_observed_mark_to_market_drawdown_usdt"],
        "fees_paid_usdt": backtest_result["fees_paid_usdt"],
        "simulated_utc_stop_latches": backtest_result["simulated_utc_stop_latches"],
        "broker_calls": 0,
        "live_order_permission": "DENIED",
    }


def research(candles, *, retrieval_clock):
    """Separate fixed-rule train/holdout episodes, then gap stress and baseline.

    This is NOT a statistical profitability or independent sample-availability
    claim. Splitting is predetermined, no fit or parameter search.
    """
    if not isinstance(retrieval_clock, datetime) or retrieval_clock.utcoffset() is None:
        raise ValueError("VALID_UTC_RETRIEVAL_CLOCK_REQUIRED")
    if len(candles) < 48:
        raise ValueError("RESEARCH_HISTORY_INSUFFICIENT")
    boundary = len(candles) * 7 // 10
    dev, holdout = candles[:boundary], candles[boundary:]
    if len(dev) < 7 or len(holdout) < 7:
        raise ValueError("RESEARCH_SPLIT_INSUFFICIENT")
    history_bytes = encode_csv(candles)
    history = summary(candles, history_bytes)
    # These are intentionally UNKNOWN. Fetching public market data and
    # computing an internal backtest do not independently certify results.
    package = {
        "protocol": PROTOCOL, "program": PROGRAM,
        "policy": {
            "symbol": "BTCUSDT",
            "max_order_quote_usdt": "50",
            "utc_daily_realized_loss_stop_usdt": "2",
            "real_trading_enabled": False,
        },
        "assertions": {
            gate: {
                "status": "UNKNOWN",
                "issuer_class": issuer,
                "observation_utc":
                    retrieval_clock.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "evidence_sha256": history["csv_sha256"],
            } for gate, issuer in REQUIRED.items()
        }
    }
    review = evaluate(package, as_of=retrieval_clock)
    if review["status"] != "REVIEW_BLOCKED":
        raise AssertionError("UNEXPECTED_RESEARCH_SELF_AUTHORIZATION")
    full = backtest(candles)
    dev_result = backtest(dev)
    holdout_result = backtest(holdout)
    stress_down = _gap_stress(candles, Decimal("0.8"))
    stress_up = _gap_stress(candles, Decimal("1.2"))
    return {
        "protocol": RESEARCH_PROTOCOL,
        "clock_program": PROGRAM,
        "mode": "PUBLIC_HISTORY_RESEARCH_NOT_ORDERING",
        "data": history,
        "study": {
            "rule": "FIXED_3_CLOSE_SMA_TWO_BAR_CONFIRM_NEXT_OPEN",
            "split": "70_PERCENT_DEVELOPMENT_30_PERCENT_HOLDOUT",
            "parameter_tuning": False,
            "development_bars": len(dev),
            "holdout_bars": len(holdout),
            "development_research": _brief(dev_result),
            "untouched_holdout_research": _brief(holdout_result),
            "full_window_research": _brief(full),
            "baselines": {
                "no_trade_equity_change_usdt": "0",
                "fifty_usdt_buy_hold_equity_change_usdt": _hold_baseline(candles),
            },
            "synthetic_stress": {
                "every_12th_open_after_8th_minus_20pct": _brief(stress_down),
                "every_12th_open_after_8th_plus_20pct": _brief(stress_up),
            },
        },
        "closure_review": {
            "status": review["status"],
            "required_count": review["required_count"],
            "claimed_pass_count": review["claimed_pass_count"],
            "independent_evidence_missing": list(REQUIRED),
            "source_authenticated_by_this_program": False,
            "broker_reconciled_by_this_program": False,
            "can_grant_order_permission": False,
        },
        "limitations": [
            "Only a rolling finite public BTCUSDT 1h candle window; historical source completeness not independently certified",
            "CLTP performance is a proposed fixed research rule, with assumed fills and fees, not validated profitability",
            "Holdout is evaluated as a fresh paper episode with 250 USDT; it is not a walk-forward/live PnL account",
            "Two artificial 20 percent gap stresses do not bound real market risk",
            "No signed Binance account inventory, all-fee FIFO ledger or kill-switch readiness evidence is available",
            "Separate human review and live-release authority remain mandatory",
        ],
        "signed_broker_reads": 0,
        "broker_calls": 0, "real_orders": 0,
        "live_order_permission": "DENIED",
        "auto_release_allowed": False,
        "deploy_allowed": False,
    }, history_bytes


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--hours", type=int, default=DEFAULT_HOURS)
    a = p.parse_args(argv)
    try:
        now = datetime.now(timezone.utc)
        candles = fetch_recent(now=now, hours=a.hours)
        report, history = research(candles, retrieval_clock=now)
        out = a.out_dir.resolve()
        out.mkdir(parents=True, exist_ok=True)
        (out / "btc-usdt-public-history.csv").write_bytes(history)
        (out / "report.json").write_text(
            json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        print("CLSDP_RESEARCH_COMPLETE_REVIEW_BLOCKED", flush=True)
        return 0
    except (HistoryError, ValueError, OSError) as exc:
        # No credential-bearing URL or raw third-party response in error logs.
        p.exit(2, "CLSDP_PUBLIC_RESEARCH_FAILED:" + type(exc).__name__ + "\n")


if __name__ == "__main__":
    sys.exit(main())
