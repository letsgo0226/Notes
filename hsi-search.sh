#!/bin/sh
set -eu
PIN="71be7f28917ec94abcb247db8b4150971c79e532"
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN/hsi_search.py"
RAW_NET="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN/hsi_net.py"
DIR="${HSI_SEARCH_HOME:-$HOME/.hsi-search}"
APP="$DIR/hsi_search.py"
NET="$DIR/hsi_net.py"
mkdir -p "$DIR"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
elif command -v pkg >/dev/null 2>&1; then pkg install -y python >/dev/null; PY=python
elif command -v apk >/dev/null 2>&1; then apk add --no-cache python3 >/dev/null; PY=python3
else echo "Python 3 required" >&2; exit 127
fi

TMP="$APP.tmp.$$"; TMP_NET="$NET.tmp.$$"
trap 'rm -f "$TMP" "$TMP_NET"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP" "$RAW"; wget -qO "$TMP_NET" "$RAW_NET"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW" -o "$TMP"; curl -fsSL "$RAW_NET" -o "$TMP_NET"
else echo "wget or curl required" >&2; exit 127
fi
test -s "$TMP"; test -s "$TMP_NET"
mv "$TMP" "$APP"; mv "$TMP_NET" "$NET"
trap - EXIT HUP INT TERM
chmod 700 "$APP" "$NET"

echo "HSI SEARCH: finite projection over HSI-NET-SINGULARITY/1.0; absence of retrieval is not nonexistence."
echo "bundle_commit> $PIN"
if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then exec "$PY" "$APP" </dev/tty; fi
exec "$PY" "$APP" "$@"
