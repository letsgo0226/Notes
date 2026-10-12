# Trader_42 Binance Spot risk staging (2026-10-13)

Requested BTCUSDT-only Spot trading, per-order ceiling **50 USDT**,
and daily **realized-loss stop threshold 2 USDT**.

## Current state (intentionally no live orders)

This PR is a risk hardening proposal, **not** an activation.
`hsi_spot_risk.assert_live_release()` rejects all real order submissions,
even if Railway has `LIVE_ARMED=1` or `HSI_ORDER_KILL=0`.
No API key value is read by the CI tests and no order is posted.

The order creation code enforces BTCUSDT and an effective maximum notional
of `min(MAX_QUOTE_PER_ORDER, 50 USDT)`. If Railway is still set to the
old default 10, the effective limit remains 10, **not automatically 50**.
No Railway variables have been modified by this PR.

The existing code does not implement independently reconciled daily
realized PnL accounting. `evaluate_daily_loss` is a pure diagnostics
function; any unverified/missing record returns UNKNOWN_FAIL_CLOSED.
A passing diagnostic (less than 2 USDT previously realized loss)
**does not authorize** the next order. A position can lose more than 2 USDT
on a gap, fee, outage, or adverse execution. The requirement is a stop
threshold, not a loss guarantee.

Real-account verification requires a signed read-only Binance request
executed inside the configured service via the protected
`POST /orders/account-check` endpoint. Listing the environment variable
names is **not** verifying account permissions. Never paste credentials
into a chat or commit them. Do not execute `POST /orders/submit`.

## Auto Mode boundary

The proposed daily read-only Auto Mode workflow is not yet installed. Existing pull-request CI runs tests; local review output is available via `python3 -m hsi_spot_risk`.
It neither self-merges nor publishes unreviewed trading strategy code,
and cannot submit orders. Every strategy upgrade must pass independent
tests, risk review, and a human-controlled release. GitHub branch
protection/required checks should be enabled before promotion to live.

## Further prerequisites

* Broker-derived UTC realized-PnL ledger with every execution, fee asset,
  deposits/withdrawals and position opening-cost basis;
  detect and fail closed on external orders and stale/unknown history.
* Reconcile exchange order IDs and all fills after crashes, including
  uncertain POST attempts; enforce portfolio exposure and daily notional.
* Confirm verified account permissions and actual persisted journal mount.
* Confirm venue filters, minimum order notional and precision at order time.
* Establish strategy backtesting, out-of-sample evaluation and realistic
  execution/slippage tests before any controlled live release.
* Explicit user approval of the exact activation/deployment and of each
  code change which relaxes the hard release gate.

Reviewing or merging this risk PR **must never** be confused with
authorizing live trading.

## Finite offline UTC FIFO replay (not account reconciliation)

The proposed `hsi_spot_ledger.py` independently replays *supplied* BTCUSDT
fills against supplied opening FIFO inventory lots. Each sell's UTC-day
realized PnL is sale proceeds less matched BTC cost basis, net of fees in
USDT or BTC. Unsupported nonzero fees in BNB/other currencies, missing
cost basis, duplicate/unordered trades, stale timestamps and invalid
records produce `UNKNOWN_FAIL_CLOSED`. A day crossing the -2 USDT
threshold stays flagged, even if a later hypothetical sale recovers PnL.

Example with synthetic or offline-imported records, never with secrets:

```sh
python3 -m hsi_spot_risk --ledger-file path/to/local-fills.json
python3 -m unittest discover -s tests -p 'test_hsi_spot_ledger.py' -v
```

Schema: JSON object with UTC `utc_day` (YYYY-MM-DD), integer
`as_of_ms`, `observed_at_ms`, `opening_lots` (objects with decimal
string `quantity` and `cost_usdt`), and chronologically ordered
`fills` (objects with `trade_id`, `time_ms`, `symbol`,
`side`, `quantity`, `price`, `commission`, `commission_asset`).
All monetary and quantity values must be decimal strings. The local
report includes a reproducible SHA-256 of the supplied data, but **this
hash does not authenticate the data's Binance origin or completeness**.

A local fixture always reports `broker_reconciled=false` and
`live_order_permission=DENIED` irrespective of computed PnL.
The source history, fee conversions (including BNB), deposits,
transfers, manual trades, cost basis and latest fills must be verified
with the exchange before a separate operator-approved implementation
could ever rely on a daily loss gate. There is no such verified
implementation or live activation in this PR.

The existing Notes full-suite CI has a separate locked-source inventory
failure: the pinned count is 22 but new files under `Notes/` are
not included in the lock. Do **not** bypass or auto-approve that
check to promote this trading proposal.
