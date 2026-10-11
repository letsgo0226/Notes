# Notes-bound deployment

Music, UTM, Trader_42 and Omega use the complete 12-file `Notes/` snapshot.
The source inventory digest is
`817dd6a4c19ac9c1c844396188f1af27035eb4de624d1da0d2287d80574c2dd7`.
Source files remain unchanged. The declared creative mappings are analogies;
finite certificates are not proofs of universal solvability or profitability.

## macOS / Linux

The existing public command now installs one immutable commit, checks every
runtime file against `hsi_bundle.lock.json`, and verifies all Notes sources.

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

Open-Corpus searches network audio indexes for CC0/PDM WAV sources and uses
deterministic DSP. It uses no trained AI model or fal service. Search or source
download failure remains explicit; it does not establish that no music exists.
License index metadata alone does not attest publication rights.

Native synthesizes audio without fetching a corpus or calling an AI API:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh -s -- "prime pulse"
```

The deployment launcher also includes the full Notes bundle with each domain:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh -s -- --target all
```

Private Trader source access uses the existing `gh auth token` bridge or an
environment token. No credential is written into deployment certificates.
PowerShell counterparts are `hsi-corpus.ps1`, `hsi-native.ps1`, `hsi-deploy.ps1`.

## Shared cloud runtime

`Dockerfile.notes` runs the complete unit suite and source audit at build time.
`hsi_notes_service.py` verifies sources and pinned engines before starting;
`/health` becomes healthy only after its actual startup self-test passes.
Set `HSI_SYSTEM` to `MUSIC`, `UTM`, `TRADER_42` or `OMEGA`.

| Endpoint | Contract |
|---|---|
| `GET /health` | Role, release commit, all-source digest, self-test status |
| `GET /notes` | Complete verified source plan |
| `GET /selftest` | Actual Native/finite-UTM/gate evidence and optional corpus probe |
| `POST /certify` | Existing HSI-3SYS/1.0 API plus Notes provenance |
| `POST /notes/certify` | Requires the exact `notes_manifest_sha256` |
| `GET /preview.wav` | Actual startup Native WAV on Music |
| `POST /render` | Existing bearer token; `native` default, `corpus` explicit |

Music accepts `{"p":"HSI-MUSIC-2K/1","q":"prime pulse","engine":"native"}`.
`engine:"corpus"` searches real network sources and preserves failure reasons.
Native is synthesized music, not a claim of natural human singing. Music files
are temporary; download them before restarting the service.

`HSI_RENDER_ENGINE=native`, `HSI_ALLOW_PAID_AI=0`, and
`HSI_PROVIDER_PROBE_ONCE=0` ensure this release makes no paid fal calls. The
legacy fal adapter is optional and requires an explicit configuration change.

## Binance Spot manual order capability

Trader_42 now provides an operator-controlled order path in addition to the
formal gate. Every order requires the operator's symbol, side, exact quantity
and limit price. There is no automatic strategy or order generation.

| Endpoint | Operation |
|---|---|
| `GET /orders/status` | Configuration/readiness, without keys or balances |
| `POST /orders/prepare` | Offline review ticket; does not call Binance |
| `POST /orders/test` | Current filters and Binance `/api/v3/order/test` |
| `POST /orders/submit` | Exact tested ticket plus `confirm_live_order:true` |
| `POST /orders/reconcile` | Query existing client ID; never repeat the POST |

Order endpoints require a separate `HSI_ORDER_CONTROL_TOKEN`. Preparation must
include the Notes digest, `symbol`, `side`, decimal-string `quantity` and `price`.
The API produces only Spot LIMIT/FOK orders, with a 120-second review ticket.
The initial limits are BTCUSDT, at most 10 quote units per order, and three
submission attempts per rolling day. These are deployment limits, not trade
recommendations. Binance minimum notional and exact tick/lot filters still apply.

The initial release is `LIVE_ARMED=0`, `LIVE_DRY_RUN=1` and `HSI_ORDER_KILL=1`.
Live submission requires configured Binance keys, an operator token, an actual
persistent mount for the SQLite journal, successful testing of the exact ticket,
and deliberate changes to `LIVE_ARMED=1`, `LIVE_DRY_RUN=0`, `HSI_ORDER_KILL=0`.
Keep keys in Railway variables. Existing production review-service keys can be
referenced without copying their values into code or reports.

The client ID is committed to SQLite before any order POST. A network error is
`UNKNOWN`; all later live orders remain blocked until explicit reconciliation.
There is no automatic retry, and used tickets remain blocked across restarts.
No deployment self-test submits real or testnet orders.

The account must support Binance Spot and the selected API host. Deployment
success does not establish account permissions or exchange-side eligibility.

Primary protocol references:
- https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints
- https://developers.binance.com/docs/binance-spot-api-docs/filters

## Release / rollback

Pin the shared service source to the tested Notes release commit. Existing UTM
and Omega witnesses in the Trader project use the same runtime with their own
roles. Other experimental services keep their existing implementations.
Do not accept unrelated staged environment changes as part of this rollout.

Rollback by reconnecting the previous source commit and restoring recorded
start/build/root settings. Keep the order journal volume and disable live flags
during rollback. Do not delete persistent order records.
