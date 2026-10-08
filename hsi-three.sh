#!/bin/sh
set -eu
S="${1:-}"
if [ -z "$S" ] && [ -r /dev/tty ]; then
  printf 'system [SELF|UTM|TRADER_42|OMEGA|ALL]> ' >/dev/tty
  IFS= read -r S </dev/tty
fi
S="$(printf '%s' "$S" | tr '[:lower:]' '[:upper:]')"
case "$S" in
  TRADER|TRADER42) S="TRADER_42" ;;
esac
case "$S" in
  SELF|UTM|TRADER_42|OMEGA|ALL) ;;
  *) echo "usage: hsi-three.sh SELF|UTM|TRADER_42|OMEGA|ALL [problem...]" >&2; exit 2 ;;
esac
[ "$#" -eq 0 ] || shift

U="https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-solve.sh"
T="${TMPDIR:-/tmp}/hsi-solve-dispatch-$$.sh"
trap 'rm -f "$T"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then wget -qO "$T" "$U"
elif command -v curl >/dev/null 2>&1; then curl -fsSL "$U" -o "$T"
else echo "wget or curl required" >&2; exit 127
fi
test -s "$T"
if [ "$#" -eq 0 ]; then
  if [ "$S" = "SELF" ]; then sh "$T" --system "$S"
  else sh "$T" --system "$S" </dev/tty
  fi
else
  sh "$T" --system "$S" "$@"
fi
