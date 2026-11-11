# COSMIC_LOVE Trading Protocol (CLTP) — OFFLINE research only

**Not a trading bot or live strategy.** The P = 55067263 two-state,
two-symbol Turing machine is a **clock** that alternates two stages of a
finite decision procedure. It is not a source of market information and
cannot confer positive expected returns. This research version contains no
Binance SDK, no broker endpoint, no network request, no secrets and no live
order permission. It is deliberately separate from Trader_42 PR #27 and
from the already-running independent COSMIC_LOVE heartbeat service.

## Reproduce locally

Python 3.11+ standard library only, in the repository root:

```sh
python3 research/cltp/cltp.py --csv research/cltp/examples/synthetic_btcusdt_candles.csv
python3 -m unittest discover -s tests -p 'test_cltp_offline.py' -v
```

The fixture is **artificial prices**, not Binance BTCUSDT history. Output is
JSON and includes synthetic decisions, approximate simulated fills, fees,
realized/unrealized equity estimates and a list of simulated UTC loss-stop
dates. Do **not** treat sample profits or losses as investment evidence.

Input CSV headers, in exact order: `timestamp,open,close`. `timestamp`
identifies the candle **open** in UTC (`YYYY-MM-DDTHH:MM:SSZ`); the candle
`close` is only considered available **after that candle finishes**.
The program assumes ordered, non-overlapping completed candles. These
assumptions are not independently validated from CSV alone; gaps, revisions,
nonuniform bar duration, and bid/ask spreads must be evaluated with a real
licensed historical market-data source in any future research. The file is
bounded at 2 MB and 20,000 rows. No CSV is fetched automatically.

## Formal control analogy

The user's Turing-machine decoding is checked exactly, with rule

```
delta(q,a) = (1-q, a, 1-2q)
```

For each closed candle, this paper strategy advances **exactly one** TM step.
The oscillator alternates:

- `q=0` (OBSERVE): calculate a candidate BUY, SELL or HOLD from **past and
  just-completed** closing prices; take **no** trading action.
- `q=1` (VERIFY): compute the same independent signal on the next completed
  candle, requiring **the two consecutive signals** agree. If non-HOLD and
  consistent, schedule a simulated order for the **following candle's open**.
- After two steps, `F²=I` resets the computation clock, **not** the
  financial ledger, exposure, account equity, or irreversible market trades.

The deliberately *unoptimized* illustrative signal is a 3-close SMA:

```
BUY  if close < 0.99 * SMA3
SELL if close > 1.01 * SMA3
HOLD otherwise
```

It is a falsifiable mean-reversion hypothesis, **not** a consequence of the
Turing-machine mathematics. No tuning or out-of-sample performance claim is
made. Alternative hypotheses need preregistered independent validation.

## Synthetic execution and risk assumptions

| Assumption | Offline-only value |
|---|---:|
| Market symbol | BTCUSDT |
| Starting paper cash | 250 USDT |
| Max total quote per simulated BUY (including fee) | 50 USDT |
| Max quote value per simulated SELL | 50 USDT |
| Simulated opening BTC inventory budget | 50 USDT marked at candidate entry price |
| USDT-denominated fee on each synthetic fill | 10 bps |
| Adverse slippage on each synthetic fill | 5 bps |
| UTC realized-loss day stop threshold | −2 USDT |

The stop uses synthetic FIFO cost basis and quote-asset fees. Crossing the
threshold prevents **subsequent** simulated fills on that UTC calendar day;
it does **not** cap the triggering loss, unrealized losses or overnight gaps.
Position mark value can exceed the entry budget after price changes. The
simulation assumes next-open liquidity for every order; that is not a
realistic guarantee. Binance lot/tick/min-notional requirements, different
fee assets such as BNB, transfers, taxes, partial FOK failures, latency,
rate limits, reliability, and all actual broker reconciliation are **out of
scope**.

## Evidence needed before any real-money discussion

1. Independently sourced, integrity-checked **historical** BTCUSDT candles
   with explicit bar-close availability, sample period and missing-data audit.
2. A preregistered protocol and untouched holdout test; compare against
   no-trade, buy-and-hold and other simpler controls; report sensitivity to
   fees, slippage, spread, gap loss and adverse market regimes.
3. Independently reconciled complete Binance Spot positions, trade history,
   deposits, transfers, all fee currencies and opening FIFO cost basis.
4. Review and test execution-layer kill switches, fail-closed behavior under
   API outages/restarts, and separate **explicit human approval** of any
   production release or trade. The 2 USDT number is a threshold, not a
   guarantee of a maximum possible loss.

CLTP does not add an HTTP route or modify existing Trader_42/Binance files.
PR review and GitHub CI **must not** be mistaken for a deployed or proven
live strategy. In particular, `live_order_permission` always equals `DENIED`
and `broker_calls` and `real_orders` remain zero.
