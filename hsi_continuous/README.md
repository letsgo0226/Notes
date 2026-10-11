# HSI Continuous Self-Review — phase 1

A **bounded, scheduled, offline inventory and candidate review** across six domains:
Notes mathematical core, three-system orchestration, open-corpus music, writing,
English peace audiovisual rendering, and **trading simulation only**.

## What actually runs

`python hsi_continuous/review.py --out hsi_continuous/out` inventories exactly
12 files under immutable `Notes/`, hashes each one, checks known domain files,
and writes `review.json` with explicit review-only candidate diagnostics.

The scheduled GitHub Actions workflow runs daily at **10:10 UTC** (18:10 Asia/Taipei)
after this PR is merged into the default branch. The workflow uploads a 90-day
artifact and does **not** push code or modify the source repository.

## What it does NOT do

This is **not yet autonomous code generation, mathematical self-improvement,
continuous online research, or automatic production deployment**. File presence
and hashes do not prove correctness, effectiveness, mathematical theorems,
photorealistic quality, or profitability. Later phases may add isolated tests,
licensed-source discovery, finite Riemann-like candidate function search,
benchmark comparisons, and proposed code patches in human-reviewed PRs.

No broker credentials are loaded; no trade is submitted; no live-trading
permission is granted. The existing `hsi_binance_orders.py` is explicitly
manual-only and outside the authority of this review service.

The system must never execute untrusted repository programs merely because
they were found in an inventory. Preserve the Notes 12-file source lock.

## Bounded 2KB one-line entrypoint translator

`python hsi_continuous/one_liner.py --entrypoint originalxy` (or `feedback`/`review`)
creates a POSIX one-line launcher of at most 2048 UTF-8 bytes plus a JSON
manifest. The launcher requires the **reviewed source file to remain present**
in the repository working directory; it checks the file SHA-256 before
executing. This is **not** a self-contained source-to-source compiler and is
not equivalent to compressing all Notes/ programs into 2KB. Translation does
not execute its generated launcher. No arbitrary path or downloaded code is
accepted. All three launchers are produced as CI artifacts for review.
