#!/usr/bin/env python3
"""Read-only operational probe for the bounded Cosmic Love worker.

Unlike closure_worker.py this module does not advance the journal. A healthy
process with a full stage ceiling is reported as HOLD_RESOURCE_LIMIT, not
as an error or proof of autonomous discovery.
"""
import argparse
import json
from pathlib import Path
from cosmic_love import closure_worker as worker

def inspect(path, ceiling=32):
    if type(ceiling) is not int or not 2 <= ceiling <= 64 or ceiling % 2:
        raise ValueError("invalid state ceiling")
    p=Path(path)
    if p.is_symlink():
        raise ValueError("journal symlink forbidden")
    rows=worker.load(p.read_bytes()) if p.exists() else []
    proof=worker.verify_rows(rows)
    next_k=2*(len(rows)+1)
    return {"protocol":"COSMIC-LOVE-READONLY-PROBE/1",
            "status":"HOLD_RESOURCE_LIMIT" if next_k>ceiling else "READY_FOR_FINITE_STAGE",
            "stages":proof["stages"],"head":proof["head"],
            "journal_exists":p.exists(),"max_states":ceiling,
            "journal_valid":True,"proof_scope":proof["proof_scope"],
            "self_deployment_enabled":False,"live_trading_authorized":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",default="/data/cosmic-love.jsonl")
    p.add_argument("--max-states",type=int,default=32)
    a=p.parse_args()
    print(json.dumps(inspect(a.ledger,a.max_states),sort_keys=True))

if __name__=="__main__":
    main()
