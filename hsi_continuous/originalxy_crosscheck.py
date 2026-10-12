#!/usr/bin/env python3
"""Cross-component property checks for bounded OriginalXY arithmetic.

This is a finite regression suite, not a proof of general correctness.
It checks the exact integer program decoder, arithmetic transitions,
self-delimited scan and native zero-result marking.
"""
import json
from originalxy_binary_increment import increment
from originalxy_binary_borrow_machine import execute as borrow
from originalxy_integrated_unary_loop import execute as unary_loop
from originalxy_self_delimiting_tape import run as delimited
from originalxy_native_zero_decider import execute as zero_decide
from originalxy_multistate_compiler import compile_rules,run as multistate_run

def main():
    checks=0
    for n in range(128):
        a=increment(n,max_steps=256)
        assert int(a["output"])==n+1
        checks+=1
        if n:
            b=borrow(n,limit=256)
            assert int(b["output"])==n-1
            checks+=1
        u=unary_loop(n,limit=256)
        assert u["steps"]==n+1 and u["final_marks"]==[n]
        checks+=1
    for n in range(64):
        bits=format(n,"b") if n else ""
        d=delimited(bits,limit=256)
        assert d["steps"]==2*len(bits)+1
        z=zero_decide(bits,limit=256)
        assert z["is_zero"]==(n==0)
        assert z["result_mark_at_terminator"]==int(n!=0)
        checks+=2
    rules=[[1,1,1],[2,0,0],[2,0,1],[2,0,0]]
    p=compile_rules(rules)
    r=multistate_run(p,"0",8)
    assert r["status"]=="HALTED" and len(r["trace"])==2
    checks+=1
    print(json.dumps({"protocol":"HSI-OX-BOUNDED-CROSS-CHECK/0.1",
      "checks":checks,"all_passed":True,"exhaustive":False,
      "general_correctness_proof":False},separators=(",",":")))

if __name__=="__main__":main()
