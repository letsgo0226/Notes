#!/usr/bin/env python3
"""Render a bounded review-only Markdown artifact; never a release manifest."""
import argparse
import json
from pathlib import Path
import re

NUMERIC = re.compile(r"-?[0-9]{1,40}(?:\.[0-9]{1,120})?\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ReviewInputError(ValueError):
    pass


def render(report):
    if not isinstance(report, dict) or report.get("protocol") != "HSI-CLSDP-PUBLIC-HISTORY-RESEARCH/1":
        raise ReviewInputError("INVALID_RESEARCH_REPORT")
    data = report.get("data")
    study = report.get("study")
    closure = report.get("closure_review")
    if (not isinstance(data, dict) or not isinstance(study, dict)
            or not isinstance(closure, dict)
            or data.get("symbol") != "BTCUSDT"
            or data.get("interval") != "1h"
            or type(data.get("count")) is not int
            or not 48 <= data["count"] <= 960
            or not isinstance(data.get("csv_sha256"), str)
            or not DIGEST.fullmatch(data["csv_sha256"])
            or report.get("broker_calls") != 0
            or report.get("real_orders") != 0
            or report.get("live_order_permission") != "DENIED"
            or report.get("auto_release_allowed") is not False
            or report.get("deploy_allowed") is not False
            or closure.get("status") != "REVIEW_BLOCKED"
            or closure.get("claimed_pass_count") != 0
            or closure.get("required_count") != 12):
        raise ReviewInputError("UNSAFE_OR_UNVERIFIED_RESEARCH_REPORT")
    dev = study.get("development_research")
    hold = study.get("untouched_holdout_research")
    full = study.get("full_window_research")
    baseline = study.get("baselines")
    if not all(isinstance(x, dict) for x in (dev, hold, full, baseline)):
        raise ReviewInputError("MISSING_COMPARISON")
    values = [
        dev.get("net_equity_change_usdt"),
        hold.get("net_equity_change_usdt"),
        full.get("net_equity_change_usdt"),
        baseline.get("no_trade_equity_change_usdt"),
        baseline.get("fifty_usdt_buy_hold_equity_change_usdt"),
        full.get("max_observed_mark_to_market_drawdown_usdt"),
    ]
    if any(type(x) is not str or not NUMERIC.fullmatch(x) for x in values):
        raise ReviewInputError("INVALID_COMPARISON_METRIC")
    devgain, holdgain, fullgain, idle, buyhold, drawdown = values
    return (
        "# CLSDP Weekly BTCUSDT Research — Review Only\n\n"
        "**NOT production-authorized.** No orders, key access, Railway updates, "
        "merges, live deployments or automatic risk-gate overrides.\n\n"
        "## Public historical market sample\n\n"
        f"- Symbol: BTCUSDT, interval: 1h, rows: {data['count']}\n"
        f"- Locally checked CSV SHA-256: {data['csv_sha256']}\n"
        "- Public market API only; independently authenticated completeness: **NO**\n\n"
        "## Fixed illustrative CLTP research\n\n"
        "- Clock: P=55067263, two-phase observe/verify; not a price predictor.\n"
        "- Predeclared rule: 3-bar moving-average deviation; no parameter fitting.\n"
        "- Development and holdout are **independent paper episodes** with 250 USDT each, "
        "not a continuous portfolio or evidence of alpha.\n\n"
        "| Metric | Candidate paper result |\n|---|---:|\n"
        f"| Development equity change | {devgain} USDT |\n"
        f"| Holdout equity change | {holdgain} USDT |\n"
        f"| Entire sample equity change | {fullgain} USDT |\n"
        f"| No-trade benchmark | {idle} USDT |\n"
        f"| 50-USDT buy-and-hold benchmark | {buyhold} USDT |\n"
        f"| Observed mark-to-market drawdown in sample | {drawdown} USDT |\n\n"
        "Stress assumptions additionally include artificial 20% jump/drop opening "
        "gaps every 12 bars (see attached workflow research report).\n\n"
        "## Formal evidence closure\n\n"
        "- CLSDP self-evaluation: **REVIEW_BLOCKED**; 0 of 12 required "
        "externally verified attestations.\n"
        "- A logically closed research computation cannot certify its own issuer "
        "or prove real-world financial profitability.\n"
        "- The 2-USDT UTC realized-loss stop is only a synthetic threshold and "
        "cannot cap gaps, fees, unreconciled positions, or unexpected fills.\n"
        "- **Binance live order permission: DENIED.**\n"
        "- External human approval and an independently audited broker-risk "
        "engine are both mandatory before discussing live activation.\n\n"
        "This GitHub PR is an **automatically generated draft for human review**, "
        "not an authorization to merge, trade or deploy.\n"
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.report.is_symlink() or args.report.stat().st_size > 100000:
        p.exit(2, "REVIEW_REPORT_TOO_LARGE_OR_LINKED\n")
    try:
        data = json.loads(args.report.read_text(encoding="utf-8"))
        content = render(data)
    except (OSError, UnicodeError, ValueError) as exc:
        p.exit(2, "REVIEW_REJECTED:" + type(exc).__name__ + "\n")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
