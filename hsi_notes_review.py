#!/usr/bin/env python3
"""Read-only, fail-closed inventory of Notes/ for four-system review.

No network requests, source execution, deployments, trades, or audio rendering.
A passing certificate asserts only the locked local file inventory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

PROTOCOL = "HSI-NOTES-FOUR-SYSTEM-REVIEW/0.1"
DOMAINS = ("music_corpus", "music_native", "music_ai_bridge", "utm", "trader_42", "omega")


def git_blob_sha1(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def valid_path(s):
    if not isinstance(s, str) or not s.startswith("Notes/"):
        return False
    p = Path(s)
    return (not p.is_absolute() and s == p.as_posix() and all(part not in ("", ".", "..") for part in p.parts) and "\\" not in s)


def audit(root, lock):
    root = Path(root)
    expected = {}
    issues = []
    for row in lock.get("entries", []):
        p = row.get("path")
        if not valid_path(p) or p in expected or type(row.get("bytes")) is not int or row["bytes"] < 0 or not re.fullmatch(r"[a-f0-9]{40}", str(row.get("git_blob_sha1", ""))):
            issues.append({"type": "invalid_lock_entry", "path": str(p)})
        else:
            expected[p] = row
    observed = {}
    source_dir = root / "Notes"
    if not source_dir.is_dir() or source_dir.is_symlink():
        issues.append({"type": "missing_or_unsafe_notes_directory", "path": "Notes"})
    else:
        for base, dirs, files in os.walk(source_dir, followlinks=False):
            for name in list(dirs):
                p = Path(base) / name
                if p.is_symlink():
                    issues.append({"type": "symlink_directory", "path": p.relative_to(root).as_posix()})
                    dirs.remove(name)
            for name in files:
                p = Path(base) / name
                rel = p.relative_to(root).as_posix()
                if p.is_symlink() or not p.is_file():
                    issues.append({"type": "unsafe_file", "path": rel})
                    continue
                data = p.read_bytes()
                observed[rel] = {
                    "bytes": len(data),
                    "git_blob_sha1": git_blob_sha1(data),
                    "sha256": hashlib.sha256(data).hexdigest()
                }
    for rel in sorted(set(expected) - set(observed)):
        issues.append({"type": "missing_file", "path": rel})
    for rel in sorted(set(observed) - set(expected)):
        issues.append({"type": "unlocked_file", "path": rel})
    for rel in sorted(set(expected) & set(observed)):
        for k in ("bytes", "git_blob_sha1"):
            if expected[rel][k] != observed[rel][k]:
                issues.append({"type": "source_mismatch", "path": rel, "field": k})
    status = "SOURCE_INVENTORY_VERIFIED" if not issues else "REVIEW_REQUIRED"
    return {
        "protocol": PROTOCOL,
        "source": {k: lock.get(k) for k in ("source_repo", "source_ref", "source_commit", "snapshot_date")},
        "inventory_status": status,
        "expected_count": len(expected),
        "observed_count": len(observed),
        "observed": {key: observed[key] for key in sorted(observed)},
        "issues": issues,
        "domain_gates": {k: "NOT_TESTED_NOT_DEPLOYED" for k in DOMAINS},
        "claims": {
            "global_halting_decider": False,
            "semantic_audio_model_from_documents": False,
            "railway_updated": False,
            "music_end_to_end_verified": False,
            "live_trading_authorized": False,
            "ethical_truth_proven": False
        }
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--lock", default=str(Path(__file__).with_name("hsi_notes_review.lock.json")))
    ap.add_argument("--json-out", help="optional local JSON certificate output")
    a = ap.parse_args()
    lock = json.loads(Path(a.lock).read_text(encoding="utf-8"))
    if lock.get("protocol") != PROTOCOL:
        ap.error("incompatible lock protocol")
    result = audit(Path(a.root), lock)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if a.json_out:
        Path(a.json_out).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["inventory_status"] == "SOURCE_INVENTORY_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
