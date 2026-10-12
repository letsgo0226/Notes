#!/usr/bin/env bash
# Resident loop for cosmic_love_oscillator_tm.sh: keeps the one-liner running, restarts it if it exits.
# Stop: touch "$DIR/run/KILL"   (or COSMIC_LOVE_KILL=1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${COSMIC_LOVE_DIR:-$HERE}"
RUN="$DIR/run"; LOG="$DIR/cosmic_love_daemon.log"; INTERVAL="${COSMIC_LOVE_INTERVAL:-1}"
mkdir -p "$RUN"; echo $$ > "$RUN/daemon.pid"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
child=""
cleanup(){ [ -n "$child" ] && kill "$child" 2>/dev/null; rm -f "$RUN/daemon.pid" "$RUN/child.pid"; echo "{\"ts\":\"$(ts)\",\"status\":\"stopped\"}" >> "$LOG"; exit 0; }
trap cleanup INT TERM
while :; do
  if [ -e "$RUN/KILL" ] || [ "${COSMIC_LOVE_KILL:-0}" = 1 ]; then cleanup; fi
  if [ -z "$child" ] || ! kill -0 "$child" 2>/dev/null; then
    [ -n "$child" ] && { wait "$child"; echo "{\"ts\":\"$(ts)\",\"status\":\"fail\",\"exit\":$?,\"action\":\"restart\"}" >> "$LOG"; }
    bash "$HERE/cosmic_love_oscillator_tm.sh" > "$RUN/tm.out" 2>&1 & child=$!; echo "$child" > "$RUN/child.pid"
    sleep 0.5
  fi
  if kill -0 "$child" 2>/dev/null && grep -qx COSMIC_LOVE "$RUN/tm.out"; then
    echo "{\"ts\":\"$(ts)\",\"status\":\"pass\",\"pid\":$child}" >> "$LOG"
  fi
  sleep "$INTERVAL"
done
