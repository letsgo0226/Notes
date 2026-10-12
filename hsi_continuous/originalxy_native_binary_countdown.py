#!/usr/bin/env python3
"""Native OriginalXY binary countdown loop on an interleaved finite word.

Data cells: bit i at 2*i+2, structural markers at 2*i+1.
Cell 0 and -1 are blank boundary probes; terminator at 2*width+1 blank.
The single compiled OriginalXY program repeatedly subtracts one from the
binary word, returns its head to the least significant bit, and halts
after the all-zero word attempts another decrement. The final word is
then all ones (underflow), and a terminal mark is written at terminator.
Python encodes input and simulates transitions with a safety bound.
"""
import argparse
import json
from math import isqrt
from originalxy_generic_compiler import compile_table,decode_program

K=8
# [next state, move right (1) / left (0), write bit]
RULES=[
    [1,1,1],[2,0,0], # q0: borrow 0->1 carry, 1->0 return
    [8,1,1],[0,1,1], # q1: blank terminator -> mark+halt; marker -> next bit
    [8,1,0],[3,0,1], # q2: return marker
    [4,0,0],[2,0,1], # q3: return data; if 0 probe preceding marker
    [6,1,0],[5,1,1], # q4: blank left boundary / marker
    [2,0,0],[2,0,1], # q5: return across zero data
    [7,1,0],[7,1,1], # q6: step from left boundary
    [8,1,0],[0,1,1], # q7: marker -> begin next decrement
]

def execute(n,width,limit=100000):
    if type(n)!=int or type(width)!=int or not 1<=width<=12 or not 0<=n<1<<width:
        raise ValueError("require 1<=width<=12 and 0<=n<2**width")
    p=compile_table(K,RULES)
    k,decoded=decode_program(p)
    assert k==K and decoded==RULES
    marked={2*i+1 for i in range(width)}
    marked.update(2*i+2 for i in range(width) if n>>i&1)
    q,h,steps=0,2,0
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    base=4*(k+1)
    while q!=k and steps<limit:
        bit=int(h in marked)
        v=c//base**(2*q+bit)%base
        nq=v%(k+1);v//=k+1
        right=v%2;v//=2
        write=v%2
        if write:marked.add(h)
        else:marked.discard(h)
        h+=2*right-1
        q=nq
        steps+=1
    if q!=k:raise RuntimeError("step budget exhausted")
    terminator=2*width+1
    return {"input":n,"width":width,"steps":steps,"halted":True,
            "terminal_mark":int(terminator in marked),
            "final_bits":"".join(str(int(2*i+2 in marked)) for i in range(width)),
            "head":h}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--width",type=int,default=4)
    ap.add_argument("--limit",type=int,default=100000)
    ap.add_argument("values",type=int,nargs="*",default=[0,1,2,3,7,15])
    a=ap.parse_args()
    results=[execute(n,a.width,a.limit) for n in a.values]
    print(json.dumps({"protocol":"HSI-OX-NATIVE-BINARY-COUNTDOWN/0.1",
        "program":str(compile_table(K,RULES)),
        "results":results,"native_loop_control":True,
        "underflow_halt":True,"initial_encoding_by_python":True,
        "unbounded_halting_proof":False},separators=(",",":")))
if __name__=="__main__":main()
