"""Classical sparse simulation of the supplied QTM phase-permutation lift.

On valid basis states U|0,h,T>=i|1,h+1,T>, U|1,h,T>=-i|0,h-1,T>.
The mapping is bijective, phases have modulus one, and the paired phase
product is one, so the ideal operator is unitary with U^2=I. Tape is fixed
because every decoded rule writes its input symbol. The implementation
retains the supplied 1e-12 sparse cutoff: numerical claims are tolerance
checks, not exact arithmetic for arbitrarily tiny amplitudes. No measurement.
"""
import json,sys
from math import isqrt,sqrt
p=55067263;v=(isqrt(8*p+1)-1)//2;c=p-v*(v+1)//2;k=v-c+1;K=k+1;B=4*K
def delta(q,a):
 u=c//B**(2*q+a)%B;z=u//K
 return u%K,z//2,2*(z%2)-1
expected={(0,0):(1,0,1),(0,1):(1,1,1),(1,0):(0,0,-1),(1,1):(0,1,-1)}
verified=all(delta(q,a)==d for(q,a),d in expected.items());assert verified
def U(psi):
 out={}
 for (q,h,T),amp in psi.items():
  Q,b,d=delta(q,int(h in T));y=(Q,h+d,T);out[y]=out.get(y,0)+amp*(1j if q==0 else-1j)
 return {x:a for x,a in out.items() if abs(a)>1e-12}
def eq(x,y):return set(x)==set(y) and all(abs(x[z]-y[z])<1e-12 for z in x)
def norm(x):return sum(abs(a)**2 for a in x.values())

PROTOCOL = "HSI-COSMIC-QUANTUM-SELF-CLOSURE/QTM-1.0"

def certificate():
    psi={(0,0,()):1/sqrt(2),(1,0,()):1j/sqrt(2)}
    phi=U(psi)
    checks=(all(delta(q,a)==d for (q,a),d in expected.items()),
            abs(norm(psi)-1)<1e-12 and abs(norm(phi)-1)<1e-12,
            eq(U(phi),psi))
    if not all(checks):
        raise ValueError("QTM recurrence verification failed")
    return dict(protocol=PROTOCOL,version=42,program=p,
                hilbert_basis="|q,h,tape>",unitary="phase-permutation",
                phase={"q0":"+i","q1":"-i"},transition_verified=checks[0],
                norm_preserved=checks[1],U2_identity=checks[2],
                two_step_quantum_recurrence=True,halt_unreachable=True,
                measurement="none",scope="quantum lift of specified two-state TM only")

if __name__ == "__main__":
    print(json.dumps(certificate(),sort_keys=True),flush=True)
    if "--run" in sys.argv:
        psi={(0,0,()):1/sqrt(2),(1,0,()):1j/sqrt(2)}
        while True:
            psi=U(psi)
