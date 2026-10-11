#!/usr/bin/env python3
"""Finite HSI-OriginalXY UTM -> Gödel -> Dirichlet -> bounded feedback.

The mathematical operations are implemented by a conventional Python interpreter.
They are *not* a new primitive UTM language or a proof of AI-equivalent learning.
No network, broker, deployment, or source modification occurs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "Notes"
SOURCE = NOTES / "HSI_Prime_Analytic_2KB_Release" / "OriginalXY_reference.py"
PROTOCOL = "HSI-UTM-DIRICHLET-FEEDBACK/0.1"

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def e257(value):
    n = 1
    for b in canonical(value).encode("utf-8"):
        n = n * 257 + b + 1
    return n

def d257(n):
    if n < 1:
        raise ValueError("invalid E257 integer")
    a = []
    while n > 1:
        n, r = divmod(n, 257)
        if not r:
            raise ValueError("invalid E257 digit")
        a.append(r - 1)
    return json.loads(bytes(reversed(a)))

def unpair(n):
    if n < 0:
        raise ValueError("negative index")
    w = (math.isqrt(8*n + 1) - 1)//2
    b = n - w*(w+1)//2
    return b, w-b

def utm_step(program, state):
    """One exact finite transition matching Notes/OriginalXY_reference.py."""
    p = int(program)
    if p < 1:
        raise ValueError("program must be positive")
    z = (math.isqrt(8*p+1)-1)//2
    c = p-z*(z+1)//2
    k = z-c+1
    base = 4*(k+1)
    q, h, marked = state
    marked = set(marked)
    bit = int(h in marked)
    v = c // base**(2*q+bit) % base
    nq = v % (k+1)
    v //= k+1
    nh = h + 2*(v%2)-1
    v //= 2
    if v%2:
        marked.add(h)
    else:
        marked.discard(h)
    return (nq, nh, tuple(sorted(marked))), nq == k

def finite_utm(program, word, steps):
    if steps < 0 or steps > 512:
        raise ValueError("bounded steps must be in 0..512")
    if not word or any(c not in "01" for c in word):
        raise ValueError("word must be a nonempty binary string")
    state = (0, 0, tuple(i for i,c in enumerate(word) if c == "1"))
    z = (math.isqrt(8*program+1)-1)//2
    c = program-z*(z+1)//2
    halt_state = z-c+1
    trace = []
    for i in range(steps):
        if state[0] == halt_state:
            break
        nxt, halted = utm_step(program, state)
        trace.append({"step": i+1, "x": str(e257([program,*state])),
                      "y": str(e257([program,*nxt]))})
        state = nxt
        if halted:
            break
    return {"state": [state[0], state[1], list(state[2])],
            "status": "HALTED" if state[0] == halt_state else "UNRESOLVED",
            "trace": trace}

def spectral(x, nterms):
    """Finite Dirichlet polynomial at s=2+i*x; coefficients 1 or -1."""
    if not 1 <= nterms <= 256:
        raise ValueError("terms must be 1..256")
    re = im = 0.0
    for n in range(1, nterms+1):
        theta = x*math.log(n)
        coeff = 1.0 if n % 2 else -1.0
        re += coeff*math.cos(theta)/(n*n)
        im -= coeff*math.sin(theta)/(n*n)
    return re, im

def solve(program, word, steps, terms, rounds):
    if not 1 <= rounds <= 64:
        raise ValueError("rounds must be 1..64")
    run = finite_utm(program, word, steps)
    state_code = e257([program, run["state"]])
    assert d257(state_code) == [program, run["state"]]
    x = (state_code % 1000003)/1000003.0
    feedback = []
    for t in range(rounds):
        re, im = spectral(x, terms)
        y = math.tanh(re + im)
        x_next = 0.75*x + 0.25*(y+1)/2
        feedback.append({"iteration": t, "x": x, "y": y,
                         "x_next": x_next, "residual": abs(x_next-x)})
        x = x_next
    return {"protocol": PROTOCOL,
            "source": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "parameters": {"program": program, "word": word, "steps": steps,
                           "terms": terms, "rounds": rounds},
            "utm": run, "state_godel": str(state_code),
            "feedback": feedback, "bounded": True,
            "claims": {"ai_equivalent": False, "halting_decider": False,
                       "analytic_continuation_proven": False,
                       "real_world_deployment": False}}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", type=int, default=2)
    ap.add_argument("--word", default="1")
    ap.add_argument("--steps", type=int, default=16)
    ap.add_argument("--terms", type=int, default=16)
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--out", default="hsi_continuous/out/feedback.json")
    a = ap.parse_args()
    result = solve(a.program, a.word, a.steps, a.terms, a.rounds)
    out = (ROOT / a.out).resolve()
    if not out.is_relative_to(ROOT) or out.is_relative_to(NOTES.resolve()):
        raise ValueError("output must be inside repository but outside Notes")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(f"{PROTOCOL}: {result['utm']['status']}; "
          f"{len(result['utm']['trace'])} UTM transitions; "
          f"{len(result['feedback'])} feedback iterations; saved {out.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
