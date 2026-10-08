#!/bin/sh
set -eu

ROOT="${HSI_NEURAL_HOME:-$HOME/.hsi-neural}"
ACE="$ROOT/ACE-Step-1.5"
CLIENT="$ROOT/hsi_local_neural.py"
RAW_CLIENT="https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi_local_neural.py"
ACE_REPO="https://github.com/ace-step/ACE-Step-1.5.git"
ACE_REF="${HSI_ACE_REF:-ca1e85fe9430179831e6bc6be790c332190a3866}"
BASE="${HSI_NEURAL_BASE:-http://127.0.0.1:8001}"
LOG="$ROOT/acestep-api.log"
PID="$ROOT/acestep-api.pid"

OS="$(uname -s 2>/dev/null || true)"
ARCH="$(uname -m 2>/dev/null || true)"
if [ "$OS" != "Darwin" ]; then
  echo "HSI Local Neural v1 currently targets macOS Apple Silicon." >&2
  exit 2
fi
if [ "$ARCH" != "arm64" ]; then
  echo "Apple Silicon (arm64) is required for the current MLX path; detected: $ARCH" >&2
  exit 2
fi

command -v git >/dev/null 2>&1 || {
  echo "git is required. Install Apple's Command Line Tools first: xcode-select --install" >&2
  exit 127
}
command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 127; }

mkdir -p "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "setup> installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || { echo "uv installation failed" >&2; exit 127; }

if [ ! -d "$ACE/.git" ]; then
  echo "setup> cloning ACE-Step 1.5"
  git clone "$ACE_REPO" "$ACE"
fi

echo "setup> pinning ACE-Step $ACE_REF"
git -C "$ACE" fetch --quiet origin
git -C "$ACE" checkout --quiet "$ACE_REF"

MARK="$ROOT/.ready-$ACE_REF"
if [ ! -f "$MARK" ]; then
  echo "setup> resolving local neural dependencies (first run can be large)"
  (cd "$ACE" && uv sync)
  : > "$MARK"
fi

TMP="$CLIENT.tmp.$$"
trap 'rm -f "$TMP"' EXIT HUP INT TERM
curl -fsSL "$RAW_CLIENT" -o "$TMP"
test -s "$TMP"
mv "$TMP" "$CLIENT"
trap - EXIT HUP INT TERM

health() {
  curl -fsS --max-time 3 "$BASE/health" >/dev/null 2>&1
}

if ! health; then
  echo "server> starting local ACE-Step MLX backend"
  (
    cd "$ACE"
    ACESTEP_API_HOST=127.0.0.1 ACESTEP_API_PORT=8001       nohup sh ./start_api_server_macos.sh >"$LOG" 2>&1 &
    echo $! >"$PID"
  )
  echo "server> waiting for local model service; first launch may download model weights"
  i=0
  while ! health; do
    i=$((i+1))
    if [ "$i" -ge 600 ]; then
      echo "server failed to become healthy. Last log lines:" >&2
      tail -n 40 "$LOG" >&2 || true
      exit 3
    fi
    if [ $((i%10)) -eq 0 ]; then
      echo "server> still loading ($((i*3))s)"
    fi
    sleep 3
  done
fi

echo "server> healthy at $BASE"
PY="$ACE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python not found after uv sync" >&2; exit 127; }

if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then
  exec "$PY" "$CLIENT" </dev/tty
fi
exec "$PY" "$CLIENT" "$@"
