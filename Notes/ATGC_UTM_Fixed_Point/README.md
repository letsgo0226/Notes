# ATGC UTM Fixed Point

A 1000-byte one-liner that maps any file to a DNA-style strand and back: each bit becomes two letters, `0 → AG` and `1 → TC`.
So every byte becomes 16 letters, and G+C is always exactly half the strand.

With no `MODE` it encodes **its own source** (`$0`) and prints a proof line:
`{"P":"ATGC_UTM_FIXED_POINT/2KB",...,"BYTES":1000,"ATGC":16000,"GC":"1/2","REV":true,"SOLUTION_EQ_S":true,...}`

| MODE | input | output |
|---|---|---|
| `proof` (default) | own source, or `SOURCE=file` | JSON proof line |
| `encode` | own source, or `SOURCE=file` | ATGC strand |
| `decode` | strand on stdin | original bytes |
| `run` | strand on stdin | decodes it and **executes it as Python** |

Any strand that is not made only of `AG`/`TC` pairs in whole bytes fails an assert.

**Warning:** `MODE=run` executes whatever Python the strand decodes to, with your permissions. Only run strands you made yourself or trust.

## Run
```bash
bash atgc_utm_fixed_point.sh                                         # proof
MODE=encode bash atgc_utm_fixed_point.sh | MODE=decode bash atgc_utm_fixed_point.sh | cmp - atgc_utm_fixed_point.sh
printf 'print(42)' > p.py; MODE=encode SOURCE=p.py bash atgc_utm_fixed_point.sh | MODE=run bash atgc_utm_fixed_point.sh
nohup setsid bash atgc_utm_fixed_point_daemon.sh >/dev/null 2>&1 &   # resident loop, 1s
touch run/KILL                                                       # stop
```

Formal scope: "universal" here means it hands decoded source to the Python interpreter, which is itself universal.
`SOLUTION_EQ_S` checks that encode(decode(w)) = w. It does not solve arbitrary problems.
