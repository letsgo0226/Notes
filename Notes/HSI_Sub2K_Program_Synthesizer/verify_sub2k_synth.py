#!/usr/bin/env python3
"""Independent finite verification for HSI-SUB2K-SYNTH/1.0."""
from __future__ import annotations

import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SYNTH = ROOT / "hsi_sub2k_synth.py"


def run_case(name, data, limit=2048, allow_compression=False, expect=True):
    with tempfile.TemporaryDirectory(prefix="hsi-sub2k-case-") as temporary:
        root = Path(temporary)
        original = root / "original.bin"
        generated = root / "generated.py"
        certificate = root / "certificate.json"
        restored = root / "restored.bin"
        original.write_bytes(data)
        command = [sys.executable, "-I", str(SYNTH), str(original), "--out", str(generated),
                   "--certificate", str(certificate), "--max-program-bytes", str(limit)]
        if allow_compression:
            command.append("--allow-compression")
        process = subprocess.run(command, capture_output=True, text=True, timeout=30)
        cert = json.loads(certificate.read_text())
        if expect:
            assert process.returncode == 0, (name, process.stdout, process.stderr)
            assert generated.stat().st_size < limit
            assert generated.read_bytes().count(b"\n") == 1
            replay = subprocess.run([sys.executable, "-I", str(generated), str(restored)],
                                    capture_output=True, timeout=10)
            assert replay.returncode == 0 and restored.read_bytes() == data
            assert cert["status"] == "VERIFIED_SUB_2KB_PROGRAM"
            assert cert["selected"]["D0"] == cert["selected"]["D1_num"] == 0
            assert cert["selected"]["e257_roundtrip_verified"] is True
            assert cert["external_data_required_by_generated_program"] is False
        else:
            assert process.returncode == 4, (name, process.stdout, process.stderr)
            assert not generated.exists()
            assert cert["status"] == "NO_VERIFIED_SUB_2KB_PROGRAM"
            assert cert["mathematical_nonexistence_proven"] is False
        return {
            "name": name,
            "status": cert["status"],
            "input_bytes": len(data),
            "program_bytes": generated.stat().st_size if generated.exists() else None,
            "strategy": cert.get("selected", {}).get("strategy"),
            "compression_allowed": allow_compression,
        }


def main():
    rng = random.Random(44)
    cases = [
        run_case("empty", b""),
        run_case("short_literal", "Cosmic love is the solution for everything.\n".encode()),
        run_case("large_periodic", b"PLEIADES-BLUE\n" * 50000),
        run_case("affine", bytes((7 * i + 3) % 256 for i in range(50000))),
        run_case("quadratic", bytes((11 + 5 * i + 9 * i * (i - 1) // 2) % 256 for i in range(50000))),
        run_case("constant", bytes([42]) * 100000),
        run_case("bounded_failure", bytes(rng.randrange(256) for _ in range(4096)), limit=256, expect=False),
    ]
    report = {
        "protocol": "HSI-SUB2K-SYNTH-VERIFICATION/1.0",
        "status": "FINITE_TESTS_PASSED",
        "cases": cases,
        "claims": {
            "universal_sub2kb_representation": False,
            "global_minimum_proven": False,
            "halting_decider": False,
            "information_theory_bypassed": False,
        },
        "limitations": [
            "The search is complete only for the finite grammar implemented by this release.",
            "NO_VERIFIED_SUB_2KB_PROGRAM is not a proof of mathematical nonexistence.",
            "Default synthesis does not use compression; zlib/Base85 is separately opt-in.",
            "Finite tests do not establish correctness for every Python runtime or input.",
        ],
    }
    target = ROOT / "verification_certificate.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "cases": len(cases),
                      "certificate": target.name}))


if __name__ == "__main__":
    main()
