#!/usr/bin/env python3
"""HSI-UVCM/1: bounded deterministic virtual Turing machine with replayable checkpoints."""
import argparse
import hashlib
import json
import os
from pathlib import Path

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def digest(x):
    return hashlib.sha256(canon(x)).hexdigest()

def encode257(x):
    n=1
    for b in canon(x):
        n=n*257+b+1
    return str(n)

def validate(spec):
    assert type(spec)==dict and type(spec.get("transitions"))==dict
    assert type(spec.get("start"))==str and type(spec.get("halt"))==str
    for key,rule in spec["transitions"].items():
        assert isinstance(key,str) and ":" in key
        assert type(rule)==list and len(rule)==3
        assert rule[0] in (0,1) and rule[1] in (-1,1) and isinstance(rule[2],str)
    return spec

def initial(spec, bits=""):
    assert len(bits)<=100000 and all(c in "01" for c in bits)
    return {"q":spec["start"],"h":0,"t":0,
            "ones":[i for i,c in enumerate(bits) if c=="1"]}

def advance(spec,state,steps):
    validate(spec)
    assert isinstance(steps,int) and 0<=steps<=100000
    s={"q":state["q"],"h":state["h"],"t":state["t"],"ones":list(state["ones"])}
    ones=set(s["ones"])
    assert all(type(v)==int for v in ones)
    for _ in range(steps):
        if s["q"]==spec["halt"]:break
        read=int(s["h"] in ones)
        key=s["q"]+":"+str(read)
        if key not in spec["transitions"]:
            return dict(s,ones=sorted(ones)), "UNRESOLVED_MISSING_RULE"
        write,move,newq=spec["transitions"][key]
        if write:ones.add(s["h"])
        else:ones.discard(s["h"])
        s["h"]+=move;s["q"]=newq;s["t"]+=1
    s["ones"]=sorted(ones)
    return s, "HALTED" if s["q"]==spec["halt"] else "UNRESOLVED_BUDGET"

def atomic_write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".tmp")
    with temp.open("wb") as f:
        f.write(canon(obj)+b"\n")
        f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def save(path,spec,state,status):
    payload={"protocol":"HSI-UVCM/1","spec":spec,"state":state,"status":status,
             "x":encode257({"spec":spec,"initial_semantics":"binary_tape"}),
             "y":encode257(state)}
    atomic_write(path,{"payload":payload,"sha256":digest(payload)})
    return payload

def load(path):
    wrapper=json.loads(path.read_text())
    assert wrapper["sha256"]==digest(wrapper["payload"]),"checkpoint checksum mismatch"
    payload=wrapper["payload"]
    assert payload["protocol"]=="HSI-UVCM/1"
    validate(payload["spec"])
    assert payload["y"]==encode257(payload["state"])
    return payload

def certificate(before,after,steps,status):
    assert after["t"]>=before["t"]
    residuals=[0 if after["t"]-before["t"]<=steps else 1,
               0 if len(after["ones"])==len(set(after["ones"])) else 1,
               0 if status in ("HALTED","UNRESOLVED_BUDGET","UNRESOLVED_MISSING_RULE") else 1]
    # Finite positive Dirichlet residual; NOT zeta, RH, or proof of all correctness.
    energy=sum(v*v/p for v,p in zip(residuals,(2,3,5)))
    return {"residuals":residuals,"dirichlet_energy":energy,
            "claim":"finite_local_invariants_only"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",type=Path)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--bits",default="")
    p.add_argument("--steps",type=int,default=128)
    p.add_argument("--resume",action="store_true")
    a=p.parse_args()
    if a.resume:
        old=load(a.checkpoint);spec=old["spec"];before=old["state"]
    else:
        if not a.spec:p.error("--spec required without --resume")
        spec=validate(json.loads(a.spec.read_text()));before=initial(spec,a.bits)
    after,status=advance(spec,before,a.steps)
    payload=save(a.checkpoint,spec,after,status)
    print(json.dumps({"protocol":payload["protocol"],"status":status,
                      "step":after["t"],"head":after["h"],
                      "x":payload["x"],"y":payload["y"],
                      "certificate":certificate(before,after,a.steps,status)}))
if __name__=="__main__":main()
