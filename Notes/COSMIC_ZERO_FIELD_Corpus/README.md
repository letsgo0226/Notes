# Corpus × COSMIC_LOVE mathematical zero field

Protocol: `HSI-COSMIC-ZERO-FIELD/1.0` · Corpus version: `1.9.3`

## Construction

The verified program `p=55067263` has `delta(q,a)=(1-q,a,1-2q)`.
On a blank tape its states and movement directions alternate every two steps.
The finite coefficient sequence is `a_n=(-1)^(n-1)`.

For a bounded number of terms N, construct

```text
D_N(s) = sum_{n=1..N} a_n * n^(-s)
z = 1/2 + i*gamma
P_Z(s) = ((s-z)*(s-conj(z)))/((2-z)*(2-conj(z)))
F(s) = A * D_N(s) * P_Z(s) / D_N(2)
E(s) = |F(s)|^2
```

Here the zeros at z and conjugate(z) are **inserted algebraically**, not discovered.
At `s=2`, `F(2)=A`; the finite checks verify normalization and nonnegative energies.
Default N=32, A=1, gamma=14.134725141734693. This gamma is a configurable
illustrative reference; no claim of Riemann Hypothesis proof is made.

## Connection to sound

Each finite Corpus render samples `E(1/2+i*t)` over a bounded interval
around gamma. The dimensionless normalized value becomes bounded
playback-rate, stereo-pan, and per-event gain corrections. These values
are embedded into `events.json` and the generated `song.hsicert`,
`correspondence.hsicert`, `corpus.lock.json` and `manifest.json`.

The existing TM event clock, open CC0/PDM corpus provenance, DSP,
rights-uncertainty disclosure, quality/correspondence checks and
non-AI rendering path remain in place.

## Configuration

* `HSI_ZERO_FIELD=1` enables the field (default).
* `HSI_ZERO_FIELD=0` disables only the field.
* `HSI_ZERO_FIELD_TERMS=32` bounds N to 8..128.
* `HSI_ZERO_FIELD_GAMMA=14.134725141734693` bounds gamma to 0.01..80.
* `HSI_ZERO_FIELD_AMPLITUDE=1` bounds A to 0.01..2.
* `HSI_COSMIC_LOVE_TM=0` disables both TM and dependent field without
  changing the native audio engine.

Test with `python3 -m unittest test_hsi_cosmic_zero_field.py`.
The bundle is hash-pinned via `hsi_bundle.lock.json`.

**Boundary:** This is a finite, deterministic, dimensionless mathematical
model for music control; it does not generate, measure or validate
physical vacuum/zero-point energy and is not a proof of any statement
about the zeros of the Riemann zeta function.
