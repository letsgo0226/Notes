"""Bounded finite Dirichlet zero-field mathematical model. NOT physical energy."""
from math import isfinite, isqrt, log
import cmath

SEED=55067263
PROTOCOL="COSMIC-LOVE-SELF-SOLVED-ZERO-FIELD/2.0"

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

def d_n(s,cs):
    return sum(a*cmath.exp(-s*log(i)) for i,a in enumerate(cs,1))

def d_prime(s,cs):
    return -sum(a*log(i)*cmath.exp(-s*log(i)) for i,a in enumerate(cs,1))

def evaluate(sigma=0.5,t=0.0,n=16,amplitude=1):
    sigma=bounded_float(sigma,-2,4,"sigma")
    t=bounded_float(t,-60,60,"t")
    amp=bounded_float(amplitude,0,10,"amplitude")
    cs=tm_coefficients(n)
    f=amp*d_n(complex(sigma,t),cs)/d_n(2+0j,cs)
    energy=abs(f)**2
    if not all(isfinite(x) for x in (f.real,f.imag,energy)):
        raise ValueError("nonfinite result")
    return {"protocol":"COSMIC-LOVE-SELF-SOLVED-ZERO-FIELD/2.0",
            "field_type":"FINITE_DIRICHLET_POLYNOMIAL",
            "p":SEED,"n":n,"s":{"re":sigma,"im":t},
            "coefficients":list(cs),"amplitude":amp,
            "f":{"re":f.real,"im":f.imag},"energy_proxy":energy,
            "zero_factor_inserted":False,
            "physical_energy_generated":False,
            "riemann_zeta_zero_proven":False,
            "all_zeros_found":False}

def _newton(z,cs):
    for _ in range(40):
        v=d_n(z,cs)
        if abs(v)<1e-10:return z
        deriv=d_prime(z,cs)
        if abs(deriv)<1e-10:return None
        step=v/deriv
        if abs(step)>2:step=2*step/abs(step)
        z-=step
        if abs(z.real)>16 or abs(z.imag)>100 or not all(isfinite(x) for x in (z.real,z.imag)):
            return None
    return z if abs(d_n(z,cs))<1e-10 else None

def solve(n=2,tmax=30,max_roots=12):
    from math import pi
    tmax=bounded_float(tmax,0,60,"tmax")
    if type(max_roots) is not int or not 1<=max_roots<=16:
        raise ValueError("max_roots must be 1..16")
    cs=tm_coefficients(n)
    if n==2:
        # This exact family follows from D_2(s)=1+2**(1-s)=0.
        roots=[complex(1,(2*m+1)*pi/log(2))
               for m in range(-10,11)
               if abs((2*m+1)*pi/log(2))<=tmax+1e-12]
        roots.sort(key=lambda z:(abs(z.imag),z.imag))
        method="ANALYTIC_ROOT_FAMILY_FILTERED_TO_WINDOW"
    else:
        roots=[]
        for sigma in (-2+i*0.5 for i in range(13)):
            for t in range(0,int(tmax)+1,2):
                for sign in ((1,-1) if t else (1,)):
                    z=_newton(complex(sigma,sign*t),cs)
                    if (z is None or not(-2<=z.real<=4 and abs(z.imag)<=tmax)
                        or abs(d_n(z,cs))>1e-8):
                        continue
                    if not any(abs(z-w)<1e-4 for w in roots):
                        roots.append(z)
        roots.sort(key=lambda z:(abs(z.imag),z.real,z.imag))
        method="FINITE_RESIDUAL_VERIFIED_CANDIDATES" if roots else "UNRESOLVED_IN_BOUNDED_SEARCH"
    cut=roots[:max_roots]
    return {"protocol":"COSMIC-LOVE-SELF-SOLVED-ZERO-FIELD/2.0",
            "n":n,"status":method,
            "zeros":[{"re":z.real,"im":z.imag,"residual":abs(d_n(z,cs)),
                      "method":"analytic" if n==2 else "newton_finite_residual",
                      "verified_within_tolerance":abs(d_n(z,cs))<=1e-8}
                     for z in cut],
            "complete_within_window":n==2 and len(roots)<=max_roots,
            "search":{"real_min":-2,"real_max":4,"imag_abs_max":tmax},
            "zero_factor_inserted":False,
            "physical_energy_generated":False}
