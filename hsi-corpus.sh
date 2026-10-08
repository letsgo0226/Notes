#!/bin/sh
set -eu

PIN="7b1bd7e7f8b498687325824e168fcc0492537eea"
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN/hsi_open_corpus.py"
RAW_SEARCH="https://raw.githubusercontent.com/letsgo0226/Notes/$PIN/hsi_search.py"
DIR="${HSI_CORPUS_HOME:-$HOME/.hsi-corpus}"
APP="$DIR/hsi_open_corpus.py"
SEARCH="$DIR/hsi_search.py"
mkdir -p "$DIR"

resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    PY=python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    PY=python
    return 0
  fi
  return 1
}

if ! resolve_python; then
  case "$(uname -s 2>/dev/null || true)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        echo "setup> installing Python with Homebrew"
        brew install python
      else
        echo "python3 required. Install Python 3 (or Homebrew) first." >&2
        exit 127
      fi ;;
    *)
      if command -v pkg >/dev/null 2>&1; then
        echo "setup> installing Python in Termux"
        pkg install -y python >/dev/null
      elif command -v apk >/dev/null 2>&1; then
        echo "setup> installing Python 3"
        apk add --no-cache python3 >/dev/null
      else
        echo "Python 3 required. Install python3 with your system package manager and rerun." >&2
        exit 127
      fi ;;
  esac
  resolve_python || { echo "Python installation was not found after setup." >&2; exit 127; }
fi

TMP="$APP.tmp.$$"
TMP_SEARCH="$SEARCH.tmp.$$"
trap 'rm -f "$TMP" "$TMP_SEARCH"' EXIT HUP INT TERM

if command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP" "$RAW"
  wget -qO "$TMP_SEARCH" "$RAW_SEARCH"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW" -o "$TMP"
  curl -fsSL "$RAW_SEARCH" -o "$TMP_SEARCH"
else
  echo "wget or curl required" >&2
  exit 127
fi

test -s "$TMP"
test -s "$TMP_SEARCH"
mv "$TMP" "$APP"
mv "$TMP_SEARCH" "$SEARCH"
trap - EXIT HUP INT TERM
chmod 700 "$APP" "$SEARCH"

echo "HSI Open-Corpus Renderer: no AI / HSI-SEARCH / Openverse CC0+PDM WAV / deterministic DSP"
echo "bundle_commit> $PIN"
echo "note> YouTube audio is not downloaded or sampled."
echo "note> Openverse license metadata is indexed metadata; verify landing pages before publication/commercial reuse."

if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then
  exec "$PY" "$APP" </dev/tty
fi
exec "$PY" "$APP" "$@"
