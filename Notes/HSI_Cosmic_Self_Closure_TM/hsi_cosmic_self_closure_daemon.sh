#!/usr/bin/env bash
# Resident loop: every INTERVAL seconds run the proof (no --run) and compare with expected.json.
# Every 10th tick run --run for 2 seconds and require it to still be running (timeout exit 124) with the same header.
# --run is a tight loop with no sleep, so it is only run in short bursts here.
# Stop: touch "$DIR/run/KILL"   (or SC_KILL=1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; DIR="${SC_DIR:-$HERE}"
RUN="$DIR/run"; LOG="$DIR/self_closure_daemon.log"; INTERVAL="${SC_INTERVAL:-1}"
TM="$HERE/hsi_cosmic_self_closure_tm.sh"
mkdir -p "$RUN"; echo $$ > "$RUN/daemon.pid"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
trap 'rm -f "$RUN/daemon.pid"; echo "{\"ts\":\"$(ts)\",\"status\":\"stopped\"}" >> "$LOG"; exit 0' INT TERM
n=0
while :; do
  { [ -e "$RUN/KILL" ] || [ "${SC_KILL:-0}" = 1 ]; } && kill -TERM $$
  if [ $((n%10)) -eq 9 ]; then
    m=run; rc=0; timeout 2 bash "$TM" --run > "$RUN/run.out" 2>&1 || rc=$?
    [ $rc = 124 ] && cmp -s "$RUN/run.out" "$HERE/expected.json" && ok=1 || ok=0
  else
    m=proof; [ "$(bash "$TM" 2>&1)" = "$(cat "$HERE/expected.json")" ] && ok=1 || ok=0
  fi
  [ $ok = 1 ] && st=pass || st=fail
  echo "{\"ts\":\"$(ts)\",\"status\":\"$st\",\"mode\":\"$m\",\"n\":$n}" >> "$LOG"
  n=$((n+1)); sleep "$INTERVAL"
done
