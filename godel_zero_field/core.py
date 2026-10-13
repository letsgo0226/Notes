"""Exact integer, rational and symbolic Cosmic Love field; NO floating point.

E257 canonical UTF-8 Gödel coding. A description encoded as a natural number
is not an exact numerical solution to every equation the description denotes.
"""
import hashlib
import json
from fractions import Fraction
from math import isqrt

SEED = 55067263
PROTOCOL = 'COSMIC-LOVE-GODEL-ZERO-FIELD/1'
MAX_SERIALIZED_BYTES = 16000

def e257(blob):
    if type(blob) is not bytes or len(blob) > MAX_SERIALIZED_BYTES:
        raise ValueError('invalid byte string size')
    n = 1
    for b in blob:
        n = 257 * n + b + 1
    return n

def un257(n):
    if type(n) is not int or n < 1:
        raise ValueError('invalid Gödel natural number')
    out = bytearray()
    while n > 1:
        n, r = divmod(n, 257)
        if r == 0 or len(out) >= MAX_SERIALIZED_BYTES:
            raise ValueError('not an E257 code')
        out.append(r - 1)
    return bytes(reversed(out))

def _no_floats(o):
    if type(o) is float:
        raise ValueError('floating values forbidden')
    if type(o) is dict:
        if not all(type(k) is str for k in o):
            raise ValueError('keys must be strings')
        for v in o.values():
            _no_floats(v)
    elif type(o) in (list, tuple):
        for v in o:
            _no_floats(v)
    elif type(o) not in (str, int, bool, type(None)):
        raise ValueError('unsupported value type')

def pack(record):
    """Encode a finite structured expression losslessly as a Gödel natural."""
    _no_floats(record)
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(raw) > MAX_SERIALIZED_BYTES:
        raise ValueError('record too large')
    return '0x' + format(e257(raw), 'x')

def unpack(hex_code):
    if type(hex_code) is not str or not hex_code.startswith('0x') or len(hex_code) < 3:
        raise ValueError('hex Gödel code required')
    try:
        raw = un257(int(hex_code[2:], 16))
        obj = json.loads(raw)
    except (ValueError, UnicodeError, json.JSONDecodeError) as e:
        raise ValueError('invalid Gödel record') from e
    _no_floats(obj)
    if pack(obj) != hex_code.lower():
        raise ValueError('noncanonical Gödel record')
    return obj

def qrecord(q):
    if type(q) is not Fraction:
        raise ValueError('Fraction required')
    return {'type': 'Q', 'num': str(q.numerator), 'den': str(q.denominator)}

def rational_code(q):
    return pack(qrecord(q))

def decode_rational(code):
    obj = unpack(code)
    if type(obj) is not dict or set(obj) != {'type','num','den'} or obj['type'] != 'Q':
        raise ValueError('not a rational')
    num, den = obj['num'], obj['den']
    if not isinstance(num, str) or not isinstance(den, str) or not num.lstrip('-').isdigit() or not den.isdigit():
        raise ValueError('invalid rational digits')
    if (num.startswith('0') and num != '0') or (num.startswith('-0')) or (den.startswith('0')):
        raise ValueError('noncanonical digits')
    if len(num) > 10000 or len(den) > 10000 or int(den) == 0:
        raise ValueError('invalid rational length or denominator')
    q = Fraction(int(num), int(den))
    if qrecord(q) != obj:
        raise ValueError('not normalized')
    return q

