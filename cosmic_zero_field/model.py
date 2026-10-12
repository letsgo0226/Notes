"""COSMIC-LOVE-ZERO-FIELD/1 — dimensionless mathematical zero-field.

Finite entire Dirichlet family F(s), E(s)=|F(s)|², and algebraically
prescribed zeros. No claims about vacuum energy, zeta zeros or trading.
"""
from __future__ import annotations
from dataclasses import dataclass
import cmath
import hashlib
import json
import math
from math import isqrt

PROTOCOL = 'COSMIC-LOVE-ZERO-FIELD/1'
P = 55067263
ALLOWED_N = (8, 16, 32, 64, 128)
DEFAULT_ZEROS = ((0.5, 8.0), (0.5, 14.0), (0.5, 21.0))

def machine():
    p=P
    v=(isqrt(8*p+1)-1)//2
    c=p-v*(v+1)//2
    k=v-c+1;K=k+1;B=4*K
    if (v,c,k,K,B)!=(10493,10492,2,3,12):
        raise ValueError('HSI-ST/1 seed failed')
    rules=[]
    for q in (0,1):
        for a in (0,1):
            u=c//B**(2*q+a)%B
            z,r=divmod(u,K)
            actual=(r,z//2,2*(z%2)-1)
            expected=(1-q,a,1-2*q)
            if actual!=expected:
                raise ValueError('HSI-ST/1 transition failed')
            rules.append((q,a,*actual))
    return tuple(rules)

def primes(n):
    out=[];candidate=2
    while len(out)<n:
        if all(candidate % p for p in out if p*p<=candidate):
            out.append(candidate)
        candidate+=1
    return tuple(out)

@dataclass(frozen=True)
class Config:
    basis: str = 'prime'
    terms: int = 32
    amplitude: float = 1.0
    zeros: tuple[tuple[float,float], ...] = DEFAULT_ZEROS

    def __post_init__(self):
        if self.basis not in ('prime','eta') or type(self.terms) is not int or self.terms not in ALLOWED_N:
            raise ValueError('unsupported basis / N')
        if not math.isfinite(self.amplitude) or not .1<=self.amplitude<=5:
            raise ValueError('amplitude out of range')
        if type(self.zeros) not in (list,tuple) or not 1<=len(self.zeros)<=8:
            raise ValueError('zero count must be 1..8')
        seen=set()
        for pair in self.zeros:
            if type(pair) not in (list,tuple) or len(pair)!=2:
                raise ValueError('zero pair must have two coordinates')
            u,v=pair
            if type(u) not in (float,int) or type(v) not in (float,int) or not math.isfinite(u) or not math.isfinite(v) or not -3<=u<=3 or not 0<=v<=60:
                raise ValueError('invalid zero coordinate')
            key=(float(u),float(v))
            if key in seen:raise ValueError('duplicate zero pair')
            seen.add(key)

def model_coefficients(cfg):
    if cfg.basis=='prime':
        bases=primes(cfg.terms)
        weights=tuple(1+(j%2) for j in range(cfg.terms))
    else:
        bases=tuple(range(1,cfg.terms+1))
        weights=tuple(1-2*(j%2) for j in range(cfg.terms))
    return bases,weights

class Field:
    def __init__(self, cfg=Config()):
        self.cfg=cfg
        machine()
        self.bases,self.weights=model_coefficients(cfg)
        self.logs=tuple(math.log(b) for b in self.bases)
        self.anchor=sum(w/(float(b)**2) for w,b in zip(self.weights,self.bases))
        if not math.isfinite(self.anchor) or self.anchor<=0:raise ValueError('invalid D_N(2)')

    def _base(self,s):
        D=complex(0,0);dD=complex(0,0)
        for w,ln in zip(self.weights,self.logs):
            term=w*cmath.exp(-s*ln)
            D+=term;dD-=ln*term
        return D,dD

    def _zero_factor(self,s):
        product=complex(1,0);derivative=complex(0,0)
        for u,v in self.cfg.zeros:
            z=complex(u,v);zbar=complex(u,-v)
            denominator=1+u*u+v*v
            fac=(s-z)*(s-zbar)/denominator
            dfac=((s-z)+(s-zbar))/denominator
            derivative=derivative*fac+product*dfac
            product*=fac
        return product,derivative

    def evaluate(self,s):
        s=complex(s)
        if not (math.isfinite(s.real) and math.isfinite(s.imag) and -3<=s.real<=3 and -65<=s.imag<=65):
            raise ValueError('evaluation outside finite review domain')
        D,dD=self._base(s)
        Pz,dP=self._zero_factor(s)
        factor=self.cfg.amplitude/self.anchor
        F=factor*D*Pz
        Fp=factor*(dD*Pz+D*dP)
        energy=F.real*F.real+F.imag*F.imag
        if not math.isfinite(energy):raise ValueError('nonfinite numeric result')
        return F,Fp,energy

    def report(self):
        points=[]
        for u,v in self.cfg.zeros:
            F,_,E=self.evaluate(complex(u,v))
            points.append({'sigma':u,'t':v,'abs_f_numeric':abs(F),'e_numeric':E,
                           'zero_reason':'EXACT_FACTORIZATION_NOT_NUMERIC_RESIDUAL'})
        F,Fp,E=self.evaluate(.8+13.8j)
        config={'basis':self.cfg.basis,'terms':self.cfg.terms,'amplitude':self.cfg.amplitude,
                'zeros':[list(z) for z in self.cfg.zeros]}
        canonical=json.dumps(config,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        return {'protocol':PROTOCOL,'seed':P,'status':'BOUNDED_MATHEMATICAL_MODEL_VERIFIED',
                'config_sha256':hashlib.sha256(canonical).hexdigest(),
                'config':config,'base_normalizer_d2':self.anchor,
                'prescribed_zero_checks':points,
                'probe':{'sigma':.8,'t':13.8,'f_real':F.real,'f_imag':F.imag,
                         'fprime_real':Fp.real,'fprime_imag':Fp.imag,'e_numeric':E},
                'physical_energy_claim':False,'zeta_zeros_claim':False,
                'live_trading_authorized':False,'chat_access_authorized':False,
                'proof_scope':'PRESCRIBED_POLYNOMIAL_ZEROS_AND_EXACT_TWO_STEP_TM_ONLY'}

if __name__=='__main__':
    print(json.dumps(Field().report(),sort_keys=True,indent=2,ensure_ascii=False))
