#!/usr/bin/env python3
"""Self-delimiting binary data scan using native OriginalXY transitions.

Encoding of each data bit: 0 -> 10, 1 -> 11, terminator -> 00.
A finite OriginalXY machine reads the first bit of each pair; 0 means
end, 1 means a data pair, then it reads the second bit and advances.
The machine detects the boundary without Python's width condition.
States q0=prefix, q1=payload, q2=halt. The two-tape-symbol encoding
does not permit raw 00 within the encoded data stream.
"""
import argparse
import json
from math import isqrt

K=2
BASE=4*(K+1)

def compile_program():
    # digits indexed by 2*q+bit.
    # q0 prefix 0 -> halt q2, right, write0 => 5
    # q0 prefix 1 -> payload q1, right, write1 => 10
    # q1 payload 0 -> prefix q0, right, write0 => 3
    # q1 payload 1 -> prefix q0, right, write1 => 9
    digits=[5,10,3,9]
    c=sum(d*BASE**i for i,d in enumerate(digits))
    z=c+K-1
    return z*(z+1)//2+c

def encode_bits(bits):
    if any(bit not in "01" for bit in bits):raise ValueError("binary bits required")
    return "".join("1"+b for b in bits)+"00"

def run(bits,limit=4096):
    tape=encode_bits(bits)
    if len(tape)>limit:raise ValueError("step budget too small")
    marked={i for i,b in enumerate(tape) if b=="1"}
    p=compile_program()
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    q=h=steps=0
    while q!=k and steps<limit:
        bit=int(h in marked)
        v=c//BASE**(2*q+bit)%BASE
        nq=v%(k+1);v//=k+1
        move=v%2;v//=2
        write=v%2
        if write:marked.add(h)
        else:marked.discard(h)
        h+=2*move-1
        q=nq
        steps+=1
    if q!=k:raise RuntimeError("unresolved within step budget")
    return {"input_bits":bits,"encoded_tape":tape,
            "steps":steps,"halted":True,"head":h,
            "expected_steps":2*len(bits)+1,
            "native_boundary_detection":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("bitstrings",nargs="*",default=["","0","1","00101","111111"])
    a=ap.parse_args()
    results=[run(bits) for bits in a.bitstrings]
    print(json.dumps({"protocol":"HSI-OX-SELF-DELIMITING-TAPE/0.1",
        "program":str(compile_program()),"results":results,
        "delimiter":"00 following 10/11 pairs",
        "python_role":"input encoding and bounded step simulation",
        "native_delimiter_scan":True,
        "native_integer_zero_test":False},separators=(",",":")))
if __name__=="__main__":main()
