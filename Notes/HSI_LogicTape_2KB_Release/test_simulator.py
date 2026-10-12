#!/usr/bin/env python3
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import subprocess
import tempfile
import sys
import verify_single_tape as ref

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "hsi_logic_tape_2kb.sh"
checks = []


def check(name, condition, **detail):
    checks.append(dict(name=name, passed=bool(condition), **detail))
    if not condition:
        raise RuntimeError(name)


def run(source, output, program="", budget="", resume=False):
    responses = [str(source)] + ([] if resume else [str(program)]) + [str(budget), str(output)]
    process = subprocess.run(["sh", str(SCRIPT)], input="\n".join(responses) + "\n",
                             cwd=source.parent, text=True, capture_output=True, timeout=50)
    if process.returncode:
        raise RuntimeError(process.stderr)
    return ref.load_checkpoint(str(output) + ".json")


def main():
    code = SCRIPT.read_bytes()
    check("whole_command_strictly_sub2KB", len(code) < 2048,
          including_LF=len(code), excluding_LF=len(code.rstrip(b"\n")))
    check("one_physical_line", len(code.splitlines()) == 1)
    unpacked = subprocess.run(["sh", "-c", code.decode().replace("python3 -c", "printf '%s'", 1)],
                              capture_output=True, check=True).stdout
    check("shell_quoting_and_printf_exact_source", unpacked == (ROOT / "core.py").read_bytes().rstrip(b"\n"))
    check("no_SHA_network_or_compressed_payload",
          all(x not in code.lower() for x in (b"hashlib", b"sha256", b"zlib", b"base85", b"urllib", b"requests")))
    with tempfile.TemporaryDirectory(prefix="single-tape-tests-") as tmp:
        directory = Path(tmp)
        source = directory / "中文 空格.pdf"
        data = bytes(range(256)) * 300
        source.write_bytes(data)
        state, image = run(source, directory / "identity.tm")
        check("default_1829_preserves_binary_file", image == data and state["status"] == "HALTED"
              and state["t"] == 1, input_bytes=len(data))
        check("default_run_independently_replayed",
              ref.verify(source, directory / "identity.tm.json")["status"] == "REPLAY_VERIFIED")
        check("source_not_modified", source.read_bytes() == data)

        # -1 embeds any finite byte string as a tape snapshot without taking a TM step.
        for name, payload in (("empty", b""), ("all-bytes", bytes(range(256))),
                              ("zeros", b"\0" * 70001)):
            raw = directory / (name + ".raw");raw.write_bytes(payload)
            state, image = run(raw, directory / (name + ".encoded"), 1829, -1)
            check("reversible_encode_" + name, image == payload and state["q"] == 0
                  and state["h"] == state["t"] == state["lo"] == 0
                  and state["hi"] == len(payload))
            check("independent_encode_replay_" + name,
                  ref.verify(raw, directory / (name + ".encoded.json"))["status"] == "REPLAY_VERIFIED")

        right = ref.encode_table(1, [(0, 1, 1), (0, 1, 1)])
        left = ref.encode_table(1, [(0, 1, -1), (0, 1, -1)])
        state, image = run(source, directory / "right.tm", right, 19)
        expected, tape = ref.replay(right, ref.initial(data), 19)
        check("cross_byte_boundaries", image == tape and all(state[k] == v for k, v in expected.items()))
        run(source, directory / "right-encoded.tm", right, -1)
        state2, image2 = run(directory / "right-encoded.tm.json",
                             directory / "right-resumed.tm", budget=19, resume=True)
        check("reversible_encode_then_resume_matches_direct_run", image2 == image
              and all(state2[k] == state[k] for k in ("p", "q", "h", "t", "lo", "hi", "status")))

        state, image = run(source, directory / "left.tm", left, 40)
        expected, tape = ref.replay(left, ref.initial(data), 40)
        check("negative_positions_and_full_image", image == tape and state["lo"] == -5
              and state["h"] == -40 and all(state[k] == v for k, v in expected.items()))

        run(source, directory / "part1.tm", left, 17)
        state, image = run(directory / "part1.tm.json", directory / "part2.tm", budget=23, resume=True)
        full, full_image = ref.load_checkpoint(directory / "left.tm.json")
        check("resume_matches_single_run_across_zero", image == full_image
              and all(state[k] == full[k] for k in ("p", "q", "h", "t", "lo", "hi", "status")))
        check("resume_independently_replayed", ref.verify(directory / "part1.tm.json",
              directory / "part2.tm.json", resume=True)["status"] == "REPLAY_VERIFIED")
        run(directory / "identity.tm.json", directory / "halted-resume.tm", budget=5, resume=True)
        halted, halted_image = ref.load_checkpoint(directory / "halted-resume.tm.json")
        check("resume_halted_machine_takes_no_extra_steps", halted["t"] == 1 and halted_image == data)

        empty = directory / "empty.bin";empty.write_bytes(b"")
        state, image = run(empty, directory / "empty.tm", 0, 9)
        expected, tape = ref.replay(0, ref.initial(b""), 9)
        check("empty_input_and_program_zero", image == tape and all(state[k] == v for k, v in expected.items()))
        state, image = run(empty, directory / "unlimited-halt.tm", 1829, 0)
        check("unlimited_mode_can_halt", state["status"] == "HALTED" and state["t"] == 1)

        large = directory / "large.bin";large.write_bytes(bytes(65538))
        steps = 8 * 65536 + 1
        state, image = run(large, directory / "large.tm", right, steps)
        check("head_crosses_65536_byte_load_boundary_without_reset",
              state["h"] == steps and state["t"] == steps and state["q"] == 0
              and image == b"\xff" * 65536 + b"\x01\x00", transitions=steps)

        # No fixed upper bound on the number of finite machine states.
        k = 512
        rules = [(k, 0, 1), (k, 1, 1)] + [(k, 0, 1)] * (2*k - 2)
        program = ref.encode_table(k, rules)
        state, image = run(source, directory / "many-states.tm", program, 1)
        check("512_state_program_without_artificial_state_cap", state["q"] == k
              and state["status"] == "HALTED" and image == data)

        rng = random.Random(121026)
        for index in range(48):
            halt = rng.randrange(1, 7)
            table = [(rng.randrange(halt+1), rng.randrange(2), rng.choice((-1, 1)))
                     for _ in range(2*halt)]
            program = ref.encode_table(halt, table)
            data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 20)))
            fresh = directory / ("random" + str(index) + ".bin");fresh.write_bytes(data)
            budget = rng.randrange(1, 100)
            state, image = run(fresh, directory / ("random" + str(index) + ".tm"), program, budget)
            expected, tape = ref.replay(program, ref.initial(data), budget)
            if image != tape or any(state[key] != value for key, value in expected.items()):
                raise RuntimeError("random transition mismatch " + str(index))
        check("48_random_tables_against_independent_bit_dictionary", True)

        # Mismatched coordinate/image lengths must not be silently accepted on resume.
        bad, _ = ref.load_checkpoint(directory / "part1.tm.json")
        bad["hi"] += 1
        corrupt = directory / "bad.json";corrupt.write_text(json.dumps(bad))
        result = subprocess.run(["sh", str(SCRIPT)], input=str(corrupt) + "\n1\nbad-output.tm\n",
                                cwd=directory, capture_output=True, text=True, timeout=10)
        check("inconsistent_resume_image_length_rejected", result.returncode != 0
              and not (directory / "bad-output.tm").exists())

        existing = directory / "existing.tm";existing.write_bytes(b"preserve")
        result = subprocess.run(["sh", str(SCRIPT)], input=str(source) + "\n\n\n" + str(existing) + "\n",
                                cwd=directory, capture_output=True, text=True, timeout=10)
        check("existing_output_not_overwritten", result.returncode != 0 and existing.read_bytes() == b"preserve")

    report = dict(protocol="HSI-LOGIC-TAPE-TEST/1", timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  simulator_file_bytes=len(code), simulator_command_bytes=len(code.rstrip(b"\n")),
                  total_checks=len(checks), all_checks_passed=all(c["passed"] for c in checks), checks=checks,
                  platform=sys.platform, python=sys.version.split()[0],
                  scope="Reversible finite-file tape embedding, finite execution evidence, and complete signed-coordinate tape images; not compression")
    (ROOT / "simulation_certificate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("simulator_file_bytes", "total_checks", "all_checks_passed")}))


if __name__ == "__main__":main()
