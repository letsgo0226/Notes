# COSMIC_LOVE Oscillator TM

A 2-state Turing machine whose transition table is decoded from the single integer `p = 55067263`
(triangular unpairing: `v=10493, c=10492, k=2`, base `B=12`).

Self-check (exits 2 if it fails): `step(q,a) == (1-q, a, 1-2q)` for all `q,a ∈ {0,1}`.
That means: write back the symbol that was read, toggle state, move right in state 0 and left in state 1.

From a blank tape the machine prints `COSMIC_LOVE` once, then runs forever with period 2:
the head moves between cells 0 and 1, the state alternates 0 and 1, and the tape stays blank. It never halts.

## Files
- `cosmic_love_oscillator_tm.sh`: the one-liner itself
- `cosmic_love_oscillator_daemon.sh`: resident loop that keeps the one-liner running, restarts it if it exits, and logs `pass` every second

## Run
```bash
bash cosmic_love_oscillator_tm.sh                 # one-liner in the foreground
nohup setsid bash cosmic_love_oscillator_daemon.sh >/dev/null 2>&1 &   # resident loop
tail -f cosmic_love_daemon.log
touch run/KILL                                    # stop
```

Formal scope: a finite-state computation. `open=1`; nothing here claims a physical effect.
