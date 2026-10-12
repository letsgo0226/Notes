#!/usr/bin/env python3
"""Bounded E257 arithmetic composed from OriginalXY tape increment.

All arithmetic results are exact integers. Repeated increment is native to
OriginalXY's tape transition rules, but Python controls the loops.
This is deliberately limited to short byte strings to bound runtime.
"""
import argparse
import json
from originalxy_exact_addition import add

def multiply(a,b,budget=4096):
    if type(a)!=int or type(b)!=int or a<0 or b<0:
        raise ValueError("nonnegative operands required")
    if a*b>budget:raise ValueError("operation budget exceeded")
    x=0
    steps=0
    for _ in range(b):
        r=add(x,a,max_iterations=budget)
        x=int(r["sum"])
        steps+=r["originalxy_transitions"]
    return x,steps

def e257_bytes(data,budget=4096):
    if not isinstance(data,(bytes,bytearray)):raise ValueError("bytes required")
    n=1
    transitions=0
    for b in data:
        n,t=multiply(n,257,budget)
        transitions+=t
        r=add(n,b+1,max_iterations=budget)
        n=int(r["sum"])
        transitions+=r["originalxy_transitions"]
    return n,transitions

def d257_bytes(n):
    if type(n)!=int or n<1:raise ValueError("positive E257 integer required")
    out=[]
    while n>1:
        n,r=divmod(n,257)
        if not r:raise ValueError("invalid E257 digit")
        out.append(r-1)
    return bytes(reversed(out))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--hex",default="00")
    ap.add_argument("--budget",type=int,default=4096)
    a=ap.parse_args()
    raw=bytes.fromhex(a.hex)
    encoded,steps=e257_bytes(raw,a.budget)
    decoded=d257_bytes(encoded)
    assert decoded==raw
    print(json.dumps({"protocol":"HSI-OX-E257-BOUNDED/0.1",
        "input_hex":raw.hex(),"encoded":str(encoded),"decoded_hex":decoded.hex(),
        "originalxy_transitions":steps,"roundtrip":True,
        "integer_exact":True,"python_loop_control":True,
        "python_division_for_decoding":True},separators=(",",":")))
if __name__=="__main__":main()
