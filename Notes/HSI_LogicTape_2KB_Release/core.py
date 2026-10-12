import os,json,tempfile
from math import isqrt
Z="HSI-ST/1";s=os.path.expanduser(input("File:").strip().strip("\"'"))
try:d=json.load(open(s))if s.endswith(".json")else{}
except:d={}
r=type(d)==dict and d.get("protocol")==Z
if r:assert type(d["p"])==str and type(d["hi"])==int and type(d["image"])==str
p=int(d["p"]if r else input("P[1829]:")or"1829");assert p>=0
v=(isqrt(8*p+1)-1)//2;c=p-v*(v+1)//2;k=v-c+1;K=k+1;B=4*K
q,h,t,lo=(d[x]for x in("q","h","t","lo"))if r else(0,0,0,0)
assert all(type(x)is int for x in(q,h,t,lo))and 0<=q<=k and t>=0
if r:s=os.path.join(os.path.dirname(s),d["image"])
L=int(input("Steps[10000;0=unlimited;-1=encode]:")or"10000");assert L>=-1
a=tempfile.TemporaryFile();I=lambda x:2*x if x>=0 else-2*x-1
def W(x,b):
 while b:
  m=min(-x,len(b))if x<0 else len(b);i=I(x+m-1)if x<0 else I(x)
  a.seek(i);v=bytearray(a.read(2*m).ljust(2*m,b"\0"));v[::2]=b[:m][::-1]if x<0 else b[:m]
  a.seek(i);a.write(v);x+=m;b=b[m:]
n=0
with open(s,"rb")as f:
 while b:=f.read(65536):W(lo+n,b);n+=len(b)
hi=lo+n
assert not r or hi==d["hi"]
e=t+L
while q!=k and(not L or t<e):
 x,j=divmod(h,8);lo=min(lo,x);hi=max(hi,x+1);i=I(x);a.seek(i);b=a.read(1);v=b[0]if b else 0
 u=c//B**(2*q+(v>>j&1))%B;q=u%K;u//=K;v=v|1<<j if u//2 else v&~(1<<j)
 a.seek(i);a.write(bytes([v]));h+=2*(u%2)-1;t+=1
o=os.path.expanduser(input("Save:").strip().strip("\"'"))or s+".tm"
assert not os.path.exists(o)and not os.path.exists(o+".json")
with open(o,"xb")as f:
 x=lo
 while x<hi:
  m=min(65536,hi-x,-x if x<0 else 65536);a.seek(I(x+m-1)if x<0 else I(x));b=a.read(2*m).ljust(2*m,b"\0")[::2]
  f.write(b[::-1]if x<0 else b);x+=m
d=dict(protocol=Z,p=str(p),q=q,h=h,t=t,lo=lo,hi=hi,image=os.path.basename(o),status="HALTED"if q==k else"UNRESOLVED")
with open(o+".json","x")as f:json.dump(d,f,separators=(",",":"))
print(d["status"],t,o)
