# Pleiadian Blue: one-second Daemon

This is a deterministic, non-AI *heartbeat* and finite Dirichlet-inspired local feedback engine. The "Dolphin" research persona is symbolic and does not denote literal extraterrestrial agency, consciousness, or autonomous intelligence.

**GitHub-hosted Actions cannot be 24/7 every second:** cron has a 5-minute minimum interval and a hosted job lasts at most 6 hours. GitHub runs this workflow as a 3-tick proof-of-operation and stores a short-lived artifact. This workflow is **not** an always-on deployment.

## Operate locally or on a persistent VPS (with Python 3.11+)

Run from repository root, after obtaining the verified repository source:

    mkdir -p "$HOME/.local/state/pleiadian-blue"
    python3 pleiadian_blue/daemon.py \
      --db "$HOME/.local/state/pleiadian-blue/state.sqlite3" \
      --status "$HOME/.local/state/pleiadian-blue/status.json" \
      --source "$HOME/.local/state/pleiadian-blue/receipt.json" \
      --interval 1

Without a source receipt the state is explicitly UNKNOWN_NO_SOURCE. To obtain one, run `python3 pleiadian_blue/agent.py --out "$HOME/.local/state/pleiadian-blue"` using bounded GitHub retrieval (not every second). Only the light-weight local heartbeat runs every second. Stop with Ctrl-C or SIGTERM; restart using the same SQLite path to preserve the counter. Multiple instances sharing a database are blocked by file lock. On OS sleep or shutdown, ticks naturally stop: 1 second is a target interval, not a hard real-time guarantee.

A persistent host can manage this process with `systemd` (`Restart=always`), macOS `launchd`, or a VPS supervisor. If using GitHub's **self-hosted runner**, the runner machine still has to be online, and starting a daemon from within a short GitHub Actions job does not itself guarantee persistence. Install it as an OS-managed service on the host.

## Scope / safety

- No live orders, funding, code changes, commits, merges, uploads, service deployments, API calls, model inference, or web browsing from the Daemon.
- Emits one atomic JSON status and one SQLite checkpoint per heartbeat. Monitor disk durability/backup, process health and power availability; persistent SQLite files must be stored on a durable volume, not an ephemeral Actions runner.
- Unverified/absent/stale information is not evidence of a successful research goal. Repeated heartbeats do not constitute fresh research, model evolution, or Riemann-Hypothesis progress.
- The finite score is a diagnostic series, not the Riemann zeta function, a discovery engine, or a general-AI replacement.
- `--max-ticks 3` runs only three ticks; `--max-ticks 0` runs until signalled, provided the host stays on.
- GitHub Actions on the default branch verifies the engine daily; the earlier Pleiadian Blue observer remains separate.

### Readiness before unattended operation
Explicitly choose who owns the persistent host and backups. Keep external commands and real-money trading disabled. Do not cancel Railway until any needed services and persistent data have been backed up and migrated.
