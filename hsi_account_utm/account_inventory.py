#!/usr/bin/env python3
"""Public-owner GitHub repository inventory; read-only; never executes repo content."""
import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

PROTOCOL = "HSI-ACCOUNT-UTM-PUBLIC-REVIEW/1"


def e257(data):
    n = 1
    for b in data:
        n = 257 * n + b + 1
    return hex(n)


def normalize(owner, pages, max_pages=20):
    observed = {}
    for page in pages:
        if not isinstance(page, list):
            raise ValueError("GitHub page must be an array")
        for obj in page:
            if not isinstance(obj, dict) or obj.get("owner", {}).get("login", "").lower() != owner.lower():
                continue
            if obj.get("private") is not False:
                continue
            name = obj.get("full_name")
            if not isinstance(name, str) or name.split("/", 1)[0].lower() != owner.lower() or "/" not in name:
                continue
            observed[name] = {
                "full_name": name,
                "cell_e257_hex": e257(name.encode("utf-8")),
                "default_branch": obj.get("default_branch"),
                "archived": bool(obj.get("archived", False)),
                "fork": bool(obj.get("fork", False)),
                "visibility": "public",
                "status": "INVENTORIED_NOT_DEPLOYED",
            }
    return {"protocol": PROTOCOL, "owner": owner,
            "scope": "public repositories returned by GitHub users API only",
            "complete_account_coverage": False,
            "operations": ["read_public_metadata", "e257_repo_name"],
            "automatic_push": False, "automatic_merge": False, "live_trading": False,
            "external_deployment": False,
            "repositories": [observed[k] for k in sorted(observed)],
            "public_count": len(observed)}


def fetch_pages(owner, max_pages=20):
    pages = []
    for page_num in range(1, max_pages + 1):
        url = f"https://api.github.com/users/{owner}/repos?type=owner&per_page=100&page={page_num}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "HSI-account-UTM-readonly-inventory/1",
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            items = json.load(response)
        if not isinstance(items, list):
            raise ValueError("GitHub returned a non-list result")
        pages.append(items)
        if len(items) < 100:
            return pages, False
    return pages, True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fixture", help="offline JSON array of public-repository rows")
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", args.owner):
        ap.error("Invalid GitHub account name")
    if args.fixture:
        rows = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        pages, truncated = [rows], False
    else:
        pages, truncated = fetch_pages(args.owner)
    report = normalize(args.owner, pages)
    report["pagination_truncated"] = truncated
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"protocol": PROTOCOL, "owner": args.owner,
                      "public_count": report["public_count"], "pagination_truncated": truncated,
                      "status": "READ_ONLY_NO_DEPLOY"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
