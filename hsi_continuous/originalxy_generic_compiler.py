#!/usr/bin/env python3
"""Generic exact OriginalXY transition-table compiler and finite verifier.

k active states 0..k-1, designated halt state k, two tape symbols.
Each row [next_state, direction, write_bit], direction 0=left, 1=right.
Rows are ordered (state 0/read 0, state 0/read 1, ...).
The program is an exact integer in OriginalXY's triangular enumeration.
"""
import argparse
import json
from math import isqrt

def validate(k,rules):
    if type(k)!=int or not 1<=k<=32 or not isinstance(rules,list) or len(rules)!=2*k:
        raise ValueError("invalid state count or rule table length")
    for row in rules:
        if not isinstance(row,list) or len(row)!=3:
            raise ValueError("each rule must be [next_state,direction,write_bit]")
        q,d,w=row
        if type(q)!=int or not 0<=q<=k or type(d)!=int or d not in (0,1) or type(w)!=int or w not in (0,1):
            raise ValueError("invalid transition rule")

def compile_table(k,rules):
    validate(k,rules)
    base=4*(k+1)
    c=sum((q+(k+1)*(d+2*w))*base**i for i,(q,d,w) in enumerate(rules))
    # Padding above the used transition digits keeps p positive even if c=0.
    if c==0:
        c=base**(2*k)
    z=c+k-1
    return z*(z+1)//2+c

def decode_program(p):
    if type(p)!=int or p<1:raise ValueError("positive program required")
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    if not 1<=k<=32:raise ValueError("unsupported state count")
    base=4*(k+1)
    rules=[]
    for i in range(2*k):
        v=c//base**i%base
        q=v%(k+1);v//=k+1
        d=v%2;v//=2
        rules.append([q,d,v%2])
    return k,rules

def run_table(k,rules,word,steps):
    validate(k,rules)
    if any(b not in "01" for b in word) or not 0<=steps<=4096:
        raise ValueError("invalid tape or step budget")
    marked={i for i,b in enumerate(word) if b=="1"}
    q=h=0
    trace=[]
    for _ in range(steps):
        if q==k:break
        nq,d,w=rules[2*q+int(h in marked)]
        if w:marked.add(h)
        else:marked.discard(h)
        h+=2*d-1
        q=nq
        trace.append([q,h,sorted(marked)])
    return {"state":[q,h,sorted(marked)],"halted":q==k,"trace":trace}

def run_program(p,word,steps):
    k,rules=decode_program(p)
    return run_table(k,rules,word,steps)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--states",type=int,default=2)
    ap.add_argument("--rules",default="[[1,1,1],[2,0,0],[2,0,1],[2,0,0]]")
    ap.add_argument("--word",default="0")
    ap.add_argument("--steps",type=int,default=8)
    a=ap.parse_args()
    rules=json.loads(a.rules)
    p=compile_table(a.states,rules)
    k,decoded=decode_program(p)
    assert (k,decoded)==(a.states,rules)
    actual=run_program(p,a.word,a.steps)
    assert actual==run_table(a.states,rules,a.word,a.steps)
    print(json.dumps({"protocol":"HSI-OX-GENERIC-TABLE/0.1",
      "states":k,"program":str(p),"rules":decoded,"result":actual,
      "exact_roundtrip":True,"table_equivalence":True,
      "bounded":True,"halting_decider":False},separators=(",",":")))

if __name__=="__main__":main()
