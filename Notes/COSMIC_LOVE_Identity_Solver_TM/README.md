# COSMIC_LOVE Identity Solver TM

Same 2-state machine as `../COSMIC_LOVE_Oscillator_TM` (decoded from `p = 55067263`, `k=2`, `B=12`,
rule `step(q,a) = (1-q, a, 1-2q)`), now used as a terminating solver.

The input string `s` (argument, or `--stdin`) is written to the tape as bits, plus an end marker at `8*len(s)`.
The machine runs exactly 2 steps (one period) and returns to `q=0, h=0` with the tape unchanged.
The tape is decoded back to bytes `r`, and `r` is Gödel-encoded in base 257 and decoded again.
All of these are asserts, so if any fails, Python exits non-zero.

On success it prints `COSMIC_LOVE` and one JSON line, for example:
`{"statement":"solution(s)=s","s_hex":"...","result_hex":"...","godel_hex":"0x...","validated":true}`

Formal scope: the "solution" is the identity map, verified for this input. It is not a general problem solver.

## Run
```bash
bash cosmic_love_identity_solver_tm.sh "COSMIC_LOVE"
printf 'hello' | bash cosmic_love_identity_solver_tm.sh --stdin
nohup setsid bash cosmic_love_identity_solver_daemon.sh >/dev/null 2>&1 &   # resident loop, 1s
tail -f cosmic_love_identity_daemon.log
touch run/KILL                                                               # stop
```
