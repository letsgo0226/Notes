#!/usr/bin/env bash
# Resident loop: every INTERVAL seconds run the enumerator for 14 rounds and compare with expected_14.txt.
# Every 10th tick also runs 60 rounds and checks it exits cleanly with ROUND 60 as the last line.
# Stop: touch "$DIR/run/KILL"   (or DIAG_KILL=1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; DIR="${DIAG_DIR:-$HERE}"
RUN="$DIR/run"; LOG="$DIR/diagonal_daemon.log"; INTERVAL="${DIAG_INTERVAL:-1}"
TM="$HERE/diagonal_tm_enumerator.sh"
mkdir -p "$RUN"; echo $$ > "$RUN/daemon.pid"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
trap 'rm -f "$RUN/daemon.pid"; echo "{\"ts\":\"$(ts)\",\"status\":\"stopped\"}" >> "$LOG"; exit 0' INT TERM
n=0
while :; do
  { [ -e "$RUN/KILL" ] || [ "${DIAG_KILL:-0}" = 1 ]; } && kill -TERM $$
  if [ $((n%10)) -eq 9 ]; then m=deep; last="$(bash "$TM" 60 2>&1 | tail -1)"; case "$last" in "ROUND 60 "*) ok=1;; *) ok=0;; esac
  else m=exact; [ "$(bash "$TM" 14 2>&1)" = "$(cat "$HERE/expected_14.txt")" ] && ok=1 || ok=0; fi
  [ $ok = 1 ] && st=pass || st=fail
  echo "{\"ts\":\"$(ts)\",\"status\":\"$st\",\"mode\":\"$m\",\"n\":$n}" >> "$LOG"
  n=$((n+1)); sleep "$INTERVAL"
done
