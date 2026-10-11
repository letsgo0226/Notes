#!/usr/bin/env python3
"""Native OriginalXY self-delimiting zero-test with distinct halt outcomes.

Input code: data bit 0 -> 10, 1 -> 11, end -> 00.
States q0=prefix/no-1, q1=payload/no-1, q2=prefix/saw-1,
q3=payload/saw-1, q4=halt-zero, q5=halt-nonzero.
OriginalXY uses one designated halting state q=k. Therefore this
implementation uses q5 as the sole halt and encodes the result in the
final head movement / tape mark on the terminator cell. It does NOT
have two distinct terminal states.
"""
import argparse
import json
from math import isqrt

K=5
BASE=4*(K+1)

def compile_program():
    # Each transition is (next_q,move_right,write_bit).
    # q0: prefix 0 => halt q5, move right, write0; prefix1 => q1.
    # q1: payload 0 => q0; payload1 => q2 (saw one).
    # q2: prefix 0 => halt q5, move right, write1; prefix1 => q3.
    # q3: payload 0/1 => q2.
    rules=[(5,1,0),(1,1,1),
           (0,1,0),(2,1,1),
           (5,1,1),(3,1,1),
           (2,1,0),(2,1,1)]
    c=0
    for i,(q,move,write) in enumerate(rules):
        c+=(q+(K+1)*(move+2*write))*BASE**i
    z=c+K-1
    return z*(z+1)//2+c

def execute(bits,limit=4096):
    if any(b not in "01" for b in bits):raise ValueError("binary bits only")
    tape="".join("1"+b for b in bits)+"00"
    marked={i for i,b in enumerate(tape) if b=="1"}
    p=compile_program()
    z=(isqrt(8*p+1)-1)//2
    c=p-z*(z+1)//2
    k=z-c+1
    base=4*(k+1)
    q=h=steps=0
    terminator=len(tape)-2
    while q!=k and steps<limit:
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
    if q!=k:raise RuntimeError("step bound unresolved")
    return {"input_bits":bits,"is_zero":terminator not in marked,
            "steps":steps,"halted":True,
            "result_mark_at_terminator":int(terminator in marked)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("bitstrings",nargs="*",default=["","0","00","1","00100","1111","000100"])
    a=ap.parse_args()
    results=[execute(b) for b in a.bitstrings]
    print(json.dumps({"protocol":"HSI-OX-NATIVE-DELIMITED-ZERO/0.1",
        "program":str(compile_program()),"results":results,
        "decision":"OriginalXY terminal tape mark",
        "native_end_detection":True,"python_zero_decision":False,
        "distinct_halt_states":False},separators=(",",":")))
if __name__=="__main__":main()
