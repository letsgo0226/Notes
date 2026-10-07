# HU-AUTO-UTM-RH-ATGC-Safe/1.0

This note archives a 2 KB one-line prototype that adds a Riemann-critical **design invariant** to the existing HU-AUTO-UTM search model.

## Core rule

For each finite candidate TM descriptor, the canonical descriptor string is reversibly encoded into an ATGC word. Its GC count is

[
k=GC(w).
]

A fixed system constant `K` defines the admissible critical layer. The design coordinate is represented exactly by

[
sigma=rac{k}{2K}.
]

Therefore

[
sigma=rac12 iff k=K.
]

The implementation uses the exact integer test `gc == K`; it does not use floating-point logarithms.

Equivalently, for an arbitrary base (B>1),

[
rac{log(B^{gc})}{log(B^{2K})}=rac12
iff gc=K.
]

## Coherence gate

A candidate is committed to the accepted set only when:

1. its finite TM simulation halts at the current dovetailed budget,
2. its finite output matches the requested target, and
3. its ATGC GC count equals the fixed critical constant `K`.

Candidates that satisfy the computational target but violate the GC invariant are counted as `rejected_noncritical`.

This is an engineering / formal-system coherence invariant:

[
delta(mathscr S_K)subseteqmathscr S_K,
qquad
mathscr S_K={X:GC(w_X)=K}.
]

It is **not** a proof of the Riemann hypothesis, and the script does not test whether any encoded complex number is a zeta zero.

## Unique ATGC identity

The candidate descriptor is mapped byte-for-byte into four 2-bit ATGC symbols per byte. Hence the ATGC word is reversible. The script also emits a sentinel base-4 integer `uid`:

[
u_0=1,qquad u_{j+1}=4u_j+d(w_j),
]

with (d(A)=0,d(T)=1,d(G)=2,d(C)=3). This preserves the full ATGC identity; the GC count is only the safety coordinate.

## Usage

```sh
chmod +x HU_AUTO_UTM_RH_ATGC_SAFE_2K_oneline.sh
./HU_AUTO_UTM_RH_ATGC_SAFE_2K_oneline.sh
```

Defaults:

```text
TM_WORD=1
TM_TARGET=0
TM_GC=15
TM_STATE=rhgc.state
TM_SLEEP=0.2
```

Example:

```sh
TM_WORD=1 TM_TARGET=0 TM_GC=15 ./HU_AUTO_UTM_RH_ATGC_SAFE_2K_oneline.sh
```

With those defaults, the early finite search reaches an accepted example at generation 3 with descriptor `2:1:1:2`, whose reversible ATGC code has `GC=15`.

## Explicit limits

The output preserves:

```text
rh_proved=0
zeta_zero_test=0
host_shell_exec=0
global_halting_decider=0
self_awareness=0
```

"Riemann-critical" here means the system adopts the numerical geometry of the critical coordinate (1/2) as a design invariant. It does not establish that all nontrivial zeros of the Riemann zeta function lie on the critical line.
