#!/usr/bin/env python3
"""Bounded ATGC controller: evidence and a fail-closed deployment PLAN only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

PROTOCOL = "ATGC-MASTER/1.0"
TARGETS = {
    "hsi_self": ("hsi_deploy.py", "hsi_net.py", "hsi_bootstrap.py"),
    "utm": ("hsi-three.sh", "hsi_solve.py", "hsi_xy_analytic_2k/core_readable.py"),
    "omega": ("hsi_deploy.py", "hsi_cosmic_solution_identity.py"),
    "corpus_music": ("hsi_open_corpus.py", "hsi-corpus.sh", "hsi_native_renderer.py"),
    "writing": ("trilogy_writer.py", "trilogy_tm_corpus.py"),
    "peace": ("peace_av",),
    "trader_42_research": ("hsi_binance_orders.py", "tests/test_hsi_binance_orders.py"),
}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def safe_bytes(root, rel, limit=2_000_000):
    path = root
    for component in Path(rel).parts:
        path = path / component
        if path.is_symlink():
            raise ValueError("symlink denied: " + rel)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("missing, directory or oversized: " + rel)
    return path.read_bytes()


def build(root):
    root = Path(root).resolve(strict=True)
    core = "atgc_auto/atgc_self.sh"
    report = {
        "protocol": PROTOCOL,
        "mode": "REVIEW_ONLY",
        "core": {"path": core, "self_reconstructed": False, "gc": None},
        "inventory": {"status": "UNVERIFIED", "issues": []},
        "targets": {},
        "permissions": {"read_repository": True, "write_repository": False,
                        "external_deploy": False, "run_broker": False,
                        "live_orders": False, "auto_merge": False},
        "production_deployed": False,
    }
    try:
        source = safe_bytes(root, core, 2048)
        p = subprocess.run(["sh", str(root / core)], cwd=root, capture_output=True,
                           text=True, timeout=15, check=True)
        proof = json.loads(p.stdout)
        assert proof["self_reconstructed"] is True and proof["gc"] == "1/2"
        assert proof["source_bytes"] == len(source) and proof["atgc_length"] == 16 * len(source)
        report["core"] = {"path": core, "self_reconstructed": True, "gc": "1/2",
                          "bytes": len(source), "sha256": digest(source),
                          "atgc_length": proof["atgc_length"]}
    except (OSError, ValueError, KeyError, AssertionError, subprocess.SubprocessError) as exc:
        report["core"]["error"] = type(exc).__name__ + ": " + str(exc)[:250]

    for name, paths in TARGETS.items():
        hashes, issues = {}, []
        for rel in paths:
            try:
                if (root / rel).is_dir() and not (root / rel).is_symlink():
                    hashes[rel] = "DIRECTORY_EXISTS_NOT_VERIFIED"
                else:
                    hashes[rel] = digest(safe_bytes(root, rel))
            except (OSError, ValueError) as exc:
                issues.append(str(exc))
        report["targets"][name] = {"status": "SOURCE_PRESENT_REVIEW_ONLY" if not issues else "HOLD",
                                    "source_hashes": hashes, "issues": issues,
                                    "external_actions": 0}

    try:
        # Import only the existing read-only Notes inventory routine.
        import sys
        sys.path.insert(0, str(root))
        from hsi_notes_review import PROTOCOL as notes_protocol, audit
        lock = json.loads(safe_bytes(root, "hsi_notes_review.lock.json"))
        if lock.get("protocol") != notes_protocol:
            raise ValueError("Notes lock protocol mismatch")
        inv = audit(root, lock)
        report["inventory"] = {"status": inv["inventory_status"],
                               "expected_count": inv["expected_count"],
                               "observed_count": inv["observed_count"],
                               "issues": inv["issues"][:100]}
    except (OSError, ValueError, KeyError, ImportError, TypeError) as exc:
        report["inventory"] = {"status": "REVIEW_REQUIRED", "issues": [str(exc)[:250]]}

    ok = (report["core"]["self_reconstructed"] and
          report["inventory"]["status"] == "SOURCE_INVENTORY_VERIFIED" and
          all(x["status"] == "SOURCE_PRESENT_REVIEW_ONLY" for x in report["targets"].values()))
    report["decision"] = "REVIEW_READY_NOT_DEPLOYED" if ok else "HOLD_REVIEW_REQUIRED"
    report["certificate_sha256"] = digest(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                                    separators=(",", ":")).encode())
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    parser.add_argument("--strict", action="store_true", help="exit 2 when reviews are held")
    opts = parser.parse_args()
    report = build(opts.root)
    s = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if opts.out:
        output = Path(opts.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(s, encoding="utf-8")
    print(s)
    return 2 if opts.strict and report["decision"] != "REVIEW_READY_NOT_DEPLOYED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
