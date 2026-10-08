#!/bin/sh
set -eu
BASE="https://raw.githubusercontent.com/letsgo0226/Notes/main"
DIR="${HSI_UPDATE_HOME:-$HOME/.hsi-update}"
APP="$DIR/hsi_update.py"
mkdir -p "$DIR"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "Python 3.9+ required." >&2; exit 127
fi

TMP="$APP.tmp.$$"
trap 'rm -f "$TMP"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then wget -qO "$TMP" "$BASE/hsi_update.py"
elif command -v curl >/dev/null 2>&1; then curl -fsSL "$BASE/hsi_update.py" -o "$TMP"
else echo "wget or curl required" >&2; exit 127
fi
test -s "$TMP"; mv "$TMP" "$APP"; trap - EXIT HUP INT TERM
chmod 700 "$APP"

echo "HSI UPDATE: artifact-driven finite update solver; no automatic source rewrite or git push."
exec "$PY" "$APP" "$@"
