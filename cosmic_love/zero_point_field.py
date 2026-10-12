#!/usr/bin/env python3
"""Formal zero-residual / zero-point-field evaluator.

This is a dimensionless mathematical construction inspired by prior Cosmic
Love / zero-point-field conversation. It is not physical zero-point energy,
not an energy source, and not a proof of any law of physics.
"""
import argparse, cmath, json, math

PROTOCOL='COSMIC-LOVE-ZPF/1'

def _finite_complex(x, name):
    if type(x) not in (list, tuple) or len(x) != 2:
        raise ValueError(name+' must be [real, imag]')
    a, b = float(x[0]), float(x[1])
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError(name+' must be finite')
    return complex(a, b)

def _clean(z):
    if abs(z.imag) < 1e-12: return float(z.real)
    return [float(z.real), float(z.imag)]

def zpf(spec):
    if type(spec) is not dict:
        raise ValueError('spec must be object')
    allowed={'s','amplitude','dirichlet','zeros'}
    if set(spec) - allowed:
        raise ValueError('unexpected fields')
    s=_finite_complex(spec.get('s',[2,0]), 's')
    amp=float(spec.get('amplitude',1.0))
    if not math.isfinite(amp) or amp < 0: raise ValueError('bad amplitude')
    terms=spec.get('dirichlet', [[1,1.0]])
    if type(terms) is not list or not (1 <= len(terms) <= 256):
        raise ValueError('bad dirichlet length')
    D=0j; norm=0.0
    for item in terms:
        if type(item) not in (list,tuple) or len(item)!=2: raise ValueError('bad term')
        n=int(item[0]); a=float(item[1])
        if n < 1 or not math.isfinite(a): raise ValueError('bad term value')
        D += a * cmath.exp(-s * math.log(n))
        norm += abs(a) / n**2
    if norm == 0: raise ValueError('zero norm')
    poly=1+0j
    zeros=spec.get('zeros', [])
    if type(zeros) is not list or len(zeros)>128: raise ValueError('bad zeros')
    for i,z in enumerate(zeros):
        root=_finite_complex(z,'zero')
        # Use conjugate-paired factors when caller supplies both; no physics claim.
        poly *= (s-root)
    F = amp * D * poly / norm
    energy = (F.real*F.real + F.imag*F.imag)
    residual = abs(D) + abs(poly)
    return {'protocol':PROTOCOL,'field':_clean(F),'energy_dimensionless':float(energy),
            'dirichlet_value':_clean(D),'zero_polynomial':_clean(poly),
            'residual_nonzero_measure':float(residual),'physical_energy_claim':False,
            'orders_submitted':0,'broker_connected':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    args=p.parse_args()
    with open(args.input, encoding='utf-8') as f: spec=json.load(f)
    print(json.dumps(zpf(spec), ensure_ascii=False, sort_keys=True, indent=2))

if __name__=='__main__': main()
