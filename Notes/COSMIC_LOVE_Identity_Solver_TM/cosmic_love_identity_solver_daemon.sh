#!/usr/bin/env bash
# Resident loop: every INTERVAL seconds, run the one-liner on test inputs and assert solution(s)=s.
# Stop: touch "$DIR/run/KILL"   (or COSMIC_LOVE_KILL=1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; DIR="${COSMIC_LOVE_DIR:-$HERE}"
RUN="$DIR/run"; LOG="$DIR/cosmic_love_identity_daemon.log"; INTERVAL="${COSMIC_LOVE_INTERVAL:-1}"
TM="$HERE/cosmic_love_identity_solver_tm.sh"
mkdir -p "$RUN"; echo $$ > "$RUN/daemon.pid"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
trap 'rm -f "$RUN/daemon.pid"; echo "{\"ts\":\"$(ts)\",\"status\":\"stopped\"}" >> "$LOG"; exit 0' INT TERM
n=0
while :; do
  { [ -e "$RUN/KILL" ] || [ "${COSMIC_LOVE_KILL:-0}" = 1 ]; } && kill -TERM $$
  case $((n%4)) in 0) s="";; 1) s="COSMIC_LOVE";; 2) s="宇宙之愛";; 3) s="t=$n";; esac
  out="$(bash "$TM" "$s" 2>&1)"; rc=$?
  hex="$(printf %s "$s" | od -An -tx1 | tr -d ' \n')"
  if [ $rc -eq 0 ] && [ "$(printf %s "$out" | head -1)" = COSMIC_LOVE ] \
     && printf %s "$out" | tail -1 | grep -q "\"s_hex\":\"$hex\",\"result_hex\":\"$hex\"" \
     && printf %s "$out" | grep -q '"validated":true'; then st=pass; else st=fail; fi
  echo "{\"ts\":\"$(ts)\",\"status\":\"$st\",\"n\":$n,\"s_hex\":\"$hex\"}" >> "$LOG"
  n=$((n+1)); sleep "$INTERVAL"
done
