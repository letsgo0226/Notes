#!/usr/bin/env python3
"""OriginalXY-native unary countdown, exact integer program and tape.

Initial tape: n consecutive marked cells at positions 0..n-1, followed
by blank. q=0 on marked 1: erase and move right, stay q=0.
On blank 0: keep blank, move right, halt q=1.
Thus n+1 OriginalXY transitions, with termination decided by the tape.
Python only enforces a safety step budget.
"""
import argparse
import json
from math import isqrt

def compile_program():
    k=1
    base=4*(k+1)
    # q0, read0: halt, move right, write0 => digit=3
    # q0, read1: continue, move right, write0 => digit=2
    c=3+base*2
    z=c
    return z*(z+1)//2+c

def run(n,limit=4096):
    if type(n)!=int or not 0<=n<=limit-1:raise ValueError("counter exceeds budget")
    p=compile_program()
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    base=4*(k+1)
    marked=set(range(n))
    q=h=steps=0
    while q!=k and steps<limit:
        bit=int(h in marked)
        v=c//base**(2*q+bit)%base
        nq=v%(k+1);v//=k+1
        move=v%2;v//=2
        write=v%2
        if write:marked.add(h)
        else:marked.discard(h)
        h+=2*move-1
        q=nq
        steps+=1
    if q!=k:raise RuntimeError("step bound exceeded")
    assert not marked
    return {"initial_count":n,"steps":steps,"halted":True,
            "final_state":[q,h,sorted(marked)]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("counts",nargs="*",type=int,default=[0,1,2,7,31])
    ap.add_argument("--limit",type=int,default=4096)
    a=ap.parse_args()
    results=[run(n,a.limit) for n in a.counts]
    print(json.dumps({"protocol":"HSI-OX-NATIVE-TAPE-COUNTDOWN/0.1",
        "program":str(compile_program()),"results":results,
        "loop_condition":"OriginalXY tape symbol",
        "halt_condition":"OriginalXY state transition",
        "python_role":"step budget and tape simulation",
        "binary_integer_counter":False},separators=(",",":")))
if __name__=="__main__":main()
