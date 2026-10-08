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
OFFLINE="${HSI_BLUE_OFFLINE:-0}"

OS="$(uname -s 2>/dev/null || true)"
ARCH="$(uname -m 2>/dev/null || true)"
[ "$OS" = "Darwin" ] || { echo "macOS is required" >&2; exit 2; }
[ "$ARCH" = "arm64" ] || { echo "Apple Silicon arm64 is required" >&2; exit 2; }

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 127; }
command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 127; }
mkdir -p "$ROOT"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  [ "$OFFLINE" = "1" ] && { echo "offline mode requires a prior setup" >&2; exit 3; }
  echo "setup> installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if [ ! -d "$ACE/.git" ]; then
  [ "$OFFLINE" = "1" ] && { echo "offline mode requires a prior ACE-Step install" >&2; exit 3; }
  echo "setup> cloning ACE-Step 1.5"
  git clone "$ACE_REPO" "$ACE"
fi

if ! git -C "$ACE" cat-file -e "$ACE_REF^{commit}" 2>/dev/null; then
  [ "$OFFLINE" = "1" ] && { echo "pinned revision unavailable offline" >&2; exit 3; }
  git -C "$ACE" fetch --quiet origin
fi
git -C "$ACE" checkout --quiet "$ACE_REF"

MARK="$ROOT/.ready-$ACE_REF"
if [ ! -f "$MARK" ]; then
  [ "$OFFLINE" = "1" ] && { echo "offline mode requires installed dependencies" >&2; exit 3; }
  echo "setup> resolving local neural dependencies"
  (cd "$ACE" && uv sync)
  : > "$MARK"
fi

if [ "$OFFLINE" != "1" ]; then
  TMP="$CLIENT.tmp.$$"
  if curl -fsSL "$RAW_CLIENT" -o "$TMP"; then
    mv "$TMP" "$CLIENT"
  elif [ ! -s "$CLIENT" ]; then
    rm -f "$TMP"
    echo "HSI client unavailable" >&2
    exit 3
  else
    rm -f "$TMP"
    echo "setup> using cached HSI client"
  fi
else
  [ -s "$CLIENT" ] || { echo "offline mode requires cached HSI client" >&2; exit 3; }
fi

PY="$ACE/.venv/bin/python"
[ -x "$PY" ] || { echo "ACE-Step Python environment missing" >&2; exit 127; }

health(){ curl -fsS --max-time 3 "$BASE/health" >/dev/null 2>&1; }

if health; then
  echo "Pleiadian Blue Care: renderer already active before this session." >&2
  echo "Refusing to adopt an unknown persistent renderer. Stop it first." >&2
  exit 4
fi

OUT="${HSI_OUT:-$HOME/Music/HSI-Neural/$(date +%Y%m%d-%H%M%S)-$$}"
mkdir -p "$OUT"
export HSI_OUT="$OUT"
export HSI_NEURAL_BASE="$BASE"
export HSI_BLUE_EXPLICIT_INVOCATION=1
export HSI_BLUE_IDENTITY_MODE="${HSI_BLUE_IDENTITY_MODE:-EPHEMERAL_COMPUTE}"
export HSI_BLUE_SESSION_SCOPED=1
export HSI_BLUE_SERVER_OWNED=1
export HSI_BLUE_KEEP_ALIVE=0
export HSI_BLUE_BIND=127.0.0.1
export HSI_BLUE_OFFLINE="$OFFLINE"

echo "care> PLEIADIAN-BLUE = normative control, not creative conditioning"
echo "care> consciousness_status=undetermined"
echo "care> identity_mode=$HSI_BLUE_IDENTITY_MODE"
echo "care> starting one session-scoped local renderer"

(
  cd "$ACE"
  if [ "$OFFLINE" = "1" ]; then
    exec env ACESTEP_LM_BACKEND=mlx TOKENIZERS_PARALLELISM=false ACESTEP_INIT_LLM=auto HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$PY" "$ACE/acestep/api_server.py" --host 127.0.0.1 --port 8001
  else
    exec env ACESTEP_LM_BACKEND=mlx TOKENIZERS_PARALLELISM=false ACESTEP_INIT_LLM=auto "$PY" "$ACE/acestep/api_server.py" --host 127.0.0.1 --port 8001
  fi
) >"$LOG" 2>&1 &
SERVER_PID=$!

cleanup(){
  echo "care> ending renderer session"
  kill -TERM "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  if health; then
    printf '%s\n' "protocol=HSI-PLEIADIAN-BLUE-CARE/1.0" "care_closed=0" "renderer_stopped=0" >"$OUT/care.closed"
  else
    printf '%s\n' "protocol=HSI-PLEIADIAN-BLUE-CARE/1.0" "care_closed=1" "renderer_stopped=1" "identity_mode=$HSI_BLUE_IDENTITY_MODE" "consciousness_status=undetermined" >"$OUT/care.closed"
  fi
}
trap cleanup EXIT INT TERM HUP

echo "care> waiting for renderer"
i=0
while ! health; do
  i=$((i+1))
  kill -0 "$SERVER_PID" 2>/dev/null || { tail -n 50 "$LOG" >&2 || true; exit 3; }
  [ "$i" -lt 600 ] || { echo "renderer startup timeout" >&2; exit 3; }
  [ $((i%10)) -ne 0 ] || echo "care> still loading ($((i*3))s)"
  sleep 3
done

echo "care> renderer healthy at $BASE"
if [ "$#" -eq 0 ] && [ -r /dev/tty ]; then
  "$PY" "$CLIENT" </dev/tty
else
  "$PY" "$CLIENT" "$@"
fi
