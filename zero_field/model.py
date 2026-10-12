"""Bounded finite Dirichlet zero-field mathematical model. NOT physical energy."""
from math import isfinite, isqrt, log
import cmath

SEED=55067263
PROTOCOL="COSMIC-LOVE-MATH-ZERO-FIELD/1.0"
DEFAULT_ZERO=complex(0.5,14.134725141734693)

def decode_machine(p=SEED):
    v=(isqrt(8*p+1)-1)//2
    c=p-v*(v+1)//2
    k=v-c+1;K=k+1;B=4*K
    def step(q,a):
        u=c//B**(2*q+a)%B
        z,r=divmod(u,K)
        return r,z//2,2*(z%2)-1
    if k!=2 or any(step(q,a)!=(1-q,a,1-2*q) for q in (0,1) for a in (0,1)):
        raise ValueError("seed transition defect")
    return step

STEP=decode_machine()

def tm_coefficients(n):
    if type(n) is not int or not 2<=n<=64 or n%2:
        raise ValueError("n must be even and between 2 and 64")
    q=h=0;tape={};coeff=[]
    for _ in range(n):
        coeff.append(1+q)
        a=tape.get(h,0)
        q,b,d=STEP(q,a)
        if b:tape[h]=b
        else:tape.pop(h,None)
        h+=d
    if (q,h,tape)!=(0,0,{}):
        raise ValueError("TM two-step closure defect")
    return tuple(coeff)

def bounded_float(value,lo,hi,label):
    if isinstance(value,bool):raise ValueError(label+" must be numeric")
    try:x=float(value)
    except (TypeError,ValueError,OverflowError) as e:
        raise ValueError(label+" must be numeric") from e
    if not isfinite(x) or not lo<=x<=hi:raise ValueError(label+" outside allowed domain")
    return x

def zeros_from_pairs(pairs):
    if not isinstance(pairs,(tuple,list)) or not 1<=len(pairs)<=4:
        raise ValueError("zero count must be 1..4")
    out=[]
    for re,im in pairs:
        z=complex(bounded_float(re,-3,3,"zero real part"),
                  bounded_float(im,0,60,"zero imaginary part"))
        if abs(2-z)<1e-12:raise ValueError("zero at normalization point forbidden")
        out.append(z)
    return tuple(out)

def d_n(s,coeff):
    return sum(a*cmath.exp(-s*log(j)) for j,a in enumerate(coeff,1))

def p_z(s,zeros):
    result=1+0j
    for z in zeros:
        result*=((s-z)*(s-z.conjugate()))/((2-z)*(2-z.conjugate()))
    return result

def evaluate(sigma=0.5,t=0.0,n=16,zeros=(DEFAULT_ZERO,),amplitude=1.0):
    sigma=bounded_float(sigma,-2,4,"sigma")
    t=bounded_float(t,-60,60,"t")
    amp=bounded_float(amplitude,0,10,"amplitude")
    if type(n) is not int:raise ValueError("n must be integer")
    coeff=tm_coefficients(n)
    zs=zeros_from_pairs([(z.real,z.imag) for z in zeros])
    s=complex(sigma,t)
    baseline=d_n(complex(2,0),coeff)
    value=amp*d_n(s,coeff)*p_z(s,zs)/baseline
    energy=abs(value)**2
    if not all(isfinite(v) for v in (value.real,value.imag,energy)):
        raise ValueError("nonfinite calculation")
    return {
        "protocol":PROTOCOL,
        "field_type":"FINITE_DIRICHLET_MATHEMATICAL_MODEL",
        "not_physical_energy":True,
        "is_riemann_zeta":False,
        "universal_solution_proven":False,
        "p":SEED,"n":n,"s":{"re":sigma,"im":t},
        "zeros":[{"re":z.real,"im":z.imag} for z in zs],
        "amplitude":amp,
        "field":{"re":value.real,"im":value.imag},
        "energy_proxy":energy,
        "normalization":"P_Z(2)=1, D_N(2)>0; F(2)=amplitude",
        "coefficient_source":"HSI-ST/1 two-step period q=0,1 -> 1,2 repeated"
    }