def machine_rules():
    v = (isqrt(8*SEED+1)-1)//2
    c = SEED-v*(v+1)//2
    k = v-c+1
    if k != 2:
        raise ValueError('wrong TM size')
    K = k+1
    B = 4*K
    result = []
    for q in (0,1):
        for a in (0,1):
            u = c//B**(2*q+a)%B
            z, r = divmod(u,K)
            rule = (r,z//2,2*(z%2)-1)
            if rule != (1-q,a,1-2*q):
                raise ValueError('TM transition mismatch')
            result.append(rule)
    return tuple(result)

def coefficients(n):
    if type(n) is not int or not 2 <= n <= 64 or n % 2:
        raise ValueError('n must be even, 2..64')
    rules = machine_rules()
    q = h = 0
    tape = {}
    out = []
    for i in range(n):
        out.append(q+1)
        a = tape.get(h, 0)
        nq,b,d = rules[2*q+a]
        if b: tape[h] = b
        else: tape.pop(h,None)
        q,h = nq,h+d
    if (q,h,tape) != (0,0,{}):
        raise ValueError('two-step closure failed')
    return tuple(out)

def exact_D(n,s):
    if type(s) is not int or not -8 <= s <= 8:
        raise ValueError('integer s required, -8..8')
    return sum((Fraction(a, j**s) if s >= 0 else Fraction(a*j**(-s),1)
                for j,a in enumerate(coefficients(n),1)), Fraction(0))

def expression(n):
    coeff = coefficients(n)
    return {'kind':'FINITE_DIRICHLET_EXPRESSION', 'seed':str(SEED),
            'terms': [{'coefficient':str(a),'base':str(i),'factor':'n^(-s)'}
                      for i,a in enumerate(coeff,1)],
            's':'SYMBOLIC_COMPLEX_VARIABLE',
            'normalized_field':'A*D_N(s)/D_N(2)',
            'energy_proxy':'F(s)*conjugate(F(s))',
            'zero_factor_inserted':False,
            'not_riemann_zeta':True}

def evaluate_integer(n,s,amplitude_num=1,amplitude_den=1):
    for v in (amplitude_num,amplitude_den):
        if type(v) is not int or abs(v) > 10**9:
            raise ValueError('amplitude integers out of bounds')
    if amplitude_den <= 0:
        raise ValueError('positive amplitude denominator required')
    A = Fraction(amplitude_num,amplitude_den)
    if A < 0 or A > 10:
        raise ValueError('amplitude must be in [0,10]')
    d = exact_D(n,s)
    anchor = exact_D(n,2)
    F = A*d/anchor
    E = F**2
    statement = {
        'protocol':PROTOCOL, 'mode':'EXACT_RATIONAL_EVALUATION',
        'n_godel':rational_code(Fraction(n,1)),
        's_godel':rational_code(Fraction(s,1)),
        'amplitude_godel':rational_code(A),
        'D_godel':rational_code(d),
        'D2_godel':rational_code(anchor),
        'F_godel':rational_code(F),
        'E_godel':rational_code(E),
        'expression_godel':pack(expression(n)),
        'not_physical_energy':True,
        'zero_verified': F==0,
        'proof_scope':'EXACT_FRACTION_AT_INTEGER_ARGUMENT_ONLY'
    }
    return statement

def symbolic_root_n2(k=0):
    """Complete exact parameterization for D_2(s)=1+2*2**(-s).

    Using exp(i*(2k+1)*pi)=-1: s=1+i*(2k+1)*pi/log(2).
    The expression is serialized, NOT approximated/evaluated.
    """
    if type(k) is not int or not -1000 <= k <= 1000:
        raise ValueError('root index out of bounds')
    if coefficients(2)!=(1,2):
        raise ValueError('unexpected n2 coefficients')
    odd=2*k+1
    exact={'kind':'EXACT_SYMBOLIC_ROOT', 'function':'1+2*2^(-s)',
           're':'1','im':{'numerator':str(odd),'factor':'pi','denominator':'log(2)'},
           'derivation':'2^(-s)=(-1)/2 via exp(-i*(2k+1)*pi)=-1',
           'k':str(k), 'root_is_prescribed_by_model':False,
           'applies_only_to':'N=2 positive-weight Dirichlet family',
           'zeta_root_claim':False}
    return {'protocol':PROTOCOL,'mode':'SYMBOLIC_ZERO_FAMILY',
            'root_godel':pack(exact), 'n_godel':rational_code(Fraction(2)),
            'root_is_approximation':False,
            'verification':'ALGEBRAIC_IDENTITY_WITH_EULER_EXPONENTIAL',
            'zero_factor_inserted':False}

def model_certificate(n):
    return {'protocol':PROTOCOL,'mode':'SYMBOLIC_FORMAL_MODEL',
            'model_godel':pack(expression(n)),
            'n_godel':rational_code(Fraction(n)),
            'zero_search_status':'EXACT_ROOTS_UNRESOLVED_FOR_GENERAL_N' if n > 2
                                 else 'SYMBOLIC_ROOT_FAMILY_AVAILABLE',
            'not_physical_energy':True,
            'no_decimal_approximations':True}

def verify_evaluation(receipt):
    if type(receipt) is not dict or receipt.get('mode')!='EXACT_RATIONAL_EVALUATION':
        raise ValueError('wrong receipt type')
    n=decode_rational(receipt['n_godel'])
    s=decode_rational(receipt['s_godel'])
    a=decode_rational(receipt['amplitude_godel'])
    if n.denominator!=1 or s.denominator!=1:
        raise ValueError('not integer arguments')
    expected=evaluate_integer(int(n),int(s),a.numerator,a.denominator)
    if receipt != expected: raise ValueError('altered or unsupported receipt')
    return True

def receipt_digest(receipt):
    return hashlib.sha256(pack(receipt).encode('ascii')).hexdigest()
