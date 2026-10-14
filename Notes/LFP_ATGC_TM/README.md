# LFP ATGC TM

A one-liner (1073 bytes) that finds the **least fixed point** of a monotone map `S` on 4-bit strings by iterating from `0000`:

`0000 → 1000 → 1100 → 1110 → 1111 → 1111`

`S` is monotone (if `a ⊆ b` then `S(a) ⊆ S(b)`), and `1111` is its only fixed point among all 16 values.
Each step `(a, S(a))` is written as 4 DNA letters with `00→A, 01→T, 10→G, 11→C`:
`TAAA CTAA CCTA CCCT CCCC`. Decoding each word gives back the pair (`REV:true`), and G+C is exactly 1/2.

Output is one deterministic JSON line, saved in `expected.json`.

## What is computed vs. stated
- Computed: `CHAIN`, `ATGC`, `CODE`, `FIX`, `REV`, `GC`, `H_BINARY`.
- Fixed constants in the output, not computed by the script: `TM` (a 2-state table), `CORE`/`HEX` (`D98E`), `UNIQUE_LFP`, `LENGTH_MIN`, `H_SOLUTION`.
  (`UNIQUE_LFP=1` does hold for this `S`: checking all 16 inputs, only `1111` is fixed.)

Scope, as the program says: a finite monotone prototype, not a total solver.

## Run
```bash
bash lfp_atgc_tm.sh
nohup setsid bash lfp_atgc_tm_daemon.sh >/dev/null 2>&1 &   # resident loop, 1s, compares with expected.json
touch run/KILL                                              # stop
```
