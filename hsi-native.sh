#!/bin/sh
set -eu
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi_native_renderer.py"
DIR="${HSI_NATIVE_HOME:-$HOME/.hsi-native}"
APP="$DIR/hsi_native_renderer.py"
command -v python3 >/dev/null 2>&1 || { command -v apk >/dev/null 2>&1 && apk add --no-cache python3 >/dev/null; }
command -v python3 >/dev/null 2>&1 || { echo "python3 required" >&2; exit 127; }
mkdir -p "$DIR"
TMP="$APP.tmp.$$"
trap 'rm -f "$TMP"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP" "$RAW"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW" -o "$TMP"
else
  python3 -c 'import sys,urllib.request;open(sys.argv[2],"wb").write(urllib.request.urlopen(sys.argv[1],timeout=60).read())' "$RAW" "$TMP"
fi
test -s "$TMP"
mv "$TMP" "$APP"
trap - EXIT HUP INT TERM
chmod 700 "$APP"
echo "HSI Native Renderer: local/offline synthesis; no external AI/API."
if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then
  exec python3 "$APP" </dev/tty
fi
exec python3 "$APP" "$@"
