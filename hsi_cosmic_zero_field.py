#!/usr/bin/env python3
"""Finite, auditable complex zero-field DSP control; not physical zero-point energy."""
import hashlib
import json
import math
import os

PROTOCOL = 'HSI-COSMIC-ZERO-FIELD/1.0'
TM_PROGRAM = 55067263
DEFAULT_GAMMA = 14.134725141734693


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _settings():
    n = int(os.getenv('HSI_ZERO_FIELD_TERMS', '32'))
    gamma = float(os.getenv('HSI_ZERO_FIELD_GAMMA', str(DEFAULT_GAMMA)))
    amplitude = float(os.getenv('HSI_ZERO_FIELD_AMPLITUDE', '1'))
    if not 8 <= n <= 128:
        raise ValueError('HSI_ZERO_FIELD_TERMS must be 8..128')
    if not math.isfinite(gamma) or not 0.01 <= gamma <= 80:
        raise ValueError('HSI_ZERO_FIELD_GAMMA must be finite within 0.01..80')
    if not math.isfinite(amplitude) or not 0.01 <= amplitude <= 2:
        raise ValueError('HSI_ZERO_FIELD_AMPLITUDE must be finite within 0.01..2')
    return n, gamma, amplitude


def _coefficients(tm, n):
    if not tm.get('verified') or tm.get('program') != TM_PROGRAM:
        raise ValueError('zero field requires verified COSMIC_LOVE TM')
    rows = tm.get('transition_table')
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError('invalid TM transition table')
    expected = [(q, a, 1-q, a, 1-2*q) for q in (0, 1) for a in (0, 1)]
    if [(r.get('q'), r.get('a'), r.get('next_q'), r.get('write'), r.get('direction')) for r in rows] != expected:
        raise ValueError('TM transitions differ from verified two-cycle')
    # The empty-tape trajectory alternates q=0 and q=1 without modifying tape.
    return [rows[2*(i % 2)]['direction'] for i in range(n)]


def _dirichlet(s, coefficients):
    return sum(a * pow(i + 1, -s) for i, a in enumerate(coefficients))


def _function(s, coefficients, gamma, amplitude, d2):
    z = complex(0.5, gamma)
    normalized_zeros = (s-z)*(s-z.conjugate()) / ((2-z)*(2-z.conjugate()))
    return amplitude * _dirichlet(s, coefficients) * normalized_zeros / d2


def build_zero_field(tm_control, event_count):
    if os.getenv('HSI_ZERO_FIELD', '1') == '0':
        return {'protocol': PROTOCOL, 'enabled': False, 'reason': 'disabled_by_environment'}
    if not tm_control.get('enabled'):
        return {'protocol': PROTOCOL, 'enabled': False, 'reason': 'cosmic_love_tm_disabled'}
    if not isinstance(event_count, int) or not 1 <= event_count <= 512:
        raise ValueError('event_count must be 1..512')
    n, gamma, amplitude = _settings()
    coefficients = _coefficients(tm_control, n)
    d2 = _dirichlet(2+0j, coefficients)
    if abs(d2) < 1e-10:
        raise ValueError('Dirichlet normalization denominator too small')
    positive_zero = complex(0.5, gamma)
    negative_zero = positive_zero.conjugate()
    checks = {
        'verified_two_cycle_coefficients': coefficients == [1 if i % 2 == 0 else -1 for i in range(n)],
        'inserted_positive_zero': abs(_function(positive_zero, coefficients, gamma, amplitude, d2)) < 1e-12,
        'inserted_negative_zero': abs(_function(negative_zero, coefficients, gamma, amplitude, d2)) < 1e-12,
        'normalized_at_s_2': abs(_function(2+0j, coefficients, gamma, amplitude, d2)-amplitude) < 1e-12,
    }
    energies = []
    for i in range(event_count):
        t = gamma * (0.75 + 0.5 * (i/(event_count-1) if event_count > 1 else 0.5))
        e = abs(_function(complex(0.5, t), coefficients, gamma, amplitude, d2)) ** 2
        energies.append((t, e))
    checks['finite_nonnegative_samples'] = all(math.isfinite(e) and e >= 0 for _, e in energies)
    if not all(checks.values()):
        raise ValueError('zero-field finite checks failed')
    peak = max(e for _, e in energies)
    events = []
    for t, e in energies:
        u = min(1.0, max(0.0, e/peak if peak > 0 else 0.0))
        events.append({
            'imaginary_s': round(t, 12), 'energy': round(e, 12),
            'unit_energy': round(u, 12),
            'rate_delta': round(0.018 * (2*u-1), 12),
            'pan_delta': round(0.075 * (2*u-1), 12),
            'gain_multiplier': round(0.94+0.12*u, 12),
        })
    result = {
        'protocol': PROTOCOL, 'enabled': True,
        'tm_control_uid': tm_control.get('control_uid'),
        'model': 'F(s)=A*D_N(s)*P_Z(s)/D_N(2); E(s)=abs(F(s))**2',
        'dirichlet_coefficients': 'TM directions +1,-1 repeating',
        'terms': n, 'amplitude': amplitude,
        'inserted_zero_sigma': 0.5, 'inserted_zero_imaginary': gamma,
        'zero_factor': 'P_Z(s)=((s-z)*(s-conj(z)))/((2-z)*(2-conj(z)))',
        'normalization_d2': d2.real, 'events': events,
        'checks': checks, 'verified': True,
        'epistemic_scope': 'dimensionless computational music modulation; inserted zeros by construction; no physical zero-point energy or RH proof',
    }
    result['control_uid'] = hashlib.sha256(_canon(result).encode('utf-8')).hexdigest()
    return result
