#!/usr/bin/env python3
"""Independent binary TM replay; not part of the sub-2KB executable."""
import argparse
import json
from math import isqrt
from pathlib import Path
import sys

getattr(sys, "set_int_max_str_digits", lambda n: None)(0)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode_program(program):
    require(type(program) is int and program >= 0, "invalid program")
    diagonal = isqrt(2 * program)
    while diagonal * (diagonal + 1) // 2 > program:
        diagonal -= 1
    while (diagonal + 1) * (diagonal + 2) // 2 <= program:
        diagonal += 1
    code = program - diagonal * (diagonal + 1) // 2
    halt = diagonal - code + 1
    states = halt + 1
    radix = 4 * states
    table = []
    for _ in range(2 * halt):
        code, digit = divmod(code, radix)
        table.append((digit % states, digit // (2 * states),
                      1 if digit // states % 2 else -1))
    return halt, table


def encode_table(halt, table):
    require(type(halt) is int and halt >= 1 and len(table) == 2 * halt, "invalid table")
    states, code, multiplier = halt + 1, 0, 1
    radix = 4 * states
    for next_state, write, move in table:
        require(0 <= next_state <= halt and write in (0, 1) and move in (-1, 1), "invalid rule")
        digit = next_state + states * (move == 1) + 2 * states * write
        code += digit * multiplier
        multiplier *= radix
    diagonal = code + halt - 1
    return diagonal * (diagonal + 1) // 2 + code


def initial(data, origin=0, state=0, head=0, steps=0):
    cells = {}
    for position, byte in enumerate(data, origin):
        for bit in range(8):
            if (byte >> bit) & 1:
                cells[8 * position + bit] = 1
    return dict(q=state, h=head, t=steps, lo=origin, hi=origin + len(data), cells=cells)


def replay(program, start, budget):
    halt, table = decode_program(program)
    q, h, t, lo, hi = (start[x] for x in ("q", "h", "t", "lo", "hi"))
    require(all(type(x) is int for x in (q, h, t, lo, hi, budget))
            and 0 <= q <= halt and t >= 0 and budget >= 0, "invalid configuration or budget")
    cells = dict(start["cells"])
    executed = 0
    while q != halt and executed < budget:
        byte_position = h // 8
        lo, hi = min(lo, byte_position), max(hi, byte_position + 1)
        next_state, write, movement = table[2 * q + cells.get(h, 0)]
        if write:
            cells[h] = 1
        else:
            cells.pop(h, None)
        h += movement
        q = next_state
        t += 1
        executed += 1
    image = bytearray(hi - lo)
    for cell in cells:
        byte_position, bit = divmod(cell, 8)
        require(lo <= byte_position < hi, "nonblank cell outside saved image")
        image[byte_position - lo] |= 1 << bit
    return dict(protocol="HSI-ST/1", p=str(program), q=q, h=h, t=t, lo=lo, hi=hi,
                status="HALTED" if q == halt else "UNRESOLVED"), bytes(image)


def load_checkpoint(path):
    path = Path(path)
    record = json.loads(path.read_text())
    require(type(record) is dict and record.get("protocol") == "HSI-ST/1", "invalid checkpoint schema")
    require(type(record.get("p")) is str and type(record.get("image")) is str, "invalid checkpoint fields")
    for key in ("q", "h", "t", "lo", "hi"):
        require(type(record.get(key)) is int, "invalid integer field: " + key)
    program = int(record["p"])
    halt, _ = decode_program(program)
    require(0 <= record["q"] <= halt and record["t"] >= 0 and record["hi"] >= record["lo"], "invalid state")
    image = (path.parent / record["image"]).read_bytes()
    require(len(image) == record["hi"] - record["lo"], "image length differs from coordinates")
    require(record.get("status") == ("HALTED" if record["q"] == halt else "UNRESOLVED"), "invalid status")
    return record, image


def verify(source, output, resume=False):
    observed, observed_image = load_checkpoint(output)
    if resume:
        before, data = load_checkpoint(source)
        require(before["p"] == observed["p"], "program changed across resume")
        start = initial(data, before["lo"], before["q"], before["h"], before["t"])
    else:
        start = initial(Path(source).read_bytes())
    budget = observed["t"] - start["t"]
    require(budget >= 0, "step counter went backwards")
    expected, image = replay(int(observed["p"]), start, budget)
    require(all(observed[key] == value for key, value in expected.items()), "state differs from independent replay")
    require(observed_image == image, "magnetic tape bytes differ from independent replay")
    return dict(status="REPLAY_VERIFIED", transitions=budget, origin=expected["lo"],
                end=expected["hi"], image_bytes=len(image),
                scope="Given initial configuration and declared finite transition count")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="original input file, or preceding .json with --resume")
    parser.add_argument("output", help="result .json")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.source, args.output, args.resume)))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps(dict(status="REJECT", reason=str(exc))), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
