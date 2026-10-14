# HSI Cosmic Self-Closure TM (non-halting, v42)

The same 2-state machine as `../COSMIC_LOVE_Oscillator_TM`, decoded from `p = 55067263`
(`v=10493, c=10492, k=2, B=12`).

What the script checks, as asserts:
1. All four transitions match `(0,0)→(1,0,R)`, `(0,1)→(1,1,R)`, `(1,0)→(0,0,L)`, `(1,1)→(0,1,L)`.
2. From a blank tape, two steps return to `q=0, h=0`, blank tape (a 2-step cycle).

Then it prints one JSON line (saved in `expected.json`). With `--run` it keeps stepping forever.

`halt_unreachable: true` holds because the table only has states 0 and 1, every `(state, symbol)` is defined,
and none of them leads to a halt state. `two_step_cycle` is printed as a literal, but it is only reached after assert 2 passes.
Scope, as the program says: this one specified two-state TM only.

Note: `--run` is a tight loop with no sleep, so it uses a full CPU core. The daemon only runs it in 2-second bursts.

## Run
```bash
bash hsi_cosmic_self_closure_tm.sh            # proof line
bash hsi_cosmic_self_closure_tm.sh --run      # runs forever
nohup setsid bash hsi_cosmic_self_closure_daemon.sh >/dev/null 2>&1 &   # resident loop, 1s
touch run/KILL                                # stop
```
