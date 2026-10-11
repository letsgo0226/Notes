#!/bin/sh
set -eu
DIR="${HSI_BOOTSTRAP_HOME:-$HOME/.hsi-bootstrap}"
REF="${HSI_BUNDLE_REF:-main}"
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/$REF/hsi_bootstrap.py"
mkdir -p "$DIR"
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "Python 3.9+ required. Install Python 3 and rerun." >&2; exit 127
fi
TMP="$DIR/hsi_bootstrap.py.tmp.$$"
trap 'rm -f "$TMP"' EXIT HUP INT TERM
if command -v curl >/dev/null 2>&1; then curl -fsSL "$RAW" -o "$TMP"
elif command -v wget >/dev/null 2>&1; then wget -qO "$TMP" "$RAW"
else "$PY" -c 'import sys,urllib.request;open(sys.argv[2],"wb").write(urllib.request.urlopen(sys.argv[1],timeout=30).read())' "$RAW" "$TMP"
fi
test -s "$TMP"
mv "$TMP" "$DIR/hsi_bootstrap.py"
trap - EXIT HUP INT TERM
if [ "$#" -eq 0 ] && ( : </dev/tty ) 2>/dev/null; then
  exec "$PY" "$DIR/hsi_bootstrap.py" corpus </dev/tty
fi
exec "$PY" "$DIR/hsi_bootstrap.py" corpus "$@"
