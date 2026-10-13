"""Finite byte-string identity on the exact p=55067263 Turing-machine rules.

The mathematical statement covers every finite bytestring; this CLI caps
runtime input at 2048 bytes to bound time, tape support and response size.
"""
import argparse
import hashlib
import json
import sys
from math import isqrt
from .core import SEED, e257, un257

PROTOCOL = 'HSI-COSMIC-SOLUTION-IDENTITY/1'
MAX_INPUT_BYTES = 2048


def transitions(p=SEED):
    if type(p) is not int or p != SEED:
        raise ValueError('unsupported exact machine seed')
    v = (isqrt(8 * p + 1) - 1) // 2
    c = p - v * (v + 1) // 2
    k = v - c + 1
    if k != 2:
        raise ValueError('machine state cardinality mismatch')
    K = k + 1
    B = 4 * K
    rules = {}
    for q in (0, 1):
        for a in (0, 1):
            u = c // B ** (2 * q + a) % B
            z, r = divmod(u, K)
            actual = (r, z // 2, 2 * (z % 2) - 1)
            expected = (1 - q, a, 1 - 2 * q)
            if actual != expected:
                raise ValueError('machine transition failed independent check')
            rules[q, a] = actual
    return rules


def tape_encode(data):
    if type(data) is not bytes or len(data) > MAX_INPUT_BYTES:
        raise ValueError('bytes input exceeds bounded runtime domain')
    tape = {8 * i + j for i, x in enumerate(data) for j in range(8)
            if x & (128 >> j)}
    tape.add(8 * len(data))
    return tape


def tape_decode(tape):
    if type(tape) is not set or not tape or any(type(p) is not int or p < 0 for p in tape):
        raise ValueError('invalid binary tape')
    marker = max(tape)
    if marker % 8:
        raise ValueError('invalid length marker')
    length = marker // 8
    if length > MAX_INPUT_BYTES:
        raise ValueError('tape exceeds runtime budget')
    return bytes(sum((8 * i + j in tape) << (7 - j) for j in range(8))
                 for i in range(length))


def twice(data):
    tape = tape_encode(data)
    initial = tape.copy()
    rules = transitions()
    q = h = 0
    for _ in range(2):
        symbol = int(h in tape)
        q, written, direction = rules[q, symbol]
        if written:
            tape.add(h)
        else:
            tape.discard(h)
        h += direction
    if q != 0 or h != 0 or tape != initial:
        raise ValueError('two-step full-state closure failed')
    returned = tape_decode(tape)
    if returned != data:
        raise ValueError('lossless tape decoding failed')
    return returned


def proof(data):
    returned = twice(data)
    g = e257(returned)
    if un257(g) != data:
        raise ValueError('E257 Gödel inversion failed')
    return {'protocol': PROTOCOL,
            'statement': 'solution(s)=s',
            'proof_scope': 'FINITE_BYTES_IDENTITY_NOT_PROPOSITION_SOLVER',
            'byte_count': len(data),
            's_hex': data.hex(),
            'result_hex': returned.hex(),
            'godel_hex': hex(g),
            'sha256': hashlib.sha256(data).hexdigest(),
            'floating_point_used': False,
            'physical_energy_generated': False,
            'trading_authorized': False,
            'validated': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Bounded exact identity receipt')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--stdin', action='store_true', help='read raw bytes up to bounded limit')
    group.add_argument('--hex', dest='hex_data', help='hex-encoded byte string')
    group.add_argument('--text', help='UTF-8 string')
    args = parser.parse_args(argv)
    if args.stdin:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    elif args.hex_data is not None:
        if len(args.hex_data) > 2 * MAX_INPUT_BYTES or len(args.hex_data) % 2:
            parser.error('invalid input length')
        try:
            raw = bytes.fromhex(args.hex_data)
        except ValueError:
            parser.error('invalid hex bytes')
    else:
        raw = args.text.encode('utf-8')
    print(json.dumps(proof(raw), sort_keys=True, ensure_ascii=False,
                     separators=(',', ':')))


if __name__ == '__main__':
    main()
