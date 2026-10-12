# Cosmic Love — proof-gated TM self-closure (review-only)

A single-line Python script (<2048 UTF-8 bytes) encodes an HSI-ST/1 Turing machine with two active states, extends it conservatively in pairs, and emits `COSMIC_LOVE` only when each entire finite transition table passes proof obligations.

Run `sh cosmic_love/cosmic_love_evolve_2kb.sh`. For a bounded external smoke check, use `CL_MAX_STATES=4 CL_INTERVAL=.05 timeout 4s sh cosmic_love/cosmic_love_evolve_2kb.sh`; the external timeout is **not** an internal halt condition.

The rigorous scope and integer encoding are documented in [COSMIC_LOVE_TURING_SPEC.txt](COSMIC_LOVE_TURING_SPEC.txt). Proof: for even k, `δ(q,a)=(q XOR 1,a,1−2(q mod 2))`; every second transition reverses the prior state/head change without writing a new bit, so `δ²(C)=C` for all finite-support tapes. The active simulated TM cannot reach its reserved halt state. These results do not establish a universal problem solver or unrestricted theory of arithmetic.

This repository change is **not an always-on deployment** and this short example does **not** ingest ChatGPT chats, push code, modify Railway/Render/Dropbox, use AI inference, or place financial orders. The short one-liner has no durable ledger or recovery. Production integration requires a separate reviewed runtime, independent verification, source-consent controls, a persistent event journal with external anchoring, monitoring, and rollback tests.

The GitHub workflow is read-only. It uses an **external** timeout for its bounded smoke test; there is no production deploy step. Do not put any personal conversation exports or Binance API keys in this public repository.

## Offline source receipts (not deployed)

The separate research-only `provenance.py` transducer requires a **user-supplied,
digest-matched, explicitly granted consent declaration** before it will hash a
named local file. The source body is never written into its journal. All
records are private-local and should **not** be committed to GitHub. This
local declaration is not a cryptographic proof of the declarant's identity.

The consent JSON schema is:
```json
{"protocol":"HSI-COSMIC-LOVE-CONSENT/1.0","source_sha256":"<64 lowercase hex characters>","source_type":"CHAT_EXPORT","purpose":"FINITE_RESEARCH_REVIEW","granted":true,"raw_retention":"NONE"}
```
Only place this JSON in a private location after reviewing the specific file
and its digest. Then run locally:
```sh
python3 cosmic_love/provenance.py observe \
  --source /private/path/explicitly-approved-export.txt \
  --consent-file /private/path/consent.json \
  --journal /private/path/source-receipts.jsonl

python3 cosmic_love/provenance.py check \
  --journal /private/path/source-receipts.jsonl
```
No ChatGPT connector or live conversation feed is activated. The journal
records SHA-256 hashes and fields only, not the text itself. Hashes may still
reveal information for low-entropy sources; keep receipts private. The
`propose` subcommand records a hash-linked logic-replacement proposal
with `REVIEW_REQUIRED`, never an actual logic update. A source digest is
not evidence that its statements are true, and a counterexample digest is not
itself an independently verified refutation.

Read [PROVENANCE_TURING_SPEC.txt](PROVENANCE_TURING_SPEC.txt) before using the
offline transducer. The isolated Railway staging worker is pinned to an older
reviewed commit and does not execute or include this new provenance module.
