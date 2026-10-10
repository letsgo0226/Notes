import os,json,math,functools,sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
J=lambda x:json.dumps(x,separators=(',',':'))
E=lambda s:functools.reduce(lambda n,b:257*n+b+1,s.encode(),1)
def D(p):
 z=(math.isqrt(8*p+1)-1)//2;c=p-z*(z+1)//2
 return z-c+1,c
def digit(p,q,a):
 k,c=D(p);B=4*(k+1)
 return c//B**(2*q+a)%B
def step(d):
 p=d['p'];q=d['q'];h=d['h'];m=set(d['m']);k,c=D(p)
 if q==k:return None
 a=int(h in m);v=digit(p,q,a)
 r=v%(k+1);v//=k+1;mv=2*(v%2)-1;v//=2
 if v%2:m.add(h)
 else:m.discard(h)
 return [r,h+mv,sorted(m)]
P=os.getenv('HSI_STATE','hsi.extend.state')
if os.path.exists(P):d=json.load(open(P))
else:
 p=int(os.getenv('HSI_PROGRAM','2'));w=os.getenv('HSI_WORD','1');q=int(os.getenv('HSI_START','0'))
 if p<0 or len(str(p))>=2048 or any(a not in '01' for a in w) or not 0<=q<=D(p)[0]:raise ValueError('program/word/start')
 d={'p':p,'w':w,'q':q,'h':0,'m':[i for i,a in enumerate(w) if a=='1'],'n':0,'H':[],'origin':[p,w,q]}
X=E(J([d['p'],d['q'],d['h'],d['m'],os.getenv('HSI_RULE'),os.getenv('HSI_CAND')]))
p=d['p'];k,c=D(p);kind='STEP';accepted=0;res=[0,0,0]
if 'HSI_RULE' in os.environ:
 kind='EVOLVE';new=int(os.environ['HSI_RULE']);raw=os.getenv('HSI_PERM',J(list(range(k))))
 try:pi=json.loads(raw)
 except (ValueError,TypeError):pi=[]
 K=D(new)[0] if new>=0 else -1
 valid=isinstance(pi,list) and len(pi)==k and all(type(a)==int and 0<=a<K for a in pi) and len(set(pi))==k and K>=k
 res=[int(not valid),0,int(len(str(new).encode())>=2048)]
 if valid:
  for q in range(k):
   for a in range(2):
    v=digit(p,q,a);r=v%(k+1)
    target=pi[r] if r<k else K
    want=target+(v//(k+1))*(K+1)
    res[1]+=int(digit(new,pi[q],a)!=want)
 accepted=int(not any(res));event=['E',new,pi,res]
 if accepted:
  d['p']=new;d['q']=pi[d['q']] if d['q']<k else K
else:
 exp=step(d)
 if exp is None:kind='HALTED';event=['H']
 else:
  raw=os.getenv('HSI_CAND')
  try:cand=exp if raw is None else json.loads(raw)
  except (ValueError,TypeError):cand=raw
  res=[int(not isinstance(cand,list) or len(cand)!=3),0,0]
  if not res[0]:res=[int(J(cand[i])!=J(exp[i])) for i in range(3)]
  accepted=int(not any(res));event=['S',cand,res]
  if accepted:d.update(q=exp[0],h=exp[1],m=exp[2],n=d['n']+1)
if kind!='HALTED':
 d['H'].append(str(E(J(event))));z=P+'.tmp'
 with open(z,'w') as f:
  f.write(J(d));f.flush();os.fsync(f.fileno())
 os.replace(z,P)
Y=E(J([d['p'],d['q'],d['h'],d['m']]))
print(J({'x':str(X),'y':str(Y),'D1_num':15*res[0]+10*res[1]+6*res[2],'protocol':'HSI-CL-XY/2K','kind':kind,'accepted':accepted,'D0':sum(res),'step':d['n'],'p':d['p'],'states':D(d['p'])[0],'q':d['q'],'history':len(d['H'])}))
