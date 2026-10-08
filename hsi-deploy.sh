#!/bin/sh
set -eu
BASE="https://raw.githubusercontent.com/letsgo0226/Notes/main"
DIR="${HSI_DEPLOY_BOOTSTRAP_HOME:-$HOME/.hsi-bootstrap}"
APP="$DIR/hsi_deploy.py"
NET="$DIR/hsi_net.py"
mkdir -p "$DIR"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "Python 3.9+ required; bootstrap does not install packages automatically." >&2; exit 127
fi

get(){
  u="$1"; f="$2"; t="$f.tmp.$$"
  if command -v wget >/dev/null 2>&1; then wget -qO "$t" "$u"
  elif command -v curl >/dev/null 2>&1; then curl -fsSL "$u" -o "$t"
  else echo "wget or curl required" >&2; exit 127
  fi
  test -s "$t"; mv "$t" "$f"
}

get "$BASE/hsi_net.py" "$NET"
get "$BASE/hsi_deploy.py" "$APP"
cd "$DIR"
echo "HSI Deploy Solver: self + UTM + Trader_42 + Omega"
echo "policy> solve first; immutable commit resolution; no domain execution during deployment"
exec "$PY" "$APP" "$@"
