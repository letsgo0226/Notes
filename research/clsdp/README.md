# CLSDP — Computable Reasoning Closure Standard

**Research-only, draft PR. Does not unlock live trading.**

CLSDP formalizes the distinction between a computable and internally
consistent self-assessment and an independently justified, authorized
financial action. An assurance system can *evaluate* its own completeness
without acquiring the authority to certify itself.

The mathematical oscillator P=55067263 guarantees the two-state transition
F²=I. That claim is about an internal Turing machine. Its result does not
prove BTC price prediction, profitable trading, broker position completeness
or production deployment safety.

## Formal scope

Let E_t be a finite set of evidence claims, R_t a research output, and A_t
the genuine external authority for a specific scope of live orders.

    E_{t+1} = gather_public_history_and_test(E_t)
    R_{t+1} = review_claims(E_{t+1})
    permitted_trade = independently_verified_policy AND
                      current_broker_reconciliation AND
                      separate_explicit_human_release

In this branch none of the last three terms can be established. Therefore:

    FOR ALL E_t: CLSDP(E_t).live_order_permission == DENIED
    FOR ALL E_t: CLSDP(E_t).can_grant_order_permission == False

That is a real code invariant, with adversarial synthetic unit tests. It
does **not** mean that every possible real-world market risk is decidable.
A consistency or checksum proof alone cannot authenticate its own input.

## Twelve mandatory classes of evidence

1. Independent public-market historical data integrity.
2. Chronological no-lookahead / next-open execution evidence.
3. Preregistered holdout and independent benchmark comparison.
4. Sensitivity to fees, slippage and gap/market-regime stress.
5. Real Binance symbol filters and every fee-asset valuation.
6. Complete exchange positions and all open orders.
7. Historical opening cost basis, transfers and externally placed fills.
8. Independently audited UTC daily realized-loss stop and persistent latch.
9. Duplicate-order prevention, network uncertainty and restart recovery.
10. Credential privilege separation and independently tested kill switch.
11. Immutable reviewed program release and artifact provenance.
12. Separate explicit human authorization for a precisely scoped live release.

A JSON file may claim every condition is PASS, but a claimed issuer name and
SHA-256 do not establish independent attestation. The best result such a file
may earn is SELF_ASSERTED_COMPLETE_NEEDS_INDEPENDENT_REVIEW, never a trading
permission. Any absent, failed or stale required gate is REVIEW_BLOCKED.

The closure-check CLI intentionally returns **exit code 1 even if all 12
self-declared items are PASS**, because this is only an independently
reviewable candidate. Invalid or malformed input exits 2. There is no
success-style zero exit code that downstream automation may misuse as
permission to enable live trading.

The profile is fixed: Binance Spot BTCUSDT, <=50 USDT per proposed order and a
2 USDT UTC daily realized-loss stop threshold. That threshold cannot prevent
the *triggering* market loss exceeding 2 USDT. Neither raising limits nor
enabling order execution is representable in this module.

## Public-history research and safe future automation

The proposed weekly pipeline runs in THREE separate GitHub Actions jobs:

- Unit tests: fully offline, read-only GitHub token.
- Public-history research: only Binance's keyless HTTPS market data GET
  endpoint at data-api.binance.vision/api/v3/klines; 720 hourly completed
  candles, one-hour extra completion margin, strict contiguous UTC times
  and OHLC validity. No API secrets, no signed requests, no broker accounts.
- Draft-only report proposal: a distinct job with GitHub contents+PR write
  permission. It downloads the public research artifact, rejects all claims
  of live authorization, writes ONLY a new research memo to a new branch,
  and requests a **draft PR**. It NEVER merges, deploys, sets environment
  variables, handles exchange permissions or submits an order.

Failure in any dependency prevents a new PR. If public API data are
missing, stale, malformed, duplicated or incomplete, there is no fallback to
synthetic data and no fabricated "historical result". Research assets expire
from GitHub Actions artifacts after 14 days; the proposed PR memo is kept
for human review. Any real API usage is subject to endpoint availability
and rate limits.

The fixed CLTP rule uses a 3-hour close moving average, a consecutive
two-bar confirmation, and a synthetic next-hour open fill; compare
development (70%), holdout (30%), zero-trading, small buy-and-hold, and
two artificial 20% gap stress cases. This is illustrative evaluation only,
NOT a trained/optimized strategy and NOT evidence of statistical alpha.
Cost and fill assumptions remain simplified.

Run locally with Python 3.11+:

    python3 -m unittest discover -s tests -p 'test_clsdp_*.py' -v

The real public-data fetch command below is optional and DOES access a
nonprivate Binance market-data endpoint:

    python3 research/clsdp/run_research.py --out-dir clsdp-output

Inspect a local synthetic evidence-package JSON:

    python3 research/clsdp/closure_standard.py --input evidence.json

No evidence package can grant an order.

## Activation status of proposed GitHub Actions

The workflow declares a weekly Monday 02:25 UTC schedule and a manual
workflow_dispatch entry. GitHub scheduled workflows run from the DEFAULT
branch only; this branch remains a draft and no automatic schedule has been
enabled on main. The GitHub repository must also allow GitHub Actions to
create pull requests for the draft-proposal job to succeed. The workflow
does not attempt to change those repository settings.

Crucially, enabling **research automation** is different from enabling
**broker execution**. Nothing in CLSDP can toggle LIVE_ARMED, LIVE_DRY_RUN,
HSI_ORDER_KILL, merge a strategy PR, operate Binance credentials, or turn
a successful backtest into a production release.

Trader_42 draft PR #27 remains separately blocked. CLTP draft PR #30 is
the explicit research-code dependency of this new proposal. Do not merge
or deploy any code based on automatic checks without separate review.
