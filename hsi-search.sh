#!/bin/sh
set -eu
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi_search.py"
DIR="${HSI_SEARCH_HOME:-$HOME/.hsi-search}"
APP="$DIR/hsi_search.py"
mkdir -p "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
  case "$(uname -s 2>/dev/null || true)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        brew install python
      else
        echo "python3 required. Install Python 3 (or Homebrew) first." >&2
        exit 127
      fi ;;
    *)
      if command -v apk >/dev/null 2>&1; then
        apk add --no-cache python3 >/dev/null
      else
        echo "python3 required" >&2
        exit 127
      fi ;;
  esac
fi

TMP="$APP.tmp.$$"
trap 'rm -f "$TMP"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP" "$RAW"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW" -o "$TMP"
else
  echo "wget or curl required" >&2
  exit 127
fi
test -s "$TMP"
mv "$TMP" "$APP"
trap - EXIT HUP INT TERM
chmod 700 "$APP"

echo "HSI SEARCH: finite evidence expansion; absence of retrieval is not nonexistence."
if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then
  exec python3 "$APP" </dev/tty
fi
exec python3 "$APP" "$@"
