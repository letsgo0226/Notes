#!/usr/bin/env python3
"""Exact bounded OriginalXY binary decrement on little-endian tape.

q=0: borrow. On 0 write 1, move right, continue; on 1 write 0,
move right, halt. Python orchestrates the finite step budget.
Input must be strictly positive to avoid infinite borrow.
"""
import argparse
import json
from math import isqrt

def program():
    # k=1, base=8; digit(read0)=4 (write1, left, continue)
    # digit(read1)=3 (write0, right, halt).
    # For both rules move right, read0 digit=6, read1 digit=3.
    c=6+8*3
    z=c
    return z*(z+1)//2+c

def decrement(n,max_steps=128):
    if type(n)!=int or n<=0:raise ValueError("positive integer required")
    if not 1<=max_steps<=4096:raise ValueError("invalid bound")
    marked={i for i in range(n.bit_length()) if n>>i&1}
    p=program()
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    base=4*(k+1)
    q=h=steps=0
    while q!=k and steps<max_steps:
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
    if q!=k:raise RuntimeError("step bound reached")
    result=sum(1<<i for i in marked)
    return {"input":str(n),"output":str(result),"steps":steps,
            "program":str(p),"halted":True}

def subtract(a,b,budget=4096):
    if type(a)!=int or type(b)!=int or a<0 or b<0 or b>a:
        raise ValueError("require nonnegative a >= b")
    if b>budget:raise ValueError("iteration budget exceeded")
    current=a
    transitions=0
    for _ in range(b):
        r=decrement(current)
        current=int(r["output"])
        transitions+=r["steps"]
    return {"a":str(a),"b":str(b),"difference":str(current),
            "decrement_calls":b,"originalxy_transitions":transitions}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("pairs",nargs="*",type=int,default=[1,1,8,1,15,7,256,1])
    a=ap.parse_args()
    if len(a.pairs)%2:ap.error("expected pairs")
    results=[subtract(x,y) for x,y in zip(a.pairs[::2],a.pairs[1::2])]
    print(json.dumps({"protocol":"HSI-OX-NATIVE-BORROW/0.1",
        "results":results,"exact_integer":True,
        "originalxy_tape_borrow":True,"python_loop_control":True},
        separators=(",",":")))
if __name__=="__main__":main()
