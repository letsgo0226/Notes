#!/usr/bin/env python3
"""OriginalXY-native bounded-width binary zero detector.

Tape layout: a binary word occupying positions [0,width). q0 scans
without seeing a set bit; q1 scans after seeing a set bit; q2 is an
unused halt state. The scan boundary is enforced by the Python harness,
NOT by OriginalXY itself. This is not a fully native zero decider.
"""
import argparse
import json
from math import isqrt

def compile_program():
    # k=2; base=12. Four transition digits (q0/1 x read0/1).
    # q0 read0 -> q0,right,write0 = 3
    # q0 read1 -> q1,right,write1 = 10
    # q1 read0 -> q1,right,write0 = 4
    # q1 read1 -> q1,right,write1 = 10
    digits=[3,10,4,10]
    c=sum(v*12**i for i,v in enumerate(digits))
    z=c+1
    return z*(z+1)//2+c

def scan(n,width,limit=4096):
    if type(n)!=int or type(width)!=int or n<0 or not 1<=width<=1024 or n>=1<<width:
        raise ValueError("invalid bounded-width integer")
    if width>limit:raise ValueError("step budget exceeded")
    marked={i for i in range(width) if n>>i&1}
    p=compile_program()
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    base=4*(k+1)
    q=h=steps=0
    while h<width and steps<limit:
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
    if h!=width:raise RuntimeError("scan incomplete")
    return {"input":str(n),"width":width,"is_zero":q==0,
            "steps":steps,"final_state":q,"program":str(p)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--width",type=int,default=8)
    ap.add_argument("integers",nargs="*",type=int,default=[0,1,2,7,128,255])
    a=ap.parse_args()
    results=[scan(n,a.width) for n in a.integers]
    print(json.dumps({"protocol":"HSI-OX-BOUNDED-ZERO-SCAN/0.1",
        "results":results,"bit_scan":"OriginalXY transitions",
        "width_termination":"Python harness",
        "fully_native_zero_decider":False},separators=(",",":")))
if __name__=="__main__":main()
