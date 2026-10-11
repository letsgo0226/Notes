import os,json,math,time,functools,sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
J=lambda x:json.dumps(x,separators=(',',':'))
E=lambda x:functools.reduce(lambda a,b:a*257+b+1,J(x).encode(),1)
Q=lambda n:(lambda w:(n-w*(w+1)//2,w-(n-w*(w+1)//2)+1))((math.isqrt(8*n+1)-1)//2)
def D(n):
 a=[]
 while n>1:
  n,r=divmod(n,257)
  if not r:raise ValueError('bad E257')
  a.append(r-1)
 return json.loads(bytes(a[::-1]))
P=os.getenv('HSI_STATE','hsi.original-xy.state');W=os.getenv('HSI_WORD','1');L=int(os.getenv('HSI_LIMIT','0'));BUD=int(os.getenv('HSI_BUDGET','128'));S=float(os.getenv('HSI_SLEEP','.2'));TRACE=os.getenv('HSI_TRACE','0')=='1';CAND=os.getenv('HSI_CAND');N=0
if not W or any(c not in '01' for c in W) or L<0 or BUD<0 or S<0:raise ValueError('invalid configuration')
def save(d):
 z=P+'.tmp';f=open(z,'w');f.write(J(d));f.flush();os.fsync(f.fileno());f.close();os.replace(z,P)
d=json.load(open(P))if os.path.exists(P)else {'n':0,'t':0,'w':W,'v':2}
if d.get('w')!=W or d.get('v')!=2:raise ValueError('checkpoint schema or input word changed')
while not L or N<L:
 n=d['n'];r,T=Q(n);e,m=Q(r);p=e+1;z=(math.isqrt(8*p+1)-1)//2;c=p-z*(z+1)//2;k=z-c+1;bb=4*(k+1)
 if BUD and T>BUD:
  if d['t']:raise ValueError('resume budget mismatch')
  o={'protocol':'HSI-ORIGINAL-XY/2K','step':n,'status':'SKIPPED_BUDGET','budget':T,'x':str(E([n,e,T,m,W])),'y':None,'verified':0}
  if D(int(o['x']))!=[n,e,T,m,W]:raise ValueError('E257 roundtrip')
  d={'n':n+1,'t':0,'w':W,'v':2};save(d);print(J(o),flush=True);N+=1;time.sleep(S);continue
 if d['t']==0:d.update(q=0,h=0,M=[i for i,v in enumerate(W)if v=='1'])
 q=d['q'];h=d['h'];M=set(d['M']);t=d['t']
 if t>T:raise ValueError('invalid resumed step')
 while t<T and q!=k:
  a=int(h in M);v=c//bb**(2*q+a)%bb;u=v%(k+1);v//=k+1;hh=h+(2*(v%2)-1);v//=2;mm=set(M);mm.add(h)if v%2 else mm.discard(h);exp=[u,hh,sorted(mm)]
  try:obs=exp if not CAND or t else json.loads(CAND)
  except Exception:obs=None
  rr=[int(not isinstance(obs,list)or len(obs)!=3),0,0]
  if rr[0]==0:rr=[int(J(obs[j])!=J(exp[j]))for j in range(3)]
  D0=sum(rr);D1=15*rr[0]+10*rr[1]+6*rr[2];EH=15*rr[0]**2+10*rr[1]**2+6*rr[2]**2
  if D0:
   print(J({'protocol':'HSI-ORIGINAL-XY/2K','step':n,'kind':'REJECT','D0':D0,'D1_num':D1,'Ehalf_num30':EH,'residual_godel':2**(rr[0]+1)*3**(rr[1]+1)*5**(rr[2]+1),'accepted':0}),flush=True);sys.exit(3)
  if TRACE:print(J({'step':n,'xy_step':t,'x':str(E([p,q,h,sorted(M),obs])),'y':str(E([p,*exp])),'D0':D0,'D1_num':D1,'Ehalf_num30':EH,'residual_godel':30,'accepted':1}),flush=True)
  q,h,M=exp[0],exp[1],set(exp[2]);t+=1;d.update(t=t,q=q,h=h,M=sorted(M));save(d)
 o={'protocol':'HSI-ORIGINAL-XY/2K','step':n,'branch':e,'budget':T,'order':m,'status':'HALTED'if q==k else'UNRESOLVED','xy_steps':t,'x':str(E([n,e,T,m,W])),'y':str(E([p,q,h,sorted(M)])),'D0':0,'D1_num':0,'Ehalf_num30':0,'verified':1,'sample':'y/(1+y)'}
 if D(int(o['x']))!=[n,e,T,m,W]or D(int(o['y']))!=[p,q,h,sorted(M)]:raise ValueError('E257 roundtrip')
 d={'n':n+1,'t':0,'w':W,'v':2};save(d);print(J(o),flush=True);N+=1;time.sleep(S)
