"""Finite computational witness for Gaussian-cardinal interpolation.
The theorem for all bounded sequences is stated in XY_SPEC.md.
"""
import cmath
import json
import math

def encode_bytes(text):
    value = 1
    for byte in text.encode('utf-8'):
        value = value * 257 + byte + 1
    return value

def decode_bytes(value):
    digits = []
    while value > 1:
        value, rem = divmod(value, 257)
        if rem == 0:
            raise ValueError('not a Base-257 string encoding')
        digits.append(rem - 1)
    if value != 1:
        raise ValueError('not a Base-257 string encoding')
    return bytes(reversed(digits)).decode('utf-8')

def normalized_godel(code):
    if code < 0:
        raise ValueError('requires nonnegative code')
    return code / (1 + code)  # for demonstration only; arbitrary-precision exact: fractions.Fraction

def cardinal(z, n):
    if isinstance(z, int):
        return complex(int(z == n))
    t = z - n
    return cmath.exp(-t*t) * cmath.sin(math.pi*t)/(math.pi*t) if t else 1+0j

def interpolate(samples, z):
    """A finite entire interpolant of sampled normalized output codes.
    For integer z in sample index range the value is the exact selected sample
    up to floating-point conversion; symbolic equality is a separate theorem.
    """
    return sum(b * cardinal(z,n) for n,b in enumerate(samples))

def dirichlet(residuals, s):
    return sum(v*p**(-s) for v,p in zip(residuals,(2,3,5)))

if __name__ == '__main__':
    examples = [0,1,2,3,5]
    samples = [normalized_godel(g) for g in examples]
    print(json.dumps({'sample_y':samples,'at_integers':[
        interpolate(samples,n).real for n in range(len(samples))],
        'off_axis_example':str(interpolate(samples,1.5+0.5j)),
        'D_zero':str(dirichlet((0,0,0),1+1j)),
        'D_incompatible':str(dirichlet((1,0,0),1+1j))}))