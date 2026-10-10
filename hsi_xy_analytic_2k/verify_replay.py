"""Independent verifier for the HSI-CL-EXTEND finite transition proof trace."""
import json,math,sys
from pathlib import Path

def code_text(s):
 n=int(s)
 if n<1:raise ValueError('invalid Godel seed')
 b=[]
 while n>1:
  n,x=divmod(n-1,257)
  if x>255:raise ValueError('invalid Godel digit')
  b.append(x)
 return bytes(reversed(b)).decode('utf-8')

def decode(p):
 if type(p)!=int or p<0:raise ValueError('negative machine')
 z=(math.isqrt(8*p+1)-1)//2;c=p-z*(z+1)//2
 return z-c+1,c

def trans(p,q,a):
 k,c=decode(p);return c//(4*(k+1))**(2*q+a)%(4*(k+1))

def nxt(p,q,h,m):
 k,_=decode(p)
 if q==k:return None
 v=trans(p,q,int(h in m));r=v%(k+1);z=v//(k+1)
 out=set(m)
 (out.add(h) if (z//2)%2 else out.discard(h))
 return r,h+(1 if z%2 else -1),sorted(out)

def check_extension(old,new,pi):
 k,_=decode(old);K=decode(new)[0] if type(new)==int and new>=0 else -1
 ok=(isinstance(pi,list) and len(pi)==k and all(type(x)==int and 0<=x<K for x in pi) and len(set(pi))==k and K>=k)
 delta=[int(not ok),0,int(len(str(new).encode())>=2048)]
 if ok:
  for q in range(k):
   for a in (0,1):
    v=trans(old,q,a);r=v%(k+1)
    want=(pi[r] if r<k else K)+(v//(k+1))*(K+1)
    delta[1]+=trans(new,pi[q],a)!=want
 return [int(z) for z in delta]

def verify(d):
 p,w,q=d['origin'];k,_=decode(p)
 if len(str(p))>=2048 or any(z not in '01' for z in w) or not 0<=q<=k:raise ValueError('origin')
 n=0;h=0;m=[j for j,x in enumerate(w) if x=='1'];a=b=rej=0
 for raw in d['H']:
  ev=json.loads(code_text(raw))
  if ev[0]=='E':
   _,new,pi,res=ev
   actual=check_extension(p,new,pi)
   if actual!=res:raise ValueError('evolution certificate')
   if not any(actual):
    k,_=decode(p);K,_=decode(new)
    q=pi[q] if q<k else K;p=new;a+=1
   else:rej+=1
  elif ev[0]=='S':
   _,cand,res=ev
   exp=nxt(p,q,h,m)
   if exp is None:raise ValueError('step from halt')
   if not isinstance(cand,list) or len(cand)!=3:actual=[1,0,0]
   else:actual=[int(json.dumps(cand[i],separators=(',',':'))!=json.dumps(exp[i],separators=(',',':'))) for i in range(3)]
   if actual!=res:raise ValueError('step certificate')
   if not any(actual):q,h,m=exp;n+=1;b+=1
   else:rej+=1
  else:raise ValueError('unknown event')
 if (p,q,h,m,n)!=(d['p'],d['q'],d['h'],d['m'],d['n']):raise ValueError('replay mismatch')
 return {'verified':True,'accepted_extensions':a,'accepted_steps':b,'rejections':rej,'history':len(d['H']),'states':decode(p)[0],'program_bytes':len(str(p).encode())}
if __name__=='__main__':
 try:print(json.dumps(verify(json.loads(Path(sys.argv[1]).read_text())),ensure_ascii=False))
 except Exception as e:print('REPLAY FAILED:',str(e),file=sys.stderr);sys.exit(1)
