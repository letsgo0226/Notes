# HSI SOLVE / 1.0

Protocol: HSI-SOLVE/1.0

HSI SOLVE is a finite meta-solver and deployment verifier. It does not claim to be a universal solver.

Core distinction:

verification closure != universal problem totality

Domains:
- SELF verifies the pinned HSI deployment graph.
- UTM preserves UNRESOLVED and never claims a universal halting decider.
- TRADER_42 preserves HOLD, paper, dry-run, unarmed, certificate-only behavior.
- OMEGA preserves UNRESOLVED and never forces COMMITTED.

SELF=COMMITTED means only that the finite pinned deployment graph passed protocol, provenance, and guard checks.

Pipeline:

SEARCH -> OBSERVE -> SELECT -> TRANSFORM -> VERIFY -> COMMIT/HOLD/UNRESOLVED

The three domain adapters are fetched from pinned commits, their protocol and domain guard are verified, SHA-256 provenance is recorded, and the existing hsi_blue_native.py gate is executed locally.

Default output:

~/HSI/SOLVE/YYYYMMDD-HHMMSS-PID/
  solve.request.json
  solve.hsicert
  deployment.lock.json
  manifest.json
  domains/

macOS / Linux:

    curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh

All domains:

    curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh -s -- --system ALL "finite problem context"

UTM:

    curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh -s -- --system UTM "problem"

TRADER_42:

    curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh -s -- --system TRADER_42 "market context"

OMEGA:

    curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh -s -- --system OMEGA "continuation context"

iSH:

    wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh

Android / Termux:

    pkg install -y python curl
    curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh | sh

Windows PowerShell:

    $p = Join-Path $env:TEMP "hsi-solve.ps1"; Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.ps1" -OutFile $p; & $p

Certificate fields distinguish solution_status, verification_closed, problem_totality_claim, and universal_solver_claim.

Examples:
- UTM may have solution_status=UNRESOLVED while verification_closed=true.
- TRADER_42 may have solution_status=HOLD while verification_closed=true.

Blue invariants:
semantic_non_coercion=true
semantic_humility=true
unresolved_is_valid=true
verification_closure_is_not_problem_totality=true
human_action_boundary=true
