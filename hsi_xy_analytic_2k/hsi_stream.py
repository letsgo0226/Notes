#!/usr/bin/env python3
"""Continuous HSI_original enumeration verified by the unchanged HSI-CL-XY/2K engine.

One outer record enumerates (e,T,m) exactly like HSI-UTM/1.0, runs up to
T accepted XY transitions, then persists the next outer enumerator index.
An XY HALTED condition is about that candidate TM, not the stream controller.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

PROTOCOL = "HSI-UTM-XY-STREAM/1.0"


def pair(n):
    w = (math.isqrt(8*n+1)-1)//2
    a = n-w*(w+1)//2
    return a, w-a+1


def machine_states(p):
    z = (math.isqrt(8*p+1)-1)//2
    c = p-z*(z+1)//2
    return z-c+1


def store(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def decode_e257(code):
    n = int(code)
    if n < 1:
        raise ValueError("invalid XY Gödel number")
    buf = bytearray()
    while n > 1:
        n, r = divmod(n, 257)
        if r < 1 or r > 256:
            raise ValueError("non-canonical XY Gödel digit")
        buf.append(r-1)
    buf.reverse()
    return json.loads(bytes(buf).decode("utf-8"))


def execute_xy(script, path, p, word, *, evolve=None, perm=None):
    env = dict(os.environ)
    for key in ("HSI_RULE", "HSI_CAND", "HSI_PERM"):
        env.pop(key, None)
    env.update(HSI_STATE=str(path), HSI_PROGRAM=str(p), HSI_WORD=word, HSI_START="0")
    if evolve is not None:
        env["HSI_RULE"] = str(evolve)
        if perm is not None:
            env["HSI_PERM"] = perm
    r = subprocess.run(["sh", str(script)], env=env, capture_output=True,
                       text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError("XY microkernel failed: "+r.stderr[-500:])
    line = r.stdout.strip()
    y = json.loads(line)
    if y.get("protocol") != "HSI-CL-XY/2K":
        raise RuntimeError("unexpected XY protocol")
    d = read(path)
    actual = [d["p"], d["q"], d["h"], d["m"]]
    if decode_e257(y["y"]) != actual:
        raise RuntimeError("XY y code mismatches saved state")
    if y["step"] != d["n"] or y["history"] != len(d["H"]):
        raise RuntimeError("XY counter/history mismatch")
    if y["kind"] != "HALTED":
        event = decode_e257(d["H"][-1])
        residual = event[-1]
        if (not isinstance(residual, list) or len(residual) != 3
                or any(type(v) is not int or v < 0 for v in residual)):
            raise RuntimeError("XY history has invalid residuals")
        if y["D0"] != sum(residual) or y["D1_num"] != (
                15*residual[0]+10*residual[1]+6*residual[2]):
            raise RuntimeError("XY Dirichlet residual does not match persisted event")
    if y["D0"] < 0 or y["D1_num"] < 0 or (y["D0"] == 0) != (y["D1_num"] == 0):
        raise RuntimeError("XY Dirichlet zero certificate inconsistency")
    return y, d


def stream(args):
    path = Path(args.state).expanduser().resolve()
    xy_path = path.with_name(path.name+".active-xy.json")
    micro = Path(args.microkernel).expanduser().resolve()
    if not micro.is_file():
        raise ValueError("XY microkernel not found: "+str(micro))
    if any(c not in "01" for c in args.word) or not args.word:
        raise ValueError("HSI_WORD must be a nonempty binary word")
    if args.limit < 0 or args.max_budget < 0 or args.sleep < 0:
        raise ValueError("negative limit, budget or delay")
    if args.evolve_rule is not None and args.evolve_rule < 0:
        raise ValueError("negative evolution rule")

    config = {"word":args.word, "max_budget":args.max_budget,
              "evolve_rule":args.evolve_rule, "perm":args.perm}
    if path.exists():
        state = read(path)
        if state.get("protocol") != PROTOCOL or state.get("config") != config:
            raise ValueError("stream checkpoint differs from requested configuration; use a new --state")
    else:
        state = {"protocol":PROTOCOL, "next":0, "config":config}
        store(path, state)

    completed = 0
    while args.limit == 0 or completed < args.limit:
        n = state["next"]
        # Recover from a crash after committing the outer index but before
        # clearing the previous candidate's persisted XY state.
        if xy_path.exists() and state.get("last_completed") == n-1:
            xy_path.unlink()
        r, T = pair(n)
        e, m = pair(r)
        p = e+1
        skipped = args.max_budget != 0 and T > args.max_budget
        if skipped:
            if xy_path.exists():
                raise RuntimeError("unexpected active XY state for skipped candidate")
            item = {"protocol":PROTOCOL,"step":n,"branch":e,"budget":T,
                    "order":m,"program":p,"status":"SKIPPED_BUDGET",
                    "xy_steps":0,"xy_closed":0}
        else:
            if not xy_path.exists() and args.evolve_rule is not None:
                ev, d = execute_xy(micro, xy_path, p, args.word,
                                   evolve=args.evolve_rule, perm=args.perm)
                if ev["kind"] != "EVOLVE" or ev["accepted"] != 1 or ev["D0"] != 0 or ev["D1_num"] != 0:
                    raise RuntimeError("proposed XY rule evolution rejected; stream not advanced")
                if args.emit_xy:
                    print(json.dumps({"outer_step":n,"xy":ev},separators=(",",":")), flush=True)
            last = None
            d = read(xy_path) if xy_path.exists() else None
            if d is not None:
                if args.evolve_rule is not None:
                    if not d.get("H"):
                        raise RuntimeError("evolution history is missing")
                    first = decode_e257(d["H"][0])
                    if (first[0] != "E" or first[1] != args.evolve_rule
                            or first[-1] != [0,0,0]):
                        raise RuntimeError("previous XY evolution was rejected; stream not advanced")
                if d.get("origin") != [p,args.word,0] or d["n"] > T:
                    raise RuntimeError("active XY checkpoint does not match enumerated candidate")
                if args.evolve_rule is None and d["p"] != p:
                    raise RuntimeError("unexpected machine mutation in active XY checkpoint")
            for _ in range(T-(d["n"] if d is not None else 0)):
                if d is not None and d["q"] == machine_states(d["p"]):
                    break
                last, d = execute_xy(micro, xy_path, p, args.word)
                if last["kind"] != "STEP" or last["accepted"] != 1 or last["D0"] != 0 or last["D1_num"] != 0:
                    raise RuntimeError("XY STEP certificate invalid; stream not advanced")
                if args.emit_xy:
                    print(json.dumps({"outer_step":n,"xy":last},separators=(",",":")),flush=True)
            if d is None:
                raise RuntimeError("missing XY state after candidate simulation")
            halted = d["q"] == machine_states(d["p"])
            item = {"protocol":PROTOCOL,"step":n,"branch":e,"budget":T,
                    "order":m,"program":p,"active_program":d["p"],
                    "status":"HALTED" if halted else "UNRESOLVED",
                    "xy_steps":d["n"],"xy_closed":1,
                    "xy_D0":0,"xy_D1_num":0,"q":d["q"],
                    "head":d["h"],"tape_ones":len(d["m"]),
                    "xy_history":len(d["H"])}
            if last is not None:
                item["x"] = last["x"]
                item["y"] = last["y"]
        # Atomic checkpoint before emitting; crashes may omit, never falsely advance.
        state = {"protocol":PROTOCOL, "next":n+1, "last_completed":n, "config":config}
        store(path, state)
        if xy_path.exists():
            xy_path.unlink()
        print(json.dumps(item, separators=(",", ":")),flush=True)
        completed += 1
        if args.sleep:
            time.sleep(args.sleep)


def main():
    p = argparse.ArgumentParser(description="Original infinite dovetail + exact XY step verification")
    p.add_argument("--state",default=os.getenv("HSI_STREAM_STATE",str(Path.home()/".hsi-xy-stream"/"stream.json")))
    p.add_argument("--microkernel",default=str(Path(__file__).with_name("hsi_cl_xy_2k.sh")))
    p.add_argument("--word",default=os.getenv("HSI_WORD","1"))
    p.add_argument("--limit",type=int,default=0,help="outer records; 0 means continuous")
    p.add_argument("--max-budget",type=int,default=128,help="skip candidates requiring more XY steps; 0 removes bound")
    p.add_argument("--sleep",type=float,default=.2)
    p.add_argument("--emit-xy",action="store_true",help="also print every inner XY STEP/EVOLVE result")
    p.add_argument("--evolve-rule",type=int,help="optional finite conservative XY rule proposal")
    p.add_argument("--perm",help="optional JSON state permutation for --evolve-rule")
    a = p.parse_args()
    try:
        stream(a)
    except KeyboardInterrupt:
        print("HSI XY stream interrupted; checkpoint retained.",file=sys.stderr)
        return 130
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired,KeyError,IndexError) as exc:
        print("HSI XY stream HOLD: "+str(exc),file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
