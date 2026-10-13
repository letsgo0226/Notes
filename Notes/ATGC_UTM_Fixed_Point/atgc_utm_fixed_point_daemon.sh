#!/usr/bin/env bash
# Resident loop: every INTERVAL seconds verify the ATGC fixed point.
# Cycle: proof (self), self encode->decode roundtrip, run a fixed bundled test program, reject invalid strand.
# MODE=run only ever executes the bundled test program below, never outside input.
# Stop: touch "$DIR/run/KILL"   (or ATGC_KILL=1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; DIR="${ATGC_DIR:-$HERE}"
RUN="$DIR/run"; LOG="$DIR/atgc_daemon.log"; INTERVAL="${ATGC_INTERVAL:-1}"
TM="$HERE/atgc_utm_fixed_point.sh"
mkdir -p "$RUN"; echo $$ > "$RUN/daemon.pid"
printf 'print("COSMIC_LOVE",6*7)' > "$RUN/test_program.py"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
trap 'rm -f "$RUN/daemon.pid"; echo "{\"ts\":\"$(ts)\",\"status\":\"stopped\"}" >> "$LOG"; exit 0' INT TERM
n=0
while :; do
  { [ -e "$RUN/KILL" ] || [ "${ATGC_KILL:-0}" = 1 ]; } && kill -TERM $$
  case $((n%4)) in
    0) m=proof;     out="$(bash "$TM" 2>/dev/null)"; printf %s "$out" | grep -q '"REV":true,"SOLUTION_EQ_S":true' ;;
    1) m=roundtrip; MODE=encode bash "$TM" 2>/dev/null | MODE=decode bash "$TM" 2>/dev/null | cmp -s - "$TM" ;;
    2) m=run;       [ "$(MODE=encode SOURCE="$RUN/test_program.py" bash "$TM" 2>/dev/null | MODE=run bash "$TM" 2>/dev/null)" = "COSMIC_LOVE 42" ] ;;
    3) m=reject;    ! echo AGTX | MODE=decode bash "$TM" >/dev/null 2>&1 ;;
  esac
  if [ $? -eq 0 ]; then st=pass; else st=fail; fi
  echo "{\"ts\":\"$(ts)\",\"status\":\"$st\",\"mode\":\"$m\",\"n\":$n}" >> "$LOG"
  n=$((n+1)); sleep "$INTERVAL"
done
