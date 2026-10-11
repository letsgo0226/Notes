#!/usr/bin/env python3
"""Single-program OriginalXY unary loop, zero branch, and tape output.

Tape input: n consecutive 1 cells from head 0, then blank 0.
q0/read1: erase 1, move right, continue q0 (unary decrement).
q0/read0: write 1 at first blank, move right, halt q1.
The final 1 is a completion marker at cell n, not an arithmetic sum.
OriginalXY chooses every loop iteration and the terminating branch.
Python only simulates transitions and enforces a finite safety budget.
"""
import argparse
import json
from math import isqrt

def compile_program():
    k=1
    base=4*(k+1)
    # read0: next q1, right, write1 => 7
    # read1: next q0, right, write0 => 2
    c=7+base*2
    z=c
    return z*(z+1)//2+c

def execute(n,limit=4096):
    if type(n)!=int or n<0 or n>=limit:
        raise ValueError("nonnegative unary count below safety limit required")
    marked=set(range(n))
    p=compile_program()
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    base=4*(k+1)
    q=h=steps=0
    trace=[]
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
        trace.append([q,h,sorted(marked)])
    if q!=k:raise RuntimeError("safety bound reached")
    return {"initial_count":n,"steps":steps,"halted":True,
            "completion_marker_at":h-1,"final_marks":sorted(marked),
            "trace":trace}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("counts",nargs="*",type=int,default=[0,1,2,7,31])
    ap.add_argument("--limit",type=int,default=4096)
    a=ap.parse_args()
    results=[execute(n,a.limit) for n in a.counts]
    print(json.dumps({"protocol":"HSI-OX-UNARY-INTEGRATED-LOOP/0.1",
        "program":str(compile_program()),"results":results,
        "loop_and_halt":"single OriginalXY program",
        "python_loop_control":False,
        "binary_counter":False},separators=(",",":")))
if __name__=="__main__":main()
