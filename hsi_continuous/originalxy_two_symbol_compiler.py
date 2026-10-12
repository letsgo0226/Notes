#!/usr/bin/env python3
"""Exact OriginalXY two-symbol, one-state transition compiler.

A table has one rule per scanned bit, encoded into the OriginalXY program
number. Each rule is (write_bit, move_right, halt). This restricted compiler
always halts after one step; it is NOT an arbitrary integer DSL compiler.
"""
import argparse
import json
from math import isqrt

def compile_table(rules):
    if len(rules)!=2 or any(len(r)!=2 or any(type(v)!=int or v not in (0,1) for v in r) for r in rules):
        raise ValueError("two [write,move_right] binary rules required")
    # k=1: state 0 is active, state 1 halts.
    # digit = 1 + 2*(move_right + 2*write_bit), in 1,3,5,7.
    d=[1+2*(move+2*write) for write,move in rules]
    c=d[0]+8*d[1]
    # choose z=c => k=z-c+1=1.
    z=c
    p=z*(z+1)//2+c
    return p

def execute(p,word):
    if p<1 or word not in ("0","1"):raise ValueError("one bit input required")
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    b=4*(k+1)
    bit=int(word)
    v=c//b**bit%b
    q=v%(k+1);v//=k+1
    h=2*(v%2)-1;v//=2
    write=v%2
    return {"state":[q,h,[0] if write else []],"halted":q==k,"output_bit":write}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rules",default="[[1,1],[0,0]]",
                    help="JSON [[write_on_zero,move_right],[write_on_one,move_right]]")
    a=ap.parse_args()
    rules=json.loads(a.rules)
    p=compile_table(rules)
    outcomes={}
    for bit in (0,1):
        r=execute(p,str(bit))
        assert r["output_bit"]==rules[bit][0]
        assert r["state"][1]==(1 if rules[bit][1] else -1)
        assert r["halted"]
        outcomes[str(bit)]=r
    print(json.dumps({"protocol":"HSI-OX-NATIVE-TWO-SYMBOL/0.1",
                      "program":p,"rules":rules,"outcomes":outcomes,
                      "native_originalxy_transition":True,
                      "bounded_one_step":True,
                      "general_arithmetic_compiler":False},separators=(",",":")))
if __name__=="__main__":main()
