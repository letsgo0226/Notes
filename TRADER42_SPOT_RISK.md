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

`.github/workflows/trader42_spot_auto_review.yml` runs regression tests
and emits a finite review-only JSON risk report on PR / manually / daily.
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
