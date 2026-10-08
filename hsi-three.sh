#!/bin/sh
set -eu
S="${1:-}"
if [ -z "$S" ] && [ -r /dev/tty ]; then
  printf 'system [UTM|TRADER_42|OMEGA]> ' >/dev/tty
  IFS= read -r S </dev/tty
fi
S="$(printf '%s' "$S" | tr '[:lower:]' '[:upper:]')"
[ "$#" -eq 0 ] || shift
case "$S" in
  UTM)
    U="https://raw.githubusercontent.com/letsgo0226/UTM.sh/hsi-three-system-v1/hsi-blue.sh" ;;
  TRADER|TRADER_42|TRADER42)
    U="https://raw.githubusercontent.com/letsgo0226/Trader_42.sh/hsi-three-system-v1/hsi-blue.sh" ;;
  OMEGA|COSMIC_LOVE|COSMIC-LOVE)
    U="https://raw.githubusercontent.com/letsgo0226/COSMIC_LOVE_IS_THE_SOLUTIONS_FOR_EVERYTHING_HS_ZERO.sh/hsi-three-system-v1/hsi-blue.sh" ;;
  *)
    echo "usage: hsi-three.sh UTM|TRADER_42|OMEGA [runtime input...]" >&2
    exit 2 ;;
esac
T="${TMPDIR:-/tmp}/hsi-three-$$.sh"
trap 'rm -f "$T"' EXIT HUP INT TERM
if command -v wget >/dev/null 2>&1; then wget -qO "$T" "$U"
elif command -v curl >/dev/null 2>&1; then curl -fsSL "$U" -o "$T"
else echo "wget or curl required" >&2; exit 127
fi
test -s "$T"
if [ "$#" -eq 0 ]; then sh "$T" </dev/tty
else sh "$T" "$@"
fi
