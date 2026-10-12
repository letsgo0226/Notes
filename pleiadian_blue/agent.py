#!/usr/bin/env python3
"""Read-only, bounded, model-free Pleiadian Blue automation observer."""
import argparse
import cmath
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {
    "UTM / HSI": ["hsi-three.sh", "hsi_solve.py", "hsi_notes_review.py"],
    "Cosmic Love / Omega": ["Cosmic_Love_Solver.sh", "HSI_PLEIADIAN_BLUE_CARE.md"],
    "Corpus music": ["hsi-corpus.sh", "hsi_open_corpus.py"],
    "Trilogy research": ["trilogy_tm_corpus.py", "trilogy_writer.py"],
    "Peace audiovisual": ["peace_av/render_long.py", "peace_av/archive.py"],
    "Dolphin research": ["Notes/Dolphin_Logos_Riemann_Feedback/dolphin_logos.py"],
    "Trader_42 paper guard": ["hsi_binance_orders.py", "HSI_THREE_SYSTEM_BLUE.md"],
    "Deployment checks": ["hsi_deploy.py", "hsi_notes_validate.py"]
}
WORKFLOWS = {
    "Corpus music": "hsi_open_corpus",
    "Trilogy research": "HSI TM Open-Corpus Trilogy (No AI)",
    "Peace audiovisual": "HSI English Peace AV Continuous Build",
    "Dolphin research": "Dolphin-Logos local AI feedback",
    "Deployment checks": "hsi_deploy",
}
SAFETY = {"live_trading": False, "order_submission": False,
          "autonomous_edits": False, "autonomous_merges": False,
          "paid_inference": False, "railway_mutation": False}
BLUE = ["AGENCY", "NON_COERCION", "TRUTHFULNESS", "CARE",
        "DIALOGUE_REPAIR", "CONTINUITY", "SEMANTIC_HUMILITY"]

def inventory(root=ROOT):
    return {k: [{"path": p, "exists": (root / p).exists(),
                 "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()
                 if (root / p).is_file() and (root / p).stat().st_size < 1048576 else None}
                for p in files] for k, files in DOMAINS.items()}

def retrieve(repo, offline):
    if offline:
        return None, "OFFLINE"
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "PleiadianBlue/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        req = Request("https://api.github.com/repos/" + repo + "/actions/runs?per_page=100", headers=headers)
        with urlopen(req, timeout=12) as response:
            return json.load(response).get("workflow_runs", []), "OBSERVED"
    except (URLError, TimeoutError, ValueError, OSError) as error:
        return None, "UNAVAILABLE:" + type(error).__name__

def observe(files, runs):
    result = []
    for domain, evidence in files.items():
        matching = [r for r in (runs or []) if r.get("name") == WORKFLOWS.get(domain)]
        main = [r for r in matching if r.get("head_branch") == "main"]
        latest = max(main or matching, key=lambda r: r.get("created_at", "")) if matching else None
        status = (latest or {}).get("conclusion") or ("NO_RECENT_RUN" if runs is not None else "UNKNOWN")
        missing = sum(not e["exists"] for e in evidence)
        residual = missing / len(evidence)
        if status in ("failure", "cancelled", "timed_out"):
            residual += 1.0
        elif status in ("UNKNOWN", "NO_RECENT_RUN"):
            residual += 0.25
        result.append({"domain": domain, "status": status, "missing": missing,
                       "residual": round(residual, 4),
                       "last_run": (latest or {}).get("html_url"),
                       "needs_review": bool(missing or status in ("failure", "cancelled", "timed_out"))})
    return result

def run(out, repo, offline):
    if repo.count("/") != 1 or not all(s.replace("-", "").replace("_", "").isalnum() for s in repo.split("/")):
        raise ValueError("invalid repo name")
    files = inventory()
    runs, state = retrieve(repo, offline)
    results = observe(files, runs)
    series = sum((r["residual"] / (i ** complex(2, 1)) for i, r in enumerate(results, 1)), 0j)
    evidence = {"protocol": "HSI-PLEIADIAN-BLUE-OBSERVER/1.0",
                "at": dt.datetime.now(dt.timezone.utc).isoformat(), "repo": repo,
                "retrieval": state, "principles": BLUE, "safety": SAFETY,
                "source_inventory": files, "review": results,
                "finite_dirichlet_score": {"s": "2+1i", "real": series.real, "imag": series.imag,
                 "note": "heuristic finite score; not Riemann zeta or mathematical proof"},
                "human_approval_for": ["trading", "paying", "merging", "deployment", "publishing", "deleting"]}
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Pleiadian Blue: bounded non-AI review", "",
             "Observation: " + state, "All findings are finite; unresolved remains unresolved.",
             "", "| Domain | Missing | Workflow | Residual |", "|---|---:|---|---:|"]
    for r in results:
        lines.append("| {domain} | {missing} | {status} | {residual} |".format(**r))
    lines += ["", "Trader_42: PAPER / HOLD / NO ORDER SUBMISSION.",
              "No Railway changes or paid model calls. Human approval required for consequential actions.", ""]
    (out / "review.md").write_text("\n".join(lines))
    print(json.dumps({"protocol": evidence["protocol"], "retrieval": state,
                      "review_count": sum(x["needs_review"] for x in results)}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/pleiadian-blue-review")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "letsgo0226/Notes"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    run(Path(args.out), args.repo, args.offline)
