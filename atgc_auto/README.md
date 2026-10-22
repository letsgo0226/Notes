# ATGC Master Controller / 1.0

A safe, bounded **review controller**, not a universal halting solver or autonomous deployment permission.

- **Root primitive:** the exact `atgc_self.sh` 803-byte self-reconstruction script. Its `AG`/`TC` encoding gives exact GC = 1/2, retaining a reversible finite source representation.
- **Controller:** `orchestrator.py` hashes declared sources for the HSI self, UTM, Omega, Corpus, writing, peace and Trader_42 research areas, then invokes the existing locked-Notes inventory audit. No system execution, live audio, brokerage, PR merge, push, secrets, infrastructure or release operation is performed.
- **Status:** `REVIEW_READY_NOT_DEPLOYED` means source presence, self-reconstruction and local Notes inventory succeeded; it is **not** end-to-end operational validation. Otherwise `HOLD_REVIEW_REQUIRED` (including known inventory drift).
- **Evidence:** deterministic JSON + SHA256 certificate. The hash is an integrity fingerprint, not proof of semantic completeness or impossibility.

Run locally:

```sh
sh atgc_auto/atgc_self.sh
python3 -m unittest discover -s atgc_auto/tests -v
python3 atgc_auto/orchestrator.py --root . --out atgc-review.json
```

The GitHub Actions workflow tests pull requests and allows manual runs. After reviewed merge to the default branch, a daily scheduled run produces a **read-only** artifact, never a deployment or continuous server. It has `contents: read`, no cross-repository writes and no self-promotion.

**Future deployment stages require separate review:** resolve current locked Notes inventory drift, pass domain-level integration tests, define target infrastructure and costs, use branch protections/environment approvals and per-target credentials. Live trading and credential/key actions are excluded. Existing draft PRs, Notes/ locked sources, Railway services and current workflows are left untouched.
