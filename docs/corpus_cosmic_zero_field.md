# COSMIC_LOVE zero-field integration in Corpus 1.9.3

This is a **dimensionless mathematical audio controller**, not physical zero-point
energy. It implements the finite field defined in the October 13, 2026 Notes
research explanation (`COSMIC-LOVE-ZERO-FIELD/1`).

## Exact mapping

The verified `p=55067263` Turing machine has
`delta(q,a)=(1-q,a,1-2q)` and `q_j=j mod 2` on a blank initial tape.
The field uses one of these finite Dirichlet bases:

- Default **prime spectrum**:
  `D_N(s)=sum_{j=0}^{N-1}(1+q_j)*p_j**(-s)`, with `p_j` the j-th prime.
- Optional **alternating**:
  `D_N(s)=sum_{n=1}^N (-1)**(n-1)*n**(-s)`.

For specified conjugate zeros `z_j=u_j+i*v_j` define
`P_Z(s)=product_j((s-z_j)*(s-conj(z_j))/(1+|z_j|**2))`,
`F(s)=A*D_N(s)*P_Z(s)/D_N(2)`, and `E(s)=|F(s)|**2`.

Defaults: `N=32`, `A=1`, basis `prime`, prescribed zeros
`0.5±8i`, `0.5±14i`, and `0.5±21i`.
The zeros are **inserted algebraically**. Additional base-function zeros may
exist. Neither a proof of the Riemann Hypothesis nor physical vacuum energy
can be inferred from the generated mathematical field.

## Bounded audio application

Corpus samples `E(0.5+i*t)` at one point per render event, normalizes
the finite batch to a unit interval, and applies bounded adjustments to
playback rate (±0.018), stereo pan (±0.075), and gain (0.94..1.06).
Per-event values appear in `events.json`; the field certificate,
settings, checks and control UID are included in `song.hsicert`,
`correspondence.hsicert`, `corpus.lock.json`, and `manifest.json`.

The existing CC0/PDM sources, metadata uncertainty, rights review,
non-AI DSP, TM clock, and correspondence verification are not removed.
New module and renderer bytes are pinned in `hsi_bundle.lock.json`.

## Environment switches

- `HSI_ZERO_FIELD=1` (default); `0` disables just this field.
- `HSI_ZERO_FIELD_BASIS=prime` (default), or `alternating`.
- `HSI_ZERO_FIELD_TERMS=32` (allowed: 8,16,32,64,128).
- `HSI_ZERO_FIELD_AMPLITUDE=1` (allowed: 0.1..5).
- `HSI_ZERO_FIELD_ZEROS=0.5:8,0.5:14,0.5:21` (1..8 pairs,
  real part -3..3, imaginary part 0..60).
- `HSI_COSMIC_LOVE_TM=0` also disables the dependent field.

Run `python3 -m unittest discover -s tests -p 'test_hsi_cosmic_zero_field.py'`
for mathematical unit checks and `hsi_open_corpus` workflow for offline
mocked WAV integration and deterministic bundle smoke tests.

The independent site referenced by the original mathematical document remains
a separately administered interactive visualization; deploying this Corpus
module does not change that site's access permissions, nor does it activate
Trader_42 or any other financial execution capability.
