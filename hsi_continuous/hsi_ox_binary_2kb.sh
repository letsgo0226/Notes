#!/bin/sh
python3 -c 'import os,json,math
K=8;B=4*(K+1);R=[(1,1,1),(2,0,0),(8,1,1),(0,1,1),(8,1,0),(3,0,1),(4,0,0),(2,0,1),(6,1,0),(5,1,1),(2,0,0),(2,0,1),(7,1,0),(7,1,1),(8,1,0),(0,1,1)];c=sum((q+(K+1)*(d+2*w))*B**i for i,(q,d,w) in enumerate(R));z=c+K-1;p=z*(z+1)//2+c
n=int(os.getenv("HSI_N","3"));width=int(os.getenv("HSI_WIDTH","4"));limit=int(os.getenv("HSI_LIMIT","100000"));assert 1<=width<=12 and 0<=n<2**width and limit>0,"invalid input"
M={2*i+1 for i in range(width)}|{2*i+2 for i in range(width) if n>>i&1};q=0;h=2;t=0
while q!=K and t<limit:
 b=int(h in M);v=c//B**(2*q+b)%B;q=v%(K+1);v//=K+1;d=v%2;w=v//2%2;M.add(h) if w else M.discard(h);h+=2*d-1;t+=1
if q!=K:raise SystemExit("step budget exhausted")
print(json.dumps({"protocol":"HSI-OX-BINARY-2KB/0.1","program":str(p),"input":n,"width":width,"steps":t,"halted":True,"terminal_mark":int(2*width+1 in M),"final_bits":"".join(str(int(2*i+2 in M)) for i in range(width)),"native_loop_control":True},separators=(",",":)))'
