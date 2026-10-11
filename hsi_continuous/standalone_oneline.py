#!/usr/bin/env python3
"""Generate a self-contained bounded UTM + Dirichlet feedback one-line program."""
import argparse
import json
from pathlib import Path
import shlex

ROOT=Path(__file__).resolve().parent.parent
CORE=r'''import math,json
from functools import reduce
E=lambda a:reduce(lambda z,b:z*257+b+1,json.dumps(a,separators=(",",":")).encode(),1)
p=2;w="1";T=16;N=16;R=8
z=(math.isqrt(8*p+1)-1)//2;c=p-z*(z+1)//2;k=z-c+1;B=4*(k+1)
q=h=0;M={i for i,b in enumerate(w)if b=="1"}
for t in range(T):
 if q==k:break
 a=int(h in M);v=c//B**(2*q+a)%B;u=v%(k+1);v//=k+1;hh=h+2*(v%2)-1;v//=2
 if v%2:M.add(h)
 else:M.discard(h)
 q,h=u,hh
x=E([p,[q,h,sorted(M)]])%1000003/1000003
for t in range(R):
 re=im=0.
 for n in range(1,N+1):
  a=(-1)**(n+1)/n**2;re+=a*math.cos(x*math.log(n));im-=a*math.sin(x*math.log(n))
 y=math.tanh(re+im);v=.75*x+.125*(y+1)
 print(json.dumps(dict(iteration=t,x=x,y=y,next=v,residual=abs(v-x)),separators=(",",":")))
 x=v
'''
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--out",default="hsi_continuous/out")
 a=p.parse_args()
 line="python3 -c "+shlex.quote(CORE)
 b=(line+"\n").encode()
 if len(b)>2048 or b.count(b"\n")!=1:
  raise ValueError("2KB single-line bound failed")
 out=(ROOT/a.out).resolve()
 if not out.is_relative_to(ROOT) or out.is_relative_to((ROOT/"Notes").resolve()):
  raise ValueError("invalid output path")
 out.mkdir(parents=True,exist_ok=True)
 (out/"feedback_standalone.oneline.sh").write_bytes(b)
 (out/"feedback_standalone.oneline.json").write_text(json.dumps(
  {"protocol":"HSI-UTM-DIRICHLET-ONELINE/0.1","bytes":len(b),
   "embedded_python":True,"external_source_required":False,
   "cryptographic_source_verification":False,
   "parameters":{"program":2,"word":"1","steps":16,"terms":16,"rounds":8},
   "scope":"finite experiment, not AI-equivalent"},indent=2)+"\n")
 print("standalone one-line generated",len(b),"bytes")
if __name__=="__main__":main()
