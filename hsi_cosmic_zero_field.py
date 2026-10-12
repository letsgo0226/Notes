#!/usr/bin/env python3
"""Finite COSMIC_LOVE mathematical zero-field for deterministic Corpus DSP."""
import hashlib
import json
import math
import os

PROTOCOL = 'HSI-COSMIC-ZERO-FIELD/1.1'
TM_PROGRAM = 55067263
DEFAULT_ZEROS = ((0.5, 8.0), (0.5, 14.0), (0.5, 21.0))
ALLOWED_TERMS = (8, 16, 32, 64, 128)


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _settings():
    n = int(os.getenv('HSI_ZERO_FIELD_TERMS', '32'))
    basis = os.getenv('HSI_ZERO_FIELD_BASIS', 'prime').lower()
    amplitude = float(os.getenv('HSI_ZERO_FIELD_AMPLITUDE', '1'))
    raw = os.getenv('HSI_ZERO_FIELD_ZEROS', '0.5:8,0.5:14,0.5:21')
    if n not in ALLOWED_TERMS:
        raise ValueError('HSI_ZERO_FIELD_TERMS must be one of 8,16,32,64,128')
    if basis not in ('prime', 'alternating'):
        raise ValueError('HSI_ZERO_FIELD_BASIS must be prime or alternating')
    if not math.isfinite(amplitude) or not 0.1 <= amplitude <= 5:
        raise ValueError('HSI_ZERO_FIELD_AMPLITUDE must be finite within 0.1..5')
    try:
        zeros = [tuple(float(y.strip()) for y in x.split(':')) for x in raw.split(',')]
    except (ValueError, TypeError) as e:
        raise ValueError('HSI_ZERO_FIELD_ZEROS requires sigma:imag entries') from e
    if not 1 <= len(zeros) <= 8 or any(len(z)!=2 or not math.isfinite(z[0]) or not math.isfinite(z[1]) or not -3<=z[0]<=3 or not 0<=z[1]<=60 for z in zeros):
        raise ValueError('HSI_ZERO_FIELD_ZEROS requires 1..8 finite sigma:imag pairs within [-3,3]x[0,60]')
    return n, basis, amplitude, tuple(zeros)


def _first_primes(n):
    primes = []
    v = 2
    while len(primes) < n:
        if all(v % p for p in primes if p*p <= v):
            primes.append(v)
        v += 1
    return primes


def _terms(tm, n, basis):
    if not tm.get('verified') or tm.get('program') != TM_PROGRAM:
        raise ValueError('requires verified COSMIC_LOVE TM')
    rows = tm.get('transition_table')
    expected = [(q, a, 1-q, a, 1-2*q) for q in (0, 1) for a in (0, 1)]
    if not isinstance(rows, list) or len(rows) != 4 or [(r.get('q'),r.get('a'),r.get('next_q'),r.get('write'),r.get('direction')) for r in rows] != expected:
        raise ValueError('verified TM transition table mismatch')
    q_seq = [i % 2 for i in range(n)]
    if basis == 'prime':
        return list(zip(_first_primes(n), [1+q for q in q_seq]))
    return [(i+1, 1-2*q) for i, q in enumerate(q_seq)]


def _dirichlet(s, terms):
    return sum(a*pow(p, -s) for p,a in terms)


def _function(s, terms, zeros, amplitude, d2):
    product = 1+0j
    for sigma, gamma in zeros:
        z = complex(sigma, gamma)
        product *= (s-z)*(s-z.conjugate()) / (1+sigma*sigma+gamma*gamma)
    return amplitude*_dirichlet(s, terms)*product/d2


def build_zero_field(tm_control, event_count):
    if os.getenv('HSI_ZERO_FIELD', '1') == '0':
        return {'protocol':PROTOCOL,'enabled':False,'reason':'disabled_by_environment'}
    if not tm_control.get('enabled'):
        return {'protocol':PROTOCOL,'enabled':False,'reason':'cosmic_love_tm_disabled'}
    if not isinstance(event_count,int) or not 1<=event_count<=512:
        raise ValueError('event_count must be 1..512')
    n, basis, amplitude, zeros = _settings()
    terms = _terms(tm_control, n, basis)
    d2 = _dirichlet(2+0j, terms)
    if abs(d2) < 1e-10:
        raise ValueError('Dirichlet normalization too small')
    root_checks = [abs(_function(complex(u, v), terms, zeros, amplitude, d2)) < 1e-10 and abs(_function(complex(u, -v), terms, zeros, amplitude, d2)) < 1e-10 for u,v in zeros]
    product_at_two = 1.0
    for sigma, gamma in zeros:
        product_at_two *= ((2-sigma)**2+gamma**2)/(1+sigma*sigma+gamma*gamma)
    checks = {
        'verified_two_cycle': [a for _,a in terms] == ([1+(i%2) for i in range(n)] if basis=='prime' else [1-2*(i%2) for i in range(n)]),
        'inserted_conjugate_zeros': all(root_checks),
        'normalization_at_s_2': abs(_function(2+0j,terms,zeros,amplitude,d2)-amplitude*product_at_two)<1e-10,
        'positive_normalization': d2.real>0 and abs(d2.imag)<1e-12,
        'conjugation_symmetry': abs(_function(.35+3j,terms,zeros,amplitude,d2).conjugate()-_function(.35-3j,terms,zeros,amplitude,d2))<1e-10,
    }
    lo = min(v for _,v in zeros)*0.75
    hi = max(v for _,v in zeros)*1.25
    if hi<=lo:hi=lo+1.0
    energies=[]
    for i in range(event_count):
        t=lo+(hi-lo)*(i/(event_count-1) if event_count>1 else 0.5)
        e=abs(_function(complex(.5,t),terms,zeros,amplitude,d2))**2
        energies.append((t,e))
    checks['finite_nonnegative_samples']=all(math.isfinite(e) and e>=0 for _,e in energies)
    if not all(checks.values()):
        raise ValueError('zero-field finite verification failed')
    peak=max(e for _,e in energies)
    events=[]
    for t,e in energies:
        u=min(1.0,max(0.0,e/peak if peak>0 else 0.0))
        events.append({
            'imaginary_s':round(t,12),'energy':round(e,12),'unit_energy':round(u,12),
            'rate_delta':round(.018*(2*u-1),12),
            'pan_delta':round(.075*(2*u-1),12),
            'gain_multiplier':round(.94+.12*u,12)
        })
    result={
        'protocol':PROTOCOL,'enabled':True,'tm_control_uid':tm_control.get('control_uid'),
        'model':'F(s)=A*D_N(s)*P_Z(s)/D_N(2); E(s)=abs(F(s))**2',
        'dirichlet_basis':basis,'terms':n,'amplitude':amplitude,
        'coefficients':'prime:1+q_j or alternating:(-1)^j; q_j=j mod 2',
        'inserted_zeros':[{'sigma':u,'imaginary':v} for u,v in zeros],
        'zero_factor':'P_Z(s)=product((s-z)*(s-conj(z))/(1+abs(z)**2))',
        'normalization_d2':d2.real,'events':events,'checks':checks,'verified':True,
        'epistemic_scope':'dimensionless finite mathematical audio control; prescribed zeros are algebraically inserted, not zeta discoveries; no physical vacuum energy or RH proof'
    }
    result['control_uid']=hashlib.sha256(_canon(result).encode('utf-8')).hexdigest()
    return result
