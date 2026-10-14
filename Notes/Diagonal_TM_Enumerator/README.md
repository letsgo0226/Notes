# Diagonal TM Enumerator

Enumerates every binary-tape Turing machine with `n` states (each `(state, symbol)` is either undefined or
`(next state or HALT, write bit, move L/R)`) and runs them on a blank tape with a fair diagonal schedule:
round `r` takes the first `r` machines of each size `n ≤ r` and runs each for `r` steps.

Each machine is classified as:
- `CLOSED`: it reached an undefined transition
- `FIX`: it reached HALT, so the configuration stops changing; the tape snapshot before and after is written in ATGC (`00→A, 01→T, 10→G, 11→C`)
- `OPEN`: still running after `r` steps (not decided; this is not a halting decider)

With no argument it runs forever; `bash diagonal_tm_enumerator.sh 14` stops after 14 rounds.
The first `FIX` appears in round 10: `SAMPLE_FIX=(1, 9, 1, 'A')`.

## Fix from the first version
The first version crashed at round 10 with `TypeError: unsupported operand type(s) for <<: 'str' and 'int'`,
because the tape snapshot is a string of `"0"/"1"` characters. This version encodes each pair with
`'ATGC'[int(a+b,2)]`, which reads the two characters as a 2-bit binary number.

## Run
```bash
bash diagonal_tm_enumerator.sh 14          # matches expected_14.txt
nohup setsid bash diagonal_tm_enumerator_daemon.sh >/dev/null 2>&1 &   # resident loop, 1s
touch run/KILL                              # stop
```
