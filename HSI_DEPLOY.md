# HSI Deployment Solver / 1.0

`HSI-DEPLOY/1.0` makes deployment itself an HSI finite-resolution problem.

The deployment pipeline is:

```text
OBSERVE
  ↓
RESOLVE immutable Git commits
  ↓
VERIFY source + policy invariants
  ↓
COMMIT or HOLD
```

A failed source resolution or verification does not partially deploy the remaining targets.

## Targets

The default `all` deployment contains:

```text
self       = HSI core
utm        = UTM HSI Blue gate
trader_42  = Trader_42 certificate-only gate
omega      = Omega / Cosmic Love HSI Blue gate
```

The HSI core release contains:

```text
hsi_net.py
hsi_search.py
hsi_open_corpus.py
hsi_native_renderer.py
hsi_update.py
hsi_deploy.py
```

Each of the three domain systems contains its pinned `core.py` and `hsi_blue_native.py`.

## HSI NET source projection

Deployment source resolution uses:

```text
HSI-NET-SINGULARITY/1.0
adapter = github_source
```

A mutable branch name is first resolved to an immutable 40-character Git commit SHA. Files are then downloaded from the commit-addressed raw URL and recorded with SHA-256 and Git blob SHA-1 in the deployment certificate.

The protocol does not claim that a GitHub repository or branch is exhaustive of reality.

## Safety invariants

```text
partial source resolution never commits
private source without auth never commits
credentials are never written to certificates
verification failure never commits
deployment does not imply domain execution
Trader live authority = false
Trader order submission = false
UTM universal halting authority = false
Omega forced-commit authority = false
```

For Trader_42 the deployer verifies that the installed public gate still contains:

```text
CERTIFICATE_ONLY
dry_run = true
live_armed = false
credentials_used = false
order_submission = false
may_authorize_trade = false
```

Deploying Trader_42 therefore installs only the existing safe certificate gate; it does not authorize real-money trading.

## Output

Default root:

```text
~/.hsi/
```

Structure:

```text
~/.hsi/
├── current.json
├── hsi.py
├── hsi
├── hsi.cmd
├── releases/
│   └── <release-id>/
│       ├── self/
│       ├── utm/
│       ├── trader_42/
│       └── omega/
└── state/
    └── deployments/
        ├── *.lock.json
        └── *.hsicert
```

Every release is immutable. A new deployment creates a new release directory and atomically updates `current.json`.

## Public launch

### iSH / macOS / Linux / Termux

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh
```

iSH may use:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh
```

Default behavior attempts all four targets.

`Trader_42.sh` is currently private. Therefore an all-target deployment requires GitHub authentication that can read that repository. If no such credential is available, HSI returns `HOLD / AUTH_REQUIRED`; it does not reinterpret GitHub's unauthenticated 404 as proof that the branch does not exist.

The bootstrap checks, in order:

```text
GITHUB_TOKEN
GH_TOKEN
gh auth token   (only when GitHub CLI is already installed and authenticated)
```

A token obtained from `gh auth token` is exported only to the current deployment process. The deployment certificate never records the credential.

To authenticate with GitHub CLI beforehand:

```sh
gh auth login
```

Or explicitly provide a token with access to the private Trader repository:

```sh
GITHUB_TOKEN="..." curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh
```

Do not paste that token into logs or commit it to a repository.

Plan only:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh -s -- --plan
```

One target:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh -s -- --target utm
```

Multiple targets:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.sh | sh -s -- --target self --target trader_42
```

### Windows PowerShell

```powershell
$p = Join-Path $env:TEMP "hsi-deploy.ps1"; Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-deploy.ps1" -OutFile $p; & $p
```

Plan only:

```powershell
& $p --plan
```

## Unified local invocation

After deployment:

```sh
python3 ~/.hsi/hsi.py net --list-adapters
python3 ~/.hsi/hsi.py search "Blue Pleiadian Stars"
python3 ~/.hsi/hsi.py corpus "Blue Pleiadian Stars"
python3 ~/.hsi/hsi.py native "Blue Pleiadian Stars"
python3 ~/.hsi/hsi.py update ~/Music/HSI-Corpus/<artifact-directory>
python3 ~/.hsi/hsi.py utm "finite computation context"
python3 ~/.hsi/hsi.py trader "market context"
python3 ~/.hsi/hsi.py omega "finite continuation context"
```

On Windows, use `py -3` or `python` instead of `python3` as appropriate.

The dispatcher only invokes targets that exist in the current committed release.
