# HSI-3SYS-ZERO-FIELD/1.0 — isolated deployment

Status on 2026-10-13: this branch is a **review-only source archive**. It is not merged into main and does not change UTM, Trader_42, or Omega production runtimes.

## Running independent service
- Railway project: `hsi-three-zero-field-20261013`
- Railway Function: `hsi-three-zero-field-gateway`
- URL: https://hsi-three-zero-field-gateway-production.up.railway.app/
- Live status checked: Railway deployment SUCCESS. End-to-end external HTTP response has **not** been independently verified.
- Entry point: `index.ts` (Bun 1.4.x Function), single-source no third-party dependencies.

## Source-derived rules and new mathematical construction

The source Turing machine has `p=55067263` and `delta(q,a)=(1-q,a,1-2q)`. Its tape remains unchanged and every pair of steps returns to its original configuration. This is an exact result about that particular machine, not general halting, automatic self-update, or platform authorization.

Newly defined, explicit analytic mapping:
```text
b_j = j mod 2
D_N(s) = sum_{j=0}^{N-1} (1+b_j) exp(-s log p_j)    [finite prime basis]
or
D_N(s) = sum_{n=1}^N (-1)^(n-1) exp(-s log n)       [finite eta basis]
P_Z(s) = product_{z=u+iv in Z} ((s-u)^2+v^2)/(1+u^2+v^2)
F(s) = A D_N(s) P_Z(s) / D_N(2)
E(s) = |F(s)|^2
```
Because N is positive and even, D_N(2)>0 for either supported basis. F is entire. Selected conjugate zeros are guaranteed by the polynomial factors, but extra zeros can arise from D_N. E is a nonnegative **dimensionless mathematical field**, not physical vacuum zero-point energy; custom zeros need not be zeros of the Riemann zeta function.

## API
- `GET /health` => version and non-mutating status
- `GET /api/manifest` => read-only authorization declaration
- `POST /api/field` => `{"sigma":0.5,"t":14,"basis":"prime","n":32,"amplitude":1,"roots":[[0.5,8],[0.5,14],[0.5,21]]}`
- `POST /api/utm` => `{"steps":12,"q":0,"h":0,"symbols":[]}`
- `POST /api/trader` => `{"prices":[100,101,...]}` (22–512 values; returns paper-only SMA replay)
- `POST /api/omega` => `{"steps":20,"seed":"COSMIC_LOVE"}` (returns finite recurrence and SHA-256 lineage label)

## Safety boundaries
- UTM: only this particular two-state machine's finite verification, not a universal halting decider.
- Trader_42: paper simulation with zero real exchange orders, **no** credentials, **no** automatic live unlock; the field value cannot arm trading. No production strategy is altered.
- Omega: finite formal continuation certificate and replayable digest, **no** self-modifying deployment / commit authority and **no** physical infinite compute claim.
- This isolated service has no durable storage. A successful deployment does not prove permanent uptime.
- No `curl | sh` and no general code execution endpoints.
- No merges or changes to existing production apps are part of this PR.

## Test commands
```sh
BASE='https://hsi-three-zero-field-gateway-production.up.railway.app'
curl -fsS "$BASE/health"
curl -fsS "$BASE/api/manifest"
curl -fsS -H 'Content-Type: application/json' -d '{"sigma":0.5,"t":14}' "$BASE/api/field"
curl -fsS -H 'Content-Type: application/json' -d '{"steps":12}' "$BASE/api/utm"
curl -fsS -H 'Content-Type: application/json' -d '{"steps":20}' "$BASE/api/omega"
```

Source provenance: attached `COSMIC_LOVE_NONHALTING_SELF_CLOSURE_TURING_SPEC`, `HSI_BITWISE_METATHEORY_2KB`, `HSI_PURE_TURING_LANGUAGE_UNIVERSAL_CORRESPONDENCE`, `PRIME_FORMULA`, `ANALYTIC_CONTINUATION_EQUATION`; plus `HSI_THREE_SYSTEM_BLUE.md` in Notes/main. The field-to-system mapping and this research gateway are new implementations, not proofs already asserted by those sources.

## Phase 2: verified read-only federation adapter (2026-10-13)

