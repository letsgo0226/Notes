#!/usr/bin/env python3
"""Bounded exact integer addition using repeated OriginalXY tape increments.

The carry operation is a genuine OriginalXY transition program.
Python orchestrates b iterations; b is NOT yet read from an OriginalXY tape.
"""
import argparse
import json
from originalxy_binary_increment import increment

def add(a,b,max_iterations=4096):
    if type(a)!=int or type(b)!=int or a<0 or b<0:
        raise ValueError("nonnegative integer operands required")
    if b>max_iterations:raise ValueError("iteration budget exceeded")
    current=a
    transitions=0
    for _ in range(b):
        r=increment(current)
        current=int(r["output"])
        transitions+=r["steps"]
    return {"a":str(a),"b":str(b),"sum":str(current),
            "increment_calls":b,"originalxy_transitions":transitions,
            "arithmetic_core":"OriginalXY binary carry",
            "loop_control":"Python bounded"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("pairs",nargs="*",type=int,default=[0,0,1,2,7,5,15,1,31,9])
    a=ap.parse_args()
    if len(a.pairs)%2:ap.error("expected even number of integers")
    results=[add(x,y) for x,y in zip(a.pairs[::2],a.pairs[1::2])]
    print(json.dumps({"protocol":"HSI-OX-EXACT-ADDITION/0.1",
                      "results":results,"exact_integer":True,
                      "pure_originalxy_loop_control":False},
                     separators=(",",":")))
if __name__=="__main__":main()
