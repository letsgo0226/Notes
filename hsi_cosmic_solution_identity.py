#!/usr/bin/env python3
"""Exact finite-byte identity certificate for the COSMIC_LOVE two-step TM.

This proves preservation/restoration of bytes, NOT truth or solvability of
propositions encoded by those bytes. The CLI accepts text or --stdin bytes.
"""
import hashlib
import json
import sys
from math import isqrt

PROTOCOL = "HSI-COSMIC-SOLUTION-IDENTITY/1"
PROGRAM = 55067263
CORPUS_MAX_BYTES = 4096


def _decoder():
    v = (isqrt(8 * PROGRAM + 1) - 1) // 2
    c = PROGRAM - v * (v + 1) // 2
    k = v - c + 1
    K = k + 1
    B = 4 * K
    if k != 2:
        raise ValueError("unexpected TM active-state count")

    def step(q, a):
        u = c // B ** (2 * q + a) % B
        z, r = divmod(u, K)
        return r, z // 2, 2 * (z % 2) - 1

    if any(step(q, a) != (1 - q, a, 1 - 2 * q)
           for q in (0, 1) for a in (0, 1)):
        raise ValueError("TM decoder does not match the reviewed 4-rule table")
    return step


def _e257(data):
    g = 1
    for b in data:
        g = 257 * g + b + 1
    return g


def _d257(g):
    if type(g) is not int or g < 1:
        raise ValueError("invalid E257 integer")
    digits = bytearray()
    while g > 1:
        g, r = divmod(g, 257)
        if not 1 <= r <= 256:
            raise ValueError("invalid E257 digit")
        digits.append(r - 1)
    return bytes(reversed(digits))


def solution(data, *, max_bytes=None):
    """Return (identical bytes, exact E257 integer) after a two-step TM check.

    Core supports any finite bytes value, subject to available host resources.
    The Corpus integration applies a separate bounded operational limit.
    """
    if not isinstance(data, bytes):
        raise TypeError("solution input must be bytes")
    if max_bytes is not None and len(data) > max_bytes:
        raise ValueError("identity input exceeds bounded Corpus certificate limit")

    step = _decoder()
    tape = {8 * i + j for i, x in enumerate(data)
            for j in range(8) if x & (128 >> j)}
    tape.add(8 * len(data))  # unique terminator beyond all data bits
    initial = tape.copy()
    q = h = 0
    for _ in range(2):
        a = int(h in tape)
        q, written, direction = step(q, a)
        if written:
            tape.add(h)
        else:
            tape.discard(h)
        h += direction
    if (q, h, tape) != (0, 0, initial):
        raise ValueError("two-step TM configuration did not return exactly")

    L = max(tape) // 8
    if max(tape) != 8 * L or L != len(data):
        raise ValueError("invalid binary terminator")
    restored = bytes(
        sum((8 * i + j in tape) << (7 - j) for j in range(8))
        for i in range(L)
    )
    if restored != data:
        raise ValueError("binary tape roundtrip mismatch")

    g = _e257(restored)
    if _d257(g) != data:
        raise ValueError("E257 roundtrip mismatch")
    return restored, g


def certificate(data, *, max_bytes=CORPUS_MAX_BYTES):
    """Compact reproducible witness for a finite Corpus generation-seed input."""
    restored, g = solution(data, max_bytes=max_bytes)
    g_hex = hex(g)
    checks = {
        "decoder_four_rules": True,
        "two_step_configuration_identity": True,
        "tape_inverse": True,
        "e257_inverse": True,
    }
    result = {
        "protocol": PROTOCOL,
        "statement": "solution(s)=s",
        "program": PROGRAM,
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "result_sha256": hashlib.sha256(restored).hexdigest(),
        "godel_hex_digits": len(g_hex) - 2,
        "godel_hex_sha256": hashlib.sha256(g_hex.encode("ascii")).hexdigest(),
        "checks": checks,
        "validated": True,
        "scope": "finite-byte exact identity only; no proposition solving or physical vacuum-energy claim",
    }
    result["certificate_uid"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ["--stdin"]:
        data = sys.stdin.buffer.read()
    elif len(args) <= 1 and (not args or not args[0].startswith("--")):
        data = (args[0] if args else "").encode("utf-8")
    else:
        raise SystemExit("usage: python3 hsi_cosmic_solution_identity.py [TEXT | --stdin]")
    restored, g = solution(data)
    print("COSMIC_LOVE")
    print(json.dumps({
        "statement": "solution(s)=s", "s_hex": data.hex(),
        "result_hex": restored.hex(), "godel_hex": hex(g),
        "validated": True
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
