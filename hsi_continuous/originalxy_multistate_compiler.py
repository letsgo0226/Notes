#!/usr/bin/env python3
"""Compile and run bounded two-state OriginalXY programs using exact integers.

Two active states q=0,1, one halt state q=2, binary tape.
Rules: [next_state, move_right, write_bit] for (q,read_bit).
The OriginalXY program integer uses the original triangular enumeration.
"""
import argparse
import json
from math import isqrt

K=2
BASE=4*(K+1)

def compile_rules(rules):
    if len(rules)!=4 or any(not isinstance(r,list) or len(r)!=3 for r in rules):
        raise ValueError("expected four [next_state,move_right,write_bit] rules")
    c=0
    for i,(q,move,write) in enumerate(rules):
        if type(q)!=int or not 0<=q<=K or type(move)!=int or move not in (0,1) or type(write)!=int or write not in (0,1):
            raise ValueError("invalid transition")
        digit=q+(K+1)*(move+2*write)
        c+=digit*BASE**i
    z=c+K-1
    p=z*(z+1)//2+c
    return p

def decode(p):
    if p<1:raise ValueError("positive program required")
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    if k!=K:raise ValueError("not a two-state program")
    return c,k

def run(p,word,limit):
    if not word or any(b not in "01" for b in word) or not 0<=limit<=64:
        raise ValueError("invalid word or bound")
    c,k=decode(p)
    marked={i for i,b in enumerate(word) if b=="1"}
    q=h=0
    trace=[]
    for t in range(limit):
        if q==k:break
        bit=int(h in marked)
        v=c//BASE**(2*q+bit)%BASE
        nq=v%(k+1);v//=k+1
        move=v%2;v//=2
        write=v%2
        if write:marked.add(h)
        else:marked.discard(h)
        h+=2*move-1
        q=nq
        trace.append({"step":t+1,"state":[q,h,sorted(marked)]})
        if q==k:break
    return {"state":[q,h,sorted(marked)],"status":"HALTED" if q==k else "UNRESOLVED","trace":trace}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rules",default="[[1,1,1],[2,0,0],[2,0,1],[2,0,0]]")
    ap.add_argument("--word",default="0")
    ap.add_argument("--steps",type=int,default=8)
    a=ap.parse_args()
    rules=json.loads(a.rules)
    p=compile_rules(rules)
    c,k=decode(p)
    assert c==sum((q+(k+1)*(m+2*w))*BASE**i for i,(q,m,w) in enumerate(rules))
    output=run(p,a.word,a.steps)
    print(json.dumps({"protocol":"HSI-OX-TWO-STATE/0.1","program":str(p),
                      "rules":rules,"input":a.word,"output":output,
                      "native_originalxy_transition":True,
                      "bounded":True,"general_arithmetic_compiler":False},
                     separators=(",",":")))
if __name__=="__main__":main()
