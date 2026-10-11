#!/usr/bin/env python3
"""Independent finite HSI 2KB, prime-encoding and analytic-interpolation audit.

No execution of compressed Base85/zlib loaders; runs only the supplied plaintext
reference and Bash single-line plaintext candidate in isolated temporary dirs.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from fractions import Fraction
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'HSI_OriginalXY_Plaintext_2KB_OneLiner.sh'
CANDIDATE_POSIX = ROOT / 'HSI_OriginalXY_POSIX_2KB_OneLiner.sh'
REFERENCE = ROOT / 'OriginalXY_reference.py'
CORE = ROOT / 'HSI_OriginalXY_Plaintext_Core.py'


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def j(v):
    return json.dumps(v, separators=(',', ':'), ensure_ascii=True)


def e257(bs: bytes) -> int:
    n = 1
    for v in bs:
        n = n * 257 + v + 1
    return n


def d257(n: int) -> bytes:
    if n < 1:
        raise ValueError('invalid positive E257 integer')
    v = []
    while n > 1:
        n, r = divmod(n, 257)
        if not 1 <= r <= 256:
            raise ValueError('invalid E257 digit')
        v.append(r - 1)
    return bytes(reversed(v))


def wilson_prime(n: int) -> bool:
    return n >= 2 and (math.factorial(n - 1) + 1) % n == 0


def small_primes(k: int):
    result = []
    n = 2
    while len(result) < k:
        if all(n % p for p in result if p * p <= n):
            result.append(n)
        n += 1
    return result


def bit_prefix(data: bytes, length: int):
    all_bits = [((byte >> shift) & 1) for byte in data for shift in range(7, -1, -1)]
    bits = all_bits[:length]
    ps = small_primes(length)
    n = 1
    for p, bit in zip(ps, bits):
        n *= p ** (bit + 1)
    cursor, recovered = n, []
    for p in ps:
        k = 0
        while cursor % p == 0:
            cursor //= p
            k += 1
        recovered.append(k - 1)
    assert cursor == 1 and bits == recovered
    return {
        'length': length,
        'bits': ''.join(str(x) for x in bits),
        'primes': ps,
        'exponents': [b + 1 for b in bits],
        'godel_code': str(n),
        'roundtrip': True,
        'dirichlet_coefficients': [{'prime': p, 'coefficient': b + 1} for p, b in zip(ps, bits)],
        'formal_identity': "-D'(0)=sum_j (bit_j+1)*log(p_j)=log(G)",
    }


def lagrange_eval(values: list[Fraction], z: Fraction) -> Fraction:
    total = Fraction(0)
    for j, a in enumerate(values):
        basis = Fraction(1)
        for k in range(len(values)):
            if k != j:
                basis *= (z - k) / (j - k)
        total += a * basis
    return total


def vanishing_polynomial(n: int, z: Fraction) -> Fraction:
    x = Fraction(1)
    for i in range(n):
        x *= z - i
    return x


def run(kind: str, params: dict, state: Path):
    env = os.environ.copy()
    for k in ('HSI_STATE','HSI_WORD','HSI_LIMIT','HSI_BUDGET','HSI_TRACE','HSI_CAND','HSI_SLEEP'):
        env.pop(k, None)
    env.update(params)
    env['HSI_STATE'] = str(state)
    env['HSI_SLEEP'] = '0'
    cmd = (['bash', str(CANDIDATE)] if kind == 'plaintext_2kb' else ['sh', str(CANDIDATE_POSIX)] if kind == 'posix_2kb' else [sys.executable, str(REFERENCE)])
    proc = subprocess.run(cmd, env=env, cwd=state.parent, capture_output=True, timeout=25)
    check = state.read_bytes() if state.exists() else None
    return proc.returncode, proc.stdout, check, proc.stderr


def replay():
    tests = {
        '26_candidates': {'HSI_LIMIT':'26'},
        'alternate_word': {'HSI_LIMIT':'24', 'HSI_WORD':'10101'},
        'trace': {'HSI_LIMIT':'20', 'HSI_TRACE':'1'},
        'budget_skip': {'HSI_LIMIT':'30', 'HSI_BUDGET':'1'},
        'reject': {'HSI_LIMIT':'40', 'HSI_CAND':'[900,0,[]]'},
        'malformed_candidate': {'HSI_LIMIT':'12', 'HSI_CAND':'not-json'},
    }
    reports = {}
    first_sample = None
    with tempfile.TemporaryDirectory(prefix='hsi-prime-analytic-') as td:
        base = Path(td)
        for name, opts in tests.items():
            variants = []
            for kind in ('reference','plaintext_2kb','posix_2kb'):
                st = base / (name+'-'+kind+'.json')
                variants.append(run(kind, opts, st))
            a,b,c = variants
            ok = a[:3] == b[:3] == c[:3]
            assert ok, f'finite observational replay mismatch in {name}: {a[:2]} / {b[:2]}'
            reports[name] = {'pass':True,'exit_code':a[0], 'stdout_sha256':sha(a[1]),'emitted_lines':len(a[1].splitlines())}
            if name == '26_candidates':
                rows = [json.loads(line) for line in a[1].splitlines()]
                assert len(rows) == 26
                first_sample = rows[:8]
                for row in rows:
                    decoded = json.loads(d257(int(row['x'])))
                    assert decoded[0] == row['step']
                    if row.get('y'):
                        assert len(json.loads(d257(int(row['y'])))) == 4
                    if row.get('verified'):
                        assert row['D0'] == row['D1_num'] == row['Ehalf_num30'] == 0
            if name=='reject':
                assert a[0] == 3 and b'"kind":"REJECT"' in a[1]
        # Segmented and single-shot runs, including actual checkpoint bytes.
        segmented = []
        for kind in ('reference','plaintext_2kb','posix_2kb'):
            st = base / ('resume-'+kind+'.json')
            a = run(kind, {'HSI_WORD':'101','HSI_TRACE':'1','HSI_LIMIT':'6'}, st)
            b = run(kind, {'HSI_WORD':'101','HSI_TRACE':'1','HSI_LIMIT':'17'}, st)
            segmented.append((a[0], b[0], a[1]+b[1], b[2]))
        assert segmented[0] == segmented[1] == segmented[2]
        reports['resume'] = {'pass':True, 'emitted_lines':len(segmented[0][2].splitlines()), 'checkpoint_sha256':sha(segmented[0][3])}
    return reports, first_sample


def main():
    code = CANDIDATE.read_bytes()
    python_code = CORE.read_bytes()
    portable = CANDIDATE_POSIX.read_bytes()
    assert len(portable) < 2048 and portable.count(b'\n')==1
    assert not any(bad in portable for bad in [b'zlib', b'base64', b'b85decode', b'exec('])
    assert len(code) < 2048 and code.count(b'\n')==1 and code.endswith(b'\n')
    assert not any(bad in code for bad in [b'zlib',b'base64',b'b85decode',b'exec('])
    assert all(c < 128 for c in code)
    assert len(python_code) < 2048
    assert not any(bad in python_code for bad in [b'zlib',b'base64',b'exec('])
    # Wilson's finite criterion and prime-count/rank correspondence.
    assert [n for n in range(2, 30) if wilson_prime(n)] == small_primes(10)
    # Prime ordinal example from the supplied PRIME_FORMULA document: p_5 = 11.
    p5 = small_primes(5)[-1]
    ordinal_g = 2**(p5+1) * 3**(5+1)
    assert p5 == 11 and ordinal_g == 2**12*3**6
    tmp = ordinal_g
    for base,power in ((2,12),(3,6)):
        for _ in range(power):
            assert tmp % base == 0
            tmp //= base
    assert tmp == 1
    # Full command bit length and selected exact prime-power prefix.
    encoding = bit_prefix(code, 16)
    report_cases, rows = replay()
    # Every row including budget-skips has a canonical finite record, so b_n is total.
    normalized = [Fraction(g, g+1) for g in [e257(j(r).encode('utf-8')) for r in rows]]
    for i, v in enumerate(normalized):
        assert lagrange_eval(normalized, Fraction(i)) == v
    z=Fraction(1,2)
    fz=lagrange_eval(normalized, z)
    bump=vanishing_polynomial(len(normalized), z)
    assert bump != 0 and (fz + bump != fz)
    tampered = dict(rows[0]);tampered['step'] = tampered['step']+1
    assert e257(j(tampered).encode('utf-8')) != e257(j(rows[0]).encode('utf-8'))
    info = {
        'protocol':'HSI-PRIME-ANALYTIC-2KB/1.0',
        'status':'FINITE_TESTS_PASSED',
        'candidate':{'bytes':len(code),'physical_lines':len(code.splitlines()),'sha256':sha(code),'plaintext_no_compression':True,'self_contained':True,'shell_requirement':'Bash ANSI-C $-quoting','posix_shell_bytes':len(portable),'posix_sha256':sha(portable),'portable_shell_requirement':'POSIX sh + printf + python3'},
        'decoded_core':{'bytes':len(python_code),'sha256':sha(python_code)},
        'prime_formula':{'wilson_tested_n':'2..29','first_10_primes':small_primes(10),'prime_ordinal_example':{'rank':5,'prime':p5,'godel_code':str(ordinal_g)},'bit_prefix':encoding,'full_bit_count':len(code)*8,'whole_file_godel_product_materialized':False},
        'analytic_continuation':{'sample_count':len(normalized),'finite_lagrange_interpolation_exact':True,'polynomial_degree_lt_sample_count':True,'nonunique_entire_interpolant_witness':True,'chosen_domain':'f = selected interpolation polynomial restricted to open unit disk; Ω = C','open_set_identity_theorem_applies_only_after_f_chosen':True,'not_a_general_analytic_continuation_solver':True},
        'bounded_semantic_replay':report_cases,
        'limitations':['The small kernel omits selected input/checkpoint validation and fsync/durable checkpoint guarantees of reference.', 'Finite tests do not establish full program equivalence.', 'The analytic interpolant does not decide unsimulated TM halting.', 'No claim of Riemann Hypothesis or zeta zeros.', 'Prime-prefix encoding is not a byte-budget reduction of arbitrary source programs.']
    }
    out = ROOT/'verification_certificate.json'
    out.write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':info['status'],'one_liner_bytes':len(code),'posix_bytes':len(portable),'python_bytes':len(python_code),'cases_passed':len(report_cases),'certificate':out.name},ensure_ascii=False))

if __name__ == '__main__':
    main()
