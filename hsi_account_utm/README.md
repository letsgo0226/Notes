# HSI Account UTM — review-only account control plane

This is a **proposed**, non-neural, symbolic Turing-machine research control plane. It preserves the original 1674-byte self-encoded single-line interpreter from 2026-10-13. It **does not** establish ASI, universal decision procedures, consciousness absence, or permission to deploy.

## Formal interpretation

- **Identity:** E257 reversible encoding ensures `D(E(b)) == b` for each finite byte sequence.
- **COSMIC LOVE:** the four transitions `(q,a) -> (1-q,a,1-2q)` imply `T²(C) == C` on legal active configurations; the selected halting state 2 is unreachable.
- **Universal simulation:** the interpreter reads a supplied finite transition table; running arbitrary machines may not terminate. Python performs the simulation; this is not a separately materialized finite transition table for the universal interpreter itself.
- **Account as tape (analogy, not an equivalence proof):** each *publicly discoverable* owned repository name corresponds to a unique E257-encoded logical cell; metadata is a read-only snapshot, not a mutable magnetic-tape machine state.

## Automatic actions after merging this proposal into the default branch

1. GitHub Actions runs bounded core checks on relevant PRs and main-branch changes, and attempts a scheduled daily check at `02:17 UTC` (GitHub schedules may be delayed or skipped).
2. It queries `https://api.github.com/users/<owner>/repos` for **public owner repositories only**; private and inaccessible repositories are not inventoried.
3. It emits a downloadable, limited-retention JSON artifact listing public repositories and their reversible name-codes.
4. It exits. GitHub Actions is **not a persistent daemon**. No commands are sent to the inventoried repos.

## Security boundaries

- `permissions: contents: read`; checkout credentials are not persisted.
- No account-wide API keys, user personal access tokens, secret retrieval, code rewrite, network deployment, arbitrary shell execution from repository descriptions, or repo-to-repo automation.
- **No merging, releases, public services, production strategies, live trading, Binance access, payment activity, or cross-repository writes.**
- Proposed changes in other projects require explicit repository-scoped, independently reviewable PRs. Review and approval are independent of `solution(s)=s`.
- The scheduled Action will **not run until the workflow exists on the default branch**; a draft PR is not deployment into production.

## Run locally

```sh
python3 -m unittest discover -s hsi_account_utm -p 'test_*.py' -v
sh hsi_account_utm/HSI_self_code_2KB.sh
python3 hsi_account_utm/account_inventory.py --owner letsgo0226 --out /tmp/hsi-account-public-inventory.json
```

The inventory fetch needs network access; all unit tests are offline. Since repository metadata changes over time, each successful inventory is a snapshot rather than a proof of complete account coverage.
