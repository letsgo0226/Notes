# Trader_42 — isolated paper-only risk prototype

**Status:** draft research prototype, not the existing Trader_42 trading system and not a live brokerage integration.

This folder contains a deterministic offline simulation ledger. Input is local JSON with explicit BUY, SELL and MARK actions. It does **not** discover prices, execute orders, connect to any exchange, use real funds or maintain durable state. Default limits: 10,000 virtual cash, 500 virtual currency units per order, 10 asset units maximum position, 100 virtual units maximum marked loss, and 0.1% simulated fees.

Example:

```json
{"actions":[{"kind":"BUY","price":"100","qty":"1"},{"kind":"MARK","price":"101"},{"kind":"SELL","price":"101","qty":"1"}]}
```

```sh
python3 -m unittest trader42_paper.test_engine -v
python3 trader42_paper/engine.py --input sample.json
```

No live-order permission is provided by the user's parallel-development authorization. The simulation is not a predictive or profitable trading strategy. The daily-loss guard is a **single-session mark-based halt**, not a calendar-day reset, exchange stop order, or guarantee against slippage. Prices must be independently supplied; results depend entirely on the supplied hypothetical path. This cannot establish real-market readiness.

**Parallel-work isolation:** Cosmic Love's staging deploy credentials, candidate code and proof tokens MUST NOT become broker permissions. Live trading requires a separate explicit authorization, strategy-specific tests, exchange restrictions, and maximum-loss controls. Do not store API secrets in GitHub.
