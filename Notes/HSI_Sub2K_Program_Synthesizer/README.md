# HSI Sub-2KB Program Synthesizer

This folder supplies the missing distinction between a program that is itself
small and a program that **generates a specified result** while remaining
strictly smaller than 2,048 bytes.

`hsi_sub2k_synth.py` performs a bounded search over explicit reconstruction
grammars (literal, periodic, constant, run-length, affine, and quadratic byte
sequences).  A candidate is accepted only after it is run with isolated Python
in a fresh temporary directory and its output is compared byte-for-byte with
the requested source.  The generated program requires only Python 3 and an
output-path argument; it does not read the original file or any network source.

By default no zlib or Base85 payload is considered.  Compression can be added
only by the explicit `--allow-compression` option and is labelled in the
certificate.  This prevents an ordinary compressed archive from being
presented as an OriginalXY or information-theoretic breakthrough.

## Generate and verify

```sh
python3 hsi_sub2k_synth.py input.bin \
  --out reconstruct.py \
  --certificate reconstruct.certificate.json
python3 reconstruct.py restored.bin
cmp input.bin restored.bin
wc -c reconstruct.py
```

On verified success the CLI exits 0 and emits
`VERIFIED_SUB_2KB_PROGRAM`.  If its finite grammar finds no exact program below
the limit, it exits 4, does not create the program, and emits
`NO_VERIFIED_SUB_2KB_PROGRAM`.  The latter is a bounded-search result, never a
proof that a shorter program is mathematically impossible.

## Independent finite suite

```sh
python3 verify_sub2k_synth.py
```

The verifier covers literal, large periodic, affine, quadratic and constant
successes plus an intentionally unresolved finite case.  It writes
`verification_certificate.json` only after every reconstruction has been
executed and compared exactly.

## Relation to HSI OriginalXY and Riemann feedback

Each successful program receives a reversible E257 coordinate.  Candidate
verification exposes the three nonnegative residuals used by the surrounding
HSI design: size violation, execution failure, and byte mismatch.  Acceptance
requires every residual to vanish; the certificate also records
`D0` and the exact numerator `30 D(1) = 15r0 + 10r1 + 6r2`.

This is a finite verified synthesis kernel suitable for a later feedback loop.
It is not a universal halting decider, a proof of the Riemann Hypothesis, a
global Kolmogorov-minimization algorithm, or a representation of every finite
file below 2 KiB.
