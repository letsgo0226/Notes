#!/usr/bin/env python3
"""Bounded, read-only HSI cross-domain self-review.

Produces deterministic candidate diagnostics. Does not execute domain programs,
fetch arbitrary URLs, edit source files, submit orders, or auto-merge PRs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = "HSI-CONTINUOUS-REVIEW/1.0"
DOMAIN_FILES = {
    "mathematical_core": ["Notes/1", "Notes/2", "Notes/3", "Notes/4",
                          "Notes/HSI_Prime_Analytic_2KB_Release/verify_prime_analytic.py"],
    "three_systems": ["hsi_deploy.py", "hsi_notes_run.py", "hsi_xy_analytic_2k/core_readable.py"],
    "corpus_music": ["hsi_open_corpus.py", "hsi_native_renderer.py", "hsi_corpus_autoevolve.py"],
    "writing": ["trilogy_writer.py", "trilogy_tm_corpus.py"],
    "video": ["peace_av/render_long.py", "peace_av/experimental_speaker.py"],
    "trading_simulation_only": ["hsi_binance_orders.py"],
}
GUARDRAILS = {
    "source_mutation": False,
    "automatic_git_push": False,
    "automatic_pr_merge": False,
    "arbitrary_program_execution": False,
    "live_broker_orders": False,
    "secrets_access": False,
    "network_fetch": False,
    "requires_human_review_for_deployment": True,
}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory():
    source = ROOT / "Notes"
    if not source.is_dir():
        raise RuntimeError("Notes/ source directory is missing")
    files = sorted((p for p in source.rglob("*") if p.is_file()), key=lambda p: str(p))
    if len(files) != 12:
        raise RuntimeError(f"immutable Notes source inventory changed: {len(files)} files, expected 12")
    return [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p),
             "bytes": p.stat().st_size} for p in files]

def inspect():
    domains = {}
    for domain, files in DOMAIN_FILES.items():
        items = []
        for rel in files:
            p = ROOT / rel
            items.append({"path": rel, "exists": p.is_file(),
                          "sha256": sha(p) if p.is_file() else None})
        domains[domain] = {
            "files": items,
            "ready_for_candidate_review": all(x["exists"] for x in items),
            "deployment_approved": False,
        }
    return domains

def candidate_plan(domains):
    # This is a proposal list, NOT a claim that new code has been synthesized.
    out = []
    for name, info in domains.items():
        out.append({
            "domain": name,
            "proposal": "review_existing_capabilities_and_tests",
            "status": "REVIEW_ONLY",
            "missing_files": [x["path"] for x in info["files"] if not x["exists"]],
            "auto_deploy": False,
            "autonomous_code_rewrite": False,
            "human_approval_required": True,
        })
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="hsi_continuous/out")
    args = parser.parse_args()
    target = (ROOT / args.out).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("output must stay inside repository")
    source = (ROOT / "Notes").resolve()
    if target == source or source in target.parents:
        raise ValueError("cannot write inside Notes")
    inv = inventory()
    domains = inspect()
    report = {
        "protocol": PROTOCOL,
        "mode": "OFFLINE_REVIEW_ONLY",
        "notes_inventory": inv,
        "domains": domains,
        "candidate_plan": candidate_plan(domains),
        "guardrails": GUARDRAILS,
        "scope_note": "File hashes and existence only; no domain solver was executed or proven correct.",
    }
    target.mkdir(parents=True, exist_ok=True)
    path = target / "review.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PROTOCOL}: wrote {path.relative_to(ROOT)}; {len(inv)} locked sources; "
          f"{len(domains)} domains; no live actions")
    return 0

if __name__ == "__main__":
    sys.exit(main())
