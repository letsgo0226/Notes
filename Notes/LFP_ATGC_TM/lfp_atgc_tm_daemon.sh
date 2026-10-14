#!/usr/bin/env bash
# Resident loop: every INTERVAL seconds run lfp_atgc_tm.sh and check its output byte-for-byte against expected.json,
# plus FIX/REV true and chain ending at the fixed point 1111.
# Stop: touch "$DIR/run/KILL"   (or LFP_KILL=1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; DIR="${LFP_DIR:-$HERE}"
RUN="$DIR/run"; LOG="$DIR/lfp_daemon.log"; INTERVAL="${LFP_INTERVAL:-1}"
mkdir -p "$RUN"; echo $$ > "$RUN/daemon.pid"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
trap 'rm -f "$RUN/daemon.pid"; echo "{\"ts\":\"$(ts)\",\"status\":\"stopped\"}" >> "$LOG"; exit 0' INT TERM
n=0
while :; do
  { [ -e "$RUN/KILL" ] || [ "${LFP_KILL:-0}" = 1 ]; } && kill -TERM $$
  out="$(bash "$HERE/lfp_atgc_tm.sh" 2>&1)"
  if [ "$out" = "$(cat "$HERE/expected.json")" ] && printf %s "$out" | grep -q '"FIX":true' \
     && printf %s "$out" | grep -q '"REV":true' && printf %s "$out" | grep -q '"CHAIN":\["0000","1000","1100","1110","1111","1111"\]'
  then st=pass; else st=fail; fi
  echo "{\"ts\":\"$(ts)\",\"status\":\"$st\",\"n\":$n,\"fix\":\"1111\"}" >> "$LOG"
  n=$((n+1)); sleep "$INTERVAL"
done
