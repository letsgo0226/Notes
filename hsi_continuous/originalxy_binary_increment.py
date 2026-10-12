#!/usr/bin/env python3
"""OriginalXY-native binary increment, little-endian tape, bounded exact steps.

States: 0=carry, 1=halt (k=1). For scanned 1: write 0, move right,
stay in carry. For scanned 0: write 1, move right, halt.
The machine operates on the finite marked-cell set, never using Python n+1.
"""
import argparse
import json
from math import isqrt

def program():
    # k=1, base=8. (read0 -> halt,right,write1) digit=7.
    # (read1 -> carry,right,write0) digit=2.
    c=7+8*2
    z=c
    return z*(z+1)//2+c

def transition(p,q,h,marked):
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    b=4*(k+1)
    bit=int(h in marked)
    v=c//b**(2*q+bit)%b
    nq=v%(k+1);v//=k+1
    move=v%2;v//=2
    write=v%2
    if write:marked.add(h)
    else:marked.discard(h)
    return nq,h+(2*move-1),marked

def increment(n,max_steps=128):
    if type(n)!=int or n<0:raise ValueError("nonnegative integer required")
    if not 1<=max_steps<=4096:raise ValueError("invalid step limit")
    marked={i for i in range(n.bit_length()) if n>>i&1}
    p=program()
    q=h=0
    steps=0
    while q!=1 and steps<max_steps:
        q,h,marked=transition(p,q,h,marked)
        steps+=1
    if q!=1:raise RuntimeError("step bound reached")
    result=sum(1<<i for i in marked)
    return {"input":str(n),"output":str(result),"steps":steps,
            "program":str(p),"state":[q,h,sorted(marked)],"halted":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("integers",nargs="*",type=int,default=[0,1,2,3,7,15,255])
    a=ap.parse_args()
    results=[increment(n) for n in a.integers]
    print(json.dumps({"protocol":"HSI-OX-NATIVE-BINARY-INCREMENT/0.1",
        "results":results,"native_tape_arithmetic":True,
        "general_integer_arithmetic":False},separators=(",",":")))
if __name__=="__main__":main()
