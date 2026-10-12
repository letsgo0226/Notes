#!/usr/bin/env python3
"""Bounded synthesis of standalone Python reconstructors smaller than 2 KiB.

Success means that a generated one-line program was executed in a fresh
temporary directory and reproduced the requested bytes exactly.  Failure means
only that this finite grammar did not find a qualifying program; it is not a
proof that no such program exists.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zlib

PROTOCOL = "HSI-SUB2K-SYNTH/1.0"
DEFAULT_LIMIT = 2048
DEFAULT_INPUT_LIMIT = 16 * 1024 * 1024

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


def e257(raw: bytes) -> int:
    value = 1
    for byte in raw:
        value = value * 257 + byte + 1
    return value


def d257(value: int) -> bytes:
    if isinstance(value, bool) or value < 1:
        raise ValueError("invalid E257 coordinate")
    digits = []
    while value > 1:
        value, remainder = divmod(value, 257)
        if not 1 <= remainder <= 256:
            raise ValueError("invalid E257 digit")
        digits.append(remainder - 1)
    return bytes(reversed(digits))


def program(expression: str, imports: str = "sys") -> bytes:
    source = f'import {imports};open(sys.argv[1],"wb").write({expression})\n'
    return source.encode("utf-8")


def _minimal_period(data: bytes) -> int:
    """Return the shortest prefix whose infinite repetition starts with data."""
    n = len(data)
    if n < 2:
        return n
    # Only a short period can participate in a sub-2KiB source.  This bounded
    # check avoids allocating an O(n) prefix table for multi-megabyte inputs.
    for size in range(1, min(n, 480) + 1):
        unit = data[:size]
        if all(data[offset:offset + size] == unit[:min(size, n - offset)]
               for offset in range(size, n, size)):
            return size
    return n


def _runs(data: bytes, maximum: int = 96):
    if not data:
        return []
    result = []
    value = data[0]
    count = 1
    for byte in data[1:]:
        if byte == value:
            count += 1
        else:
            result.append((value, count))
            if len(result) > maximum:
                return None
            value, count = byte, 1
    result.append((value, count))
    return result if len(result) <= maximum else None


def _quadratic(data: bytes):
    if len(data) < 3:
        return None
    initial = data[0]
    first = (data[1] - data[0]) % 256
    second = (data[2] - 2 * data[1] + data[0]) % 256
    if all(byte == (initial + first * i + second * i * (i - 1) // 2) % 256
           for i, byte in enumerate(data)):
        return initial, first, second
    return None


def candidate_sources(data: bytes, allow_compression: bool = False):
    """Enumerate a finite, deterministic reconstruction grammar."""
    candidates = []

    def add(strategy, expression, imports="sys", compression=False):
        candidates.append({
            "strategy": strategy,
            "source": program(expression, imports),
            "compression": compression,
        })

    n = len(data)
    if n <= 1900:
        add("bytes_literal", repr(data))
        add("hex_literal", f'bytes.fromhex("{data.hex()}")')
        number = int.from_bytes(data, "big") if data else 0
        add("integer_literal", f'({number}).to_bytes({n},"big")')
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            add("utf8_literal", repr(text) + ".encode()")

    if not data:
        add("empty", 'b""')
    else:
        if len(set(data)) == 1:
            add("constant_byte", f"bytes([{data[0]}])*{n}")

        period = _minimal_period(data)
        if 0 < period < n:
            unit = data[:period]
            repetitions = (n + period - 1) // period
            add("periodic_prefix", f"({unit!r}*{repetitions})[:{n}]")

        first = data[0]
        if all(byte == (first + i) % 256 for i, byte in enumerate(data)):
            add("ascending_mod256", f"bytes(({first}+i)%256 for i in range({n}))")

        if n >= 2:
            delta = (data[1] - data[0]) % 256
            if all(byte == (first + delta * i) % 256 for i, byte in enumerate(data)):
                add("affine_mod256", f"bytes(({first}+{delta}*i)%256 for i in range({n}))")

        quad = _quadratic(data)
        if quad is not None:
            a, b, c = quad
            add("quadratic_mod256", f"bytes(({a}+{b}*i+{c}*i*(i-1)//2)%256 for i in range({n}))")

        runs = _runs(data)
        if runs:
            add("run_length", f'b"".join(bytes([v])*n for v,n in {tuple(runs)!r})')
            longest = sorted(enumerate(runs), key=lambda item: item[1][1], reverse=True)[:8]
            positions = []
            cursor = 0
            for index, (value, count) in enumerate(runs):
                positions.append(cursor)
                cursor += count
            for index, (value, count) in longest:
                if count < 8:
                    continue
                start = positions[index]
                expression = f"{data[:start]!r}+bytes([{value}])*{count}+{data[start + count:]!r}"
                add("long_run_splice", expression)

    if allow_compression:
        payload = base64.b85encode(zlib.compress(data, 9)).decode("ascii")
        add("zlib_base85_opt_in",
            f'zlib.decompress(base64.b85decode(b"{payload}"))',
            "sys,zlib,base64", True)

    unique = {}
    for candidate in candidates:
        unique.setdefault(candidate["source"], candidate)
    return sorted(unique.values(), key=lambda item: (len(item["source"]), item["strategy"]))


def verify_source(source: bytes, expected: bytes, timeout: float = 10.0):
    residuals = [0, 0, 0]
    result = {"executed": False, "exit_code": None, "output_bytes": None,
              "byte_for_byte_equal": False}
    with tempfile.TemporaryDirectory(prefix="hsi-sub2k-verify-") as temporary:
        root = Path(temporary)
        candidate = root / "candidate.py"
        output = root / "reconstructed.bin"
        candidate.write_bytes(source)
        try:
            process = subprocess.run(
                [sys.executable, "-I", str(candidate), str(output)],
                cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=timeout, check=False,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
            )
        except (OSError, subprocess.TimeoutExpired):
            residuals[1] = 1
        else:
            result["executed"] = True
            result["exit_code"] = process.returncode
            if process.returncode != 0:
                residuals[1] = 1
            if output.is_file() and not output.is_symlink():
                recovered = output.read_bytes()
                result["output_bytes"] = len(recovered)
                result["byte_for_byte_equal"] = recovered == expected
            if not result["byte_for_byte_equal"]:
                residuals[2] = 1
    return residuals, result


def synthesize(data: bytes, max_program_bytes: int = DEFAULT_LIMIT,
               allow_compression: bool = False, timeout: float = 10.0):
    if isinstance(max_program_bytes, bool) or not 64 <= max_program_bytes <= 65536:
        raise ValueError("max_program_bytes must be an integer from 64 to 65536")
    generated = candidate_sources(data, allow_compression)
    eligible = [c for c in generated if len(c["source"]) < max_program_bytes]
    attempts = []
    for candidate in eligible:
        residuals, execution = verify_source(candidate["source"], data, timeout)
        attempt = {
            "strategy": candidate["strategy"],
            "program_bytes": len(candidate["source"]),
            "compression": candidate["compression"],
            "residuals": residuals,
            "D0": sum(residuals),
            "D1_num": 15 * residuals[0] + 10 * residuals[1] + 6 * residuals[2],
            "execution": execution,
        }
        attempts.append(attempt)
        if not any(residuals):
            coordinate = str(e257(candidate["source"]))
            certificate = {
                "protocol": PROTOCOL,
                "status": "VERIFIED_SUB_2KB_PROGRAM",
                "input_bytes": len(data),
                "limit": {"strictly_less_than_bytes": max_program_bytes},
                "compression_allowed": allow_compression,
                "candidates_generated": len(generated),
                "candidates_within_limit": len(eligible),
                "selected": {
                    **attempt,
                    "physical_lines": len(candidate["source"].splitlines()),
                    "source_e257": coordinate,
                    "source_e257_decimal_digits": len(coordinate),
                    "e257_roundtrip_verified": d257(int(coordinate)) == candidate["source"],
                },
                "verification": "fresh_tempdir_execution_and_exact_byte_comparison",
                "external_data_required_by_generated_program": False,
                "runtime_dependency": "Python 3 standard library",
                "claims": {
                    "universal_sub2kb_representation": False,
                    "global_minimum_proven": False,
                    "halting_decider": False,
                    "information_theory_bypassed": False,
                },
            }
            return candidate["source"], certificate

    residuals = [
        int(not eligible),
        int(bool(attempts) and all(attempt["residuals"][1] for attempt in attempts)),
        1,
    ]
    certificate = {
        "protocol": PROTOCOL,
        "status": "NO_VERIFIED_SUB_2KB_PROGRAM",
        "input_bytes": len(data),
        "limit": {"strictly_less_than_bytes": max_program_bytes},
        "compression_allowed": allow_compression,
        "candidates_generated": len(generated),
        "candidates_within_limit": len(eligible),
        "attempts": attempts,
        "residuals": residuals,
        "D0": sum(residuals),
        "D1_num": 15 * residuals[0] + 10 * residuals[1] + 6 * residuals[2],
        "search_complete_for_declared_finite_grammar": True,
        "mathematical_nonexistence_proven": False,
        "claims": {
            "universal_sub2kb_representation": False,
            "global_minimum_proven": False,
            "halting_decider": False,
            "information_theory_bypassed": False,
        },
    }
    return None, certificate


def _atomic_write(path: Path, raw: bytes, force: bool, executable: bool = False):
    if path.exists() and not force:
        raise FileExistsError(f"refusing to replace existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if executable:
            temporary.chmod(0o755)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="finite source file to reconstruct")
    parser.add_argument("--out", required=True, help="generated one-line Python program")
    parser.add_argument("--certificate", help="optional JSON verification certificate")
    parser.add_argument("--max-program-bytes", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--max-input-bytes", type=int, default=DEFAULT_INPUT_LIMIT)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--allow-compression", action="store_true",
                        help="also try an explicitly labelled zlib/Base85 payload")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    source = Path(args.input).resolve()
    output = Path(args.out).resolve()
    certificate_path = Path(args.certificate).resolve() if args.certificate else None
    if not source.is_file() or source.is_symlink():
        parser.error("input must be a regular non-symlink file")
    if output == source or certificate_path == source or certificate_path == output:
        parser.error("input, output, and certificate paths must be distinct")
    for destination in (output, certificate_path):
        if destination is not None and destination.exists() and not args.force:
            parser.error(f"refusing to replace existing path: {destination}")
    size = source.stat().st_size
    if isinstance(args.max_input_bytes, bool) or args.max_input_bytes < 0 or size > args.max_input_bytes:
        parser.error(f"input has {size} bytes; configured maximum is {args.max_input_bytes}")
    if args.timeout <= 0:
        parser.error("timeout must be positive")

    raw = source.read_bytes()
    if len(raw) > args.max_input_bytes:
        parser.error("input changed while it was being read and now exceeds the configured maximum")
    generated, certificate = synthesize(
        raw, args.max_program_bytes,
        args.allow_compression, args.timeout,
    )
    if certificate_path:
        payload = (json.dumps(certificate, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        _atomic_write(certificate_path, payload, args.force)
    if generated is None:
        print(json.dumps({"status": certificate["status"], "input_bytes": size,
                          "certificate": str(certificate_path) if certificate_path else None}))
        return 4
    _atomic_write(output, generated, args.force, executable=True)
    print(json.dumps({
        "status": certificate["status"],
        "input_bytes": size,
        "program_bytes": len(generated),
        "strategy": certificate["selected"]["strategy"],
        "program": str(output),
        "certificate": str(certificate_path) if certificate_path else None,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
