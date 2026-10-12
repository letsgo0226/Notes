#!/usr/bin/env python3
"""Bounded OriginalXY transitions coupled to exact integer symbolic translator.
Python orchestrates both components; NOT a native OriginalXY compiler.
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSLATOR = ROOT / "hsi_continuous/hsi_ox_eisi_2kb.sh"

def step(p, state):
    if p < 1:
        raise ValueError("positive program required")
    z = (math.isqrt(8*p+1)-1)//2
    c = p-z*(z+1)//2
    k = z-c+1
    base = 4*(k+1)
    q,h,marked = state
    if q == k:
        return state, True
    marked = set(marked)
    v = c//base**(2*q+int(h in marked))%base
    nq = v%(k+1)
    v //= k+1
    nh = h+2*(v%2)-1
    v //= 2
    if v%2:
        marked.add(h)
    else:
        marked.discard(h)
    return [nq,nh,sorted(marked)], nq == k

def run(p,word,steps,expression):
    if not 0 <= steps <= 512 or not word or any(x not in "01" for x in word):
        raise ValueError("invalid bounded configuration")
    state = [0,0,[i for i,b in enumerate(word) if b=="1"]]
    z = (math.isqrt(8*p+1)-1)//2
    k = z-(p-z*(z+1)//2)+1
    history=[]
    for i in range(steps):
        if state[0]==k:
            break
        state,halted = step(p,state)
        history.append(state)
        if halted:
            break
    # OriginalXY output is an actual operand, not an unrelated parallel report.
    # The expression may reference its exact integer state values.
    def substitute(node):
        if node=="$q": return state[0]
        if node=="$h": return state[1]
        if node=="$marked_count": return len(state[2])
        if isinstance(node,list): return [substitute(v) for v in node]
        return node
    concrete=substitute(expression)
    result=subprocess.run(["sh",str(TRANSLATOR),json.dumps(concrete,separators=(",",":"))],
                          check=True,capture_output=True,text=True,timeout=15)
    translated=json.loads(result.stdout)
    return {"protocol":"HSI-ORIGINALXY-EISI-COUPLED/0.1",
            "utm":{"program":p,"word":word,"steps":len(history),"state":state,
                   "status":"HALTED" if state[0]==k else "UNRESOLVED"},
            "substituted_expression":concrete,"translation":translated,
            "native_originalxy_compiler":False,"exact_integer":True}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--program",type=int,default=2)
    a.add_argument("--word",default="1")
    a.add_argument("--steps",type=int,default=16)
    a.add_argument("--expression",default='["add","$h",["mul","$q",2]]')
    args=a.parse_args()
    print(json.dumps(run(args.program,args.word,args.steps,json.loads(args.expression)),
                     ensure_ascii=False,separators=(",",":")))
if __name__=="__main__":
    main()
