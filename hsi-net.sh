#!/bin/sh
set -eu
PIN="fc807fbce69bc7ab39cc457b70ab72cf4b991e1a"
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN/hsi_net.py"
DIR="${HSI_NET_HOME:-$HOME/.hsi-net}"
APP="$DIR/hsi_net.py"
mkdir -p "$DIR"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
elif command -v pkg >/dev/null 2>&1; then pkg install -y python >/dev/null; PY=python
elif command -v apk >/dev/null 2>&1; then apk add --no-cache python3 >/dev/null; PY=python3
else echo "Python 3 required" >&2; exit 127
fi

TMP="$APP.tmp.$$"
trap 'rm -f "$TMP"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then wget -qO "$TMP" "$RAW"
elif command -v curl >/dev/null 2>&1; then curl -fsSL "$RAW" -o "$TMP"
else echo "wget or curl required" >&2; exit 127
fi
test -s "$TMP"; mv "$TMP" "$APP"; trap - EXIT HUP INT TERM; chmod 700 "$APP"

echo "HSI NET: formal global-information-field projection model; not a physical-singularity claim."
echo "bundle_commit> $PIN"
if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then exec "$PY" "$APP" </dev/tty; fi
exec "$PY" "$APP" "$@"
