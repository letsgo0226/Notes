# Cosmic Love — independent deployment controller

This code is on a branch created from `main`, **not** on candidate PR #29.
It independently inspects the live GitHub PR/commit, exact SHA's successful
CI, allowed changed paths, and re-checks the HSI-ST/1 finite transition
theorem. It never invokes a cloud deployment API and has no write token.

Usage:

```bash
python3 -m unittest cosmic_love_controller.test_controller -v
GITHUB_TOKEN=<READ_ONLY_TOKEN> python3 cosmic_love_controller/controller.py --candidate-sha <EXACT_40_HEX_SHA>
```

Success returns `CANARY_ELIGIBLE_NOT_DEPLOYED`. Even if a JSON input
claims a backup exists, `promote` fails closed until there is a separately
attested **actual** Railway-volume export, recovery drill and rollback.

Read `CONTROLLER_TURING_SPEC.txt`. No live trading, main merge, customer
chat ingestion, auto-promote or production deploy is enabled.
