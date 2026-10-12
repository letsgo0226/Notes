#!/usr/bin/env python3
"""Native OriginalXY binary borrow machine with tape-determined halt.

One active state q=0, halt state q=1. A 0 bit becomes 1 and borrow
continues right; a 1 bit becomes 0 and the machine halts. Input n>0.
Python provides tape simulation and a safety bound, not borrow branching.
"""
import argparse
import json
from math import isqrt

def compile_program():
    # k=1, base=8. read0 -> q0,right,write1 => digit=6
    # read1 -> q1,right,write0 => digit=3.
    c=6+8*3
    z=c
    return z*(z+1)//2+c

def execute(n,limit=4096):
    if type(n)!=int or n<=0:raise ValueError("positive binary integer required")
    if not 1<=limit<=100000:raise ValueError("invalid step budget")
    marked={i for i in range(n.bit_length()) if n>>i&1}
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
        trace.append({"q":q,"head":h,"marked":sorted(marked)})
    if q!=k:raise RuntimeError("bounded run unresolved")
    result=sum(1<<i for i in marked)
    return {"input":str(n),"output":str(result),"steps":steps,
            "halted":True,"trace":trace}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("integers",nargs="*",type=int,default=[1,2,3,8,16,255,256])
    ap.add_argument("--limit",type=int,default=4096)
    a=ap.parse_args()
    results=[execute(n,a.limit) for n in a.integers]
    print(json.dumps({"protocol":"HSI-OX-BINARY-BORROW-MACHINE/0.1",
        "program":str(compile_program()),"results":results,
        "branching":"OriginalXY tape transition",
        "halt":"OriginalXY state transition",
        "zero_test_for_outer_loop":False},separators=(",",":")))
if __name__=="__main__":main()
