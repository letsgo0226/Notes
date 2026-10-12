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