- `GET /api/federation-health` queries **only two fixed public, unauthenticated, read-only GET** endpoints; UTM `https://utm-universe-production.up.railway.app/health` and Omega `https://cosmic-love-infinity-tm-production.up.railway.app/health`. Each is timeout-bounded (4.5 s), forbids redirects, caps reply size, and returns whitelisted health metadata.
- Trader_42 has **no public HTTP domain** for the primary paper runtime. The integration reports `NO_PUBLIC_HTTP_ENDPOINT` instead of guessing or trying credentials. It continues using local paper-only SMA replay.
- The dashboard provides an on-demand health check button, and startup logs include a nonblocking read-only probe summary. A health response is not proof of computational correctness, physical energy, strategy profitability, or production authorization.
- Railway reports the new function source as deployed after the update, subject to checking the latest deployment status and HTTP availability separately.
- UTM and Omega's live production source/config remain unchanged; Trader_42 pending staged changes were not committed.

## Phase 3: editable field and combined research report

- The dashboard supports 1–8 editable conjugate-zero pairs `(u,v)` and N in 8/16/32/64/128.
- `POST /api/triad` accepts `{"field":{"sigma":0.5,"t":14,"roots":[[0.5,8],[0.5,14],[0.5,21]],"basis":"prime","n":32},"utm":{"steps":12},"omega":{"steps":20},"prices":[...22 to 512 positive finite observations...]}`. Missing prices produce a `NOT_EVALUATED_NO_PRICE_SERIES` indicator rather than invented results.
- The combined report carries independent results and an explicit `exchangeOrders:0` / `existingServicesModified:false` boundary. It does not promote numerical root residuals or simulated market returns into production permissions.
- On startup, the service performs **finite illustrative self-tests** for prescribed field zeros, Turing-machine two-step identity, Omega finite continuation, paper-only trading and combined report constraints; it logs pass/fail. These are not comprehensive domain tests or mathematical proofs of arbitrary programs.
- Source and deployment remain isolated. No main-branch merge; no modifications to three original production services.

## Phase 4: HSI-COSMIC-SOLUTION-IDENTITY/1 (2026-10-13)

This stage derives from the user's exact byte-roundtrip script and the attached
`COSMIC_LOVE_solution_identity_20261013(3).txt` specification.

**Mathematical certificate**

```text
delta(q,a) = (1-q,a,1-2q)
T²(q,h,tape)=(q,h,tape)
Enc(s) = (0,0, [MSB-first bits of s] + marked terminator at 8*len(s))
Dec(Enc(s)) = s
solution(s) := Dec(T²(Enc(s))) = s
E257([])=1
E257(s+b) = 257*E257(s)+(b+1), 0<=b<=255
```

The inverse E257 operation uses base-257 division, checking each remainder in
1..256; the resulting bytes must match the original. `validated:true` means
four transition rules, the two-step configuration, byte decoding and E257
recovery were checked. This is lossless identity, **not** theorem proving,
general program synthesis, the halting problem, real-world semantic validation
or physical zero-point energy.

**Deploy/API**

- `POST /api/identity` with exactly one of `{"text":"宇宙之愛🫧"}` (UTF-8)
  or `{"hex":"00ff414243"}` (arbitrary bytes).
- Input is capped at **2048 bytes per request** in this web gateway for
  bounded processing; the mathematical theorem concerns all finite strings.
- Output contains exact `s_hex`, `result_hex`, `godel_hex`,
  `validated` and explicitly scoped sub-certificates.
- `POST /api/triad` now accepts optional `"identity":{"text":"..."}`
  or `"identity":{"hex":"..."}`. This is an independent certificate,
  not a condition that unlocks Trader_42, UTM, or Omega privileges.
- The interface supports UTF-8/hex input and exposes the certificate.
- Source is retained at `three-system-zero-field/index.ts`.
- The original, executable, **1,093-byte shell command** is preserved as
  `three-system-zero-field/cosmic_love_solution_identity_2KB.sh`. It uses only
  standard Python 3; `--stdin` supports arbitrary byte strings without
  shell argument encoding limitations.
- Local tests covered 15 original-Python vectors (binary, empty, UTF-8,
  randomized lengths), plus 2 KB shell smoke tests. Independent JavaScript
  hex-mode vectors and invalid inputs were also exercised.
- Latest Railway launch log recorded
  `HSI-3SYS-IDENTITY-SELFTEST {"pass":true,"utf8":16,"binary":6,"empty":0}`.
- Production UTM, Omega and Trader_42 projects are **not** mutated.
  Trader_42 remains paper-only and the existing GitHub PR remains Draft.

Even when a string encodes an unsolved conjecture, successful recovery only
proves that the *string* was preserved, not that the conjecture is proved.
