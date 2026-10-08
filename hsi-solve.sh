#!/bin/sh
set -eu
PIN="4c7507fd5bed2545994a824c3e7bf95892e0155d"
BASE="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN"
DIR="${HSI_SOLVE_HOME:-$HOME/.hsi-solve}"
APP="$DIR/hsi_solve.py"
NET="$DIR/hsi_net.py"
SEARCH="$DIR/hsi_search.py"
BUNDLE="$DIR/hsi_solve_domains.json"
mkdir -p "$DIR"

resolve_python(){
  if command -v python3 >/dev/null 2>&1; then PY=python3; return 0; fi
  if command -v python >/dev/null 2>&1; then PY=python; return 0; fi
  return 1
}
if ! resolve_python; then
  if command -v pkg >/dev/null 2>&1; then pkg install -y python >/dev/null
  elif command -v apk >/dev/null 2>&1; then apk add --no-cache python3 >/dev/null
  elif [ "$(uname -s 2>/dev/null || true)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then brew install python
  else echo "Python 3 required" >&2; exit 127
  fi
  resolve_python || exit 127
fi

T1="$APP.tmp.$"; T2="$NET.tmp.$"; T3="$SEARCH.tmp.$"; T4="$BUNDLE.tmp.$"
trap 'rm -f "$T1" "$T2" "$T3" "$T4"' EXIT HUP INT TERM
get(){
  u="$1"; f="$2"
  if command -v wget >/dev/null 2>&1; then wget -qO "$f" "$u"
  elif command -v curl >/dev/null 2>&1; then curl -fsSL "$u" -o "$f"
  else echo "wget or curl required" >&2; exit 127
  fi
  test -s "$f"
}
get "$BASE/hsi_solve.py" "$T1"
get "$BASE/hsi_net.py" "$T2"
get "$BASE/hsi_search.py" "$T3"
get "$BASE/hsi_solve_domains.json" "$T4"
mv "$T1" "$APP"; mv "$T2" "$NET"; mv "$T3" "$SEARCH"; mv "$T4" "$BUNDLE"
trap - EXIT HUP INT TERM
chmod 700 "$APP" "$NET" "$SEARCH"

echo "HSI SOLVE: finite meta-solver + self-deployment verifier"
echo "bundle_commit> $PIN"
echo "note> verification closure is not universal problem totality."
exec "$PY" "$APP" "$@"
