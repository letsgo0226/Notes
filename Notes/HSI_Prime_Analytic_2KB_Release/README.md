# HSI Plaintext Sub-2KB + Prime Formula + Analytic Continuation

Two fully self-contained, **plain-text** shell commands, each a **single physical line**:

| Entry | Bytes | Shell |
|---|---:|---|
| `HSI_OriginalXY_POSIX_2KB_OneLiner.sh` | **2043** | POSIX sh + `printf`, recommended for macOS and iSH |
| `HSI_OriginalXY_Plaintext_2KB_OneLiner.sh` | **2027** | Bash (`$'...\n'`) |

The corresponding **1983-byte readable Python core** is `HSI_OriginalXY_Plaintext_Core.py`. All three contain no compressed Base85/zlib payload or `exec` code. The complete decompressed reference is `OriginalXY_reference.py` (3072 bytes).

## Run

```sh
HSI_STATE=demo.state HSI_LIMIT=12 HSI_SLEEP=0 sh HSI_OriginalXY_POSIX_2KB_OneLiner.sh
```

Resume using the same checkpoint file:

```sh
HSI_STATE=demo.state HSI_LIMIT=12 HSI_SLEEP=0 sh HSI_OriginalXY_POSIX_2KB_OneLiner.sh
```

For step-by-step output add `HSI_TRACE=1`. To test rejection, set `HSI_CAND='[999,0,[]]'`. With `HSI_LIMIT=0`, the outer enumeration continues indefinitely; interrupt with Ctrl+C. For safety, start with a limit and a new state file.

## Audit

```sh
python3 verify_prime_analytic.py
```

This checks the one-line size, source constraints, finite reference replay, checkpoint/resume behavior, prime encoding and Wilson examples, E257 recovery, exact rational Lagrange interpolation and nonuniqueness. See `verification_certificate.json` and `HSI_PRIME_ANALYTIC_PLAINTEXT_2KB_BILINGUAL_SPEC.txt`.

**Boundaries:** Finite regression equivalence is **not** a proof of all-input equivalence. Compared with the 3072-byte source, some checkpoint/input guards and filesystem durability guarantees are omitted to meet the strict budget. The arithmetic/analytic audit is a **separate file** and not included inside the 2KB byte count. Polynomial interpolation of discrete samples does not decide halting or establish unique analytic continuation without a chosen holomorphic germ on an open set. Nothing here deploys external services or authorizes live trading.
