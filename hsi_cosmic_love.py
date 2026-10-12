#!/usr/bin/env python3
"""COSMIC_LOVE: finite validation of a two-step identity binary Turing machine.

This module does not access networks, credentials, exchanges, GitHub, Railway,
or the file system (apart from normal Python imports). No trader integration.
A finite table check plus a short algebraic proof support the identity claim
for all binary tapes, head coordinates and q in {0, 1}.
"""
import argparse
import json
from math import isqrt

PROGRAM = 55067263
MARKER = "COSMIC_LOVE"
EXPECTED_K = 2
EXPECTED_TABLE = {
    (0, 0): (1, 0, 1),
    (0, 1): (1, 1, 1),
    (1, 0): (0, 0, -1),
    (1, 1): (0, 1, -1),
}


def decode(program=PROGRAM):
    """Decode the user's triangular pairing and base-4(k+1) rule digits."""
    if type(program) is not int or program < 0:
        raise ValueError("invalid program")
    diagonal = (isqrt(8 * program + 1) - 1) // 2
    code = program - diagonal * (diagonal + 1) // 2
    states = diagonal - code + 1
    if states != EXPECTED_K:
        raise ValueError("invalid state space")
    radix = 4 * (states + 1)
    table = {}
    for q in range(states):
        for symbol in (0, 1):
            digit = code // radix ** (2 * q + symbol) % radix
            quotient, next_state = divmod(digit, states + 1)
            table[(q, symbol)] = (
                next_state, quotient // 2, 2 * (quotient % 2) - 1
            )
    return {
        "program": program,
        "diagonal": diagonal,
        "code": code,
        "k": states,
        "radix": radix,
        "table": table,
    }


def transition(config, tape, table=None):
    """One step on an arbitrary *finite nonzero-support* binary tape sample.

    Zero is the implicit blank value. This implementation supports tests of
    representative finite tapes; the algebraic identity is independent of
    the size or position of the written nonzero support.
    """
    q, head = config
    if type(q) is not int or q not in (0, 1) or type(head) is not int:
        raise ValueError("invalid configuration")
    if not isinstance(tape, dict) or any(
        type(pos) is not int or type(bit) is not int or bit not in (0, 1)
        for pos, bit in tape.items()
    ):
        raise ValueError("invalid binary tape")
    table = EXPECTED_TABLE if table is None else table
    symbol = tape.get(head, 0)
    next_state, written, delta = table[(q, symbol)]
    next_tape = dict(tape)
    if written:
        next_tape[head] = 1
    else:
        next_tape.pop(head, None)
    return (next_state, head + delta), next_tape


def verify(program=PROGRAM):
    decoded = decode(program)
    if decoded["table"] != EXPECTED_TABLE:
        raise ValueError("transition defect")
    checked = 0
    # Exhaust the 2 initial states and 2^2 values at the two visited cells.
    for q in (0, 1):
        for first in (0, 1):
            for second in (0, 1):
                step_dir = 1 - 2 * q
                start_tape = {0: first, step_dir: second}
                config = (q, 0)
                once = transition(config, start_tape, decoded["table"])
                twice = transition(*once, decoded["table"])
                if twice != (config, {pos: val for pos, val in
                                     start_tape.items() if val}):
                    raise ValueError("two-step cycle defect")
                checked += 1
    return {
        "protocol": "HSI-COSMIC-LOVE-TWO-STEP/1",
        "marker": MARKER,
        "program": program,
        "diagonal": decoded["diagonal"],
        "code": decoded["code"],
        "nonhalting_state_count": decoded["k"],
        "radix": decoded["radix"],
        "rules_checked": len(decoded["table"]),
        "local_cycles_checked": checked,
        "finite_validation": "PASSED",
        "mathematical_statement": "F(F(q,h,T))=(q,h,T) for q in {0,1}, h in Z, any binary tape T",
        "proof_basis": (
            "Each transition writes back the read bit a, toggles state q, "
            "and moves d=1-2q; the next transition again preserves the bit, "
            "toggles back to q, and moves -d. All other cells are untouched."
        ),
        "limitations": (
            "The code checks the four rules and eight local cases; "
            "the universal claim follows from the separately stated algebra, "
            "not from testing infinitely many tapes. "
            "No physical, cosmological or moral claim is proved."
        ),
        "broker_calls": 0,
        "live_trading_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a review certificate")
    args = parser.parse_args()
    try:
        result = verify()
    except ValueError as exc:
        parser.exit(2, "VERIFY_FAILED: " + str(exc) + "\n")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
