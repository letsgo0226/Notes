#!/bin/sh
set -eu
PIN="b944dab3ff77db1abad474c91d41c0754d6dfe33"
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN/hsi_xy_analytic_2k"
DIR="${HSI_XY_HOME:-$HOME/.hsi-xy-stream}"
ENGINE="$DIR/hsi_stream.py"
MICRO="$DIR/hsi_cl_xy_2k.sh"
mkdir -p "$DIR"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python
fi
command -v "$PY" >/dev/null 2>&1 || { echo "Python 3 is required." >&2; exit 127; }

T1="$ENGINE.tmp.$$"
T2="$MICRO.tmp.$$"
trap 'rm -f "$T1" "$T2"' EXIT HUP INT TERM
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW/hsi_stream.py" -o "$T1"
  curl -fsSL "$RAW/hsi_cl_xy_2k.sh" -o "$T2"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$T1" "$RAW/hsi_stream.py"
  wget -qO "$T2" "$RAW/hsi_cl_xy_2k.sh"
else
  echo "curl or wget required." >&2
  exit 127
fi
test -s "$T1" && test -s "$T2"
mv "$T1" "$ENGINE"
mv "$T2" "$MICRO"
trap - EXIT HUP INT TERM
echo "HSI UTM + CL-XY continuous stream / immutable bundle $PIN" >&2
echo "note> output keeps running; Ctrl+C interrupts, checkpoint permits resume" >&2
exec "$PY" "$ENGINE" --microkernel "$MICRO" "$@"
