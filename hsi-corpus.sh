#!/bin/sh
set -eu
RAW="https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi_open_corpus.py"
RAW_SEARCH="https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi_search.py"
DIR="${HSI_CORPUS_HOME:-$HOME/.hsi-corpus}"
APP="$DIR/hsi_open_corpus.py"
SEARCH="$DIR/hsi_search.py"
mkdir -p "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
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
      if command -v apk >/dev/null 2>&1; then
        echo "setup> installing Python 3"
        apk add --no-cache python3 >/dev/null
      else
        echo "python3 required" >&2
        exit 127
      fi ;;
  esac
fi

TMP="$APP.tmp.$"
TMP_SEARCH="$SEARCH.tmp.$"
trap 'rm -f "$TMP" "$TMP_SEARCH"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP" "$RAW"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW" -o "$TMP"
else
  echo "wget or curl required" >&2
  exit 127
fi
test -s "$TMP"
if command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_SEARCH" "$RAW_SEARCH"
else
  curl -fsSL "$RAW_SEARCH" -o "$TMP_SEARCH"
fi
test -s "$TMP_SEARCH"
mv "$TMP" "$APP"
mv "$TMP_SEARCH" "$SEARCH"
trap - EXIT HUP INT TERM
chmod 700 "$APP" "$SEARCH"

echo "HSI Open-Corpus Renderer: no AI / Openverse CC0+PDM WAV / deterministic DSP"
echo "note> YouTube audio is not downloaded or sampled."
echo "note> Openverse license metadata is indexed metadata; verify landing pages before publication/commercial reuse."

if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then
  exec python3 "$APP" </dev/tty
fi
exec python3 "$APP" "$@"
