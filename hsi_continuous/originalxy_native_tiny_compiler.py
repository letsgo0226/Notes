#!/usr/bin/env python3
"""Compile a tiny integer instruction to an OriginalXY transition table.

Verified scope: one-step unary operations on the scanned bit at head 0.
The generated OriginalXY program number executes through the unmodified
OriginalXY transition decoding equations. No arbitrary-program compiler.
"""
import argparse
import json
from math import isqrt

def encode_rule(write, move_right, halt=True):
    # OriginalXY: p -> triangular (z,c), k=z-c+1,
    # v=c // (4*(k+1))**(2*q+bit) % (4*(k+1)).
    # For k=1, q=0, scanned bit=0, v=0..7.
    # v=(next_state)+(k+1)*(direction+2*write)
    k=1
    v=(1 if halt else 0)+2*((1 if move_right else 0)+2*write)
    # choose z with c=z, giving k=1, and c mod 8=v
    z=v if v else 8
    c=z
    p=z*(z+1)//2+c
    return p

def decode_step(p, word="0"):
    if p<1 or word not in ("0","1"): raise ValueError("only single bit supported")
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    base=4*(k+1)
    marked=set([0]) if word=="1" else set()
    bit=int(0 in marked)
    v=c//base**bit%base
    q=v%(k+1);v//=k+1
    h=2*(v%2)-1;v//=2
    if v%2:marked.add(0)
    else:marked.discard(0)
    return {"state":[q,h,sorted(marked)],"halted":q==k}

def compile_op(op):
    if op=="write1_right":return encode_rule(1,True)
    if op=="write0_left":return encode_rule(0,False)
    raise ValueError("unsupported instruction")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--op",choices=["write1_right","write0_left"],default="write1_right")
    a=ap.parse_args()
    p=compile_op(a.op)
    # Validate against the same OriginalXY bit-level transition semantics.
    result=decode_step(p,"0")
    expected=[1,1,[0]] if a.op=="write1_right" else [1,-1,[]]
    assert result["state"]==expected and result["halted"]
    print(json.dumps({"protocol":"HSI-OX-NATIVE-TINY-COMPILER/0.1",
      "operation":a.op,"program":p,"input":"0","output":result,
      "native_originalxy_transition":True,
      "arbitrary_program_compiler":False},separators=(",",":")))
if __name__=="__main__":main()
