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

## Optional authenticated Binance signed-GET audit (NOT enabled)

`hsi_binance_readonly_audit.py` defines a finite, private, signed-GET-only
account snapshot. A protected service route
`POST /orders/history-audit` (the **HTTP** request method; the broker
requests themselves are GET only) will be available only after the
reviewed code is separately deployed. It accepts a JSON body containing
`notes_manifest_sha256` and `acknowledge_read_only: true`, plus the
existing `Authorization: Bearer ...` control token header.

The service **must** be in safe standby
`LIVE_ARMED=0`, `LIVE_DRY_RUN=1`, `HSI_ORDER_KILL=1`.
Even then, no Binance queries are performed unless
`HSI_READONLY_HISTORY_AUDIT_ENABLED=1` is separately configured.
This flag is deliberately **not** set or deployed by this PR.
Do not add any key to GitHub and never paste secrets in a chat.

With all conditions satisfied and explicit operator invocation, the
finite snapshot uses exactly four signed GET operations:

1. `/api/v3/account` (account type and BTC-inventory presence only).
2. `/sapi/v1/account/apiRestrictions` (API-key Spot permission flag).
3. `/api/v3/openOrders?symbol=BTCUSDT` (only an open-order count).
4. `/api/v3/myTrades`, bounded from UTC midnight to the snapshot time
   and at most 1,000 fills (a full page is rejected as possibly truncated).

The returned report is a **redacted summary**: no API keys, balances,
UIDs or raw fills. Read errors, unsupported response shapes, possible
pagination truncation or incomplete data yield `UNKNOWN_FAIL_CLOSED`.
Even a successful 4-GET snapshot reports
`READ_ONLY_SNAPSHOT_UNVERIFIED`, `broker_reconciled=false`,
`daily_pnl_verified=false` and `live_order_permission=DENIED`.

A single-day query does not validate all trade history, opening cost
basis, internal transfers, BNB fee conversion, external manual trades
outside BTCUSDT or live exposure. Those gaps still require a
separate audited reconciliation ledger. As a result, this read-only
snapshot **cannot** enforce or certify the 2 USDT stop and never
activates trading.

Binance docs: https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/account

## Offline comparison of two redacted evidence summaries

`hsi_spot_trade_digest.py` defines a canonical decimal-preserving
fingerprint scheme used by both the supplied FIFO fixture and the
signed-GET audit summary. `hsi_spot_reconcile.py` can compare the
resulting JSON *on the user's own machine* (do not upload keys, balances,
or raw fill history):

```sh
python3 -m hsi_spot_ledger --input local-btcusdt-fixture.json > local-ledger-report.json
python3 -m hsi_spot_reconcile --snapshot local-readonly-snapshot.json --ledger-report local-ledger-report.json
```

This comparison checks the UTC day, exactly identical snapshot clock,
trade count, BUY/SELL counts, complete supplied window, decimal-preserving
SHA-256 fingerprint, disallowed commissions, unexpected open orders and
disabled API trading permission. Tampering or mismatching input produces
`UNKNOWN_FAIL_CLOSED`.

Even when it finds agreement, the only possible positive status is
`BOUNDED_DIGEST_MATCH_ONLY_NOT_RECONCILED` with
`broker_reconciled=false`, `daily_pnl_verified=false`,
`exchange_origin_authenticated_by_this_file=false` and
`live_order_permission=DENIED`. A SHA-256 digest is **not** a
signature or proof that the data was genuinely issued by Binance.
There is still no verified opening cost basis, all-symbol activity,
transfers or continuous signed account-history coverage. The genuine
daily realized-loss stop remains a required future implementation,
not a deployed protection. The 2 USDT threshold cannot guarantee
that realized or unrealized losses will stay within 2 USDT.

Read-only audit is deliberately opt-in and **not deployed**. The user's
Railway service remains in safe standby; PR #27 stays draft and cannot
unlock live order submission via environment variables.
