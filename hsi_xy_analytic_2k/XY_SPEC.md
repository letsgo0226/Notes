# HSI–Cosmic Love / XY Analytic UTM, proof status and scope

## Two mathematical axes

- X is a Gödel code for a finite candidate: (old TM transition code, current configuration, requested new rule/step).
- Y is the reversible Gödel code of the **actually accepted** successor configuration.
- The One-Liner's `x`, `y` fields are emitted as decimal strings. Both use the same reversible base-257 encoding with a starting digit 1.
- The executed step/rule checks are those of `core_readable.py`; see the independent `verify_replay.py`.

The **old** HSI UTM 1.0 is included unchanged as `HSI_UTM_original.sh`. The One-Liner interpreter is a different, narrower machine that adds a provably conservative extension operation for a finite class of TM rules, not an arbitrary self-improving solver.

## Entire interpolation theorem (not yet evaluated by the One-Liner)

Let n range over *all* nonnegative integers. Decode n as an input candidate, handling ill-formed inputs with a fixed default, and let Phi(n) be the Gödel code of the successor configuration selected by the total, finite-step verified evolution relation. Define b_n = Phi(n)/(1+Phi(n)), so 0 <= b_n < 1. Then

    Y(z) = sum_{n>=0} b_n exp(-(z-n)^2) sinc(pi(z-n))
    sinc(w) = sin(w)/w; sinc(0)=1.

Each term is entire, and the Gaussian damping produces uniform convergence on every compact subset of C for bounded b_n, so Y is entire. At any integer m, all the terms except n=m vanish, yielding Y(m)=b_m. The mapping is injective in the code Phi(m) at integer input points, with Phi(m)=Y(m)/(1-Y(m)) in exact arithmetic. This is **analytic interpolation of an existing computable graph**, not an algorithm that solves semantic questions that Phi does not decide.

For any prescribed sequence on the nonnegative integers, continuation is not unique just from those isolated values. The Gaussian-cardinal formula chooses a canonical *rule-dependent* interpolation; it should not be conflated with analytic continuation of the Riemann zeta function from Re(s)>1.

## Dirichlet compatibility

The microkernel returns three nonnegative integer residuals r0,r1,r2 and exactly calculates

    D(0)=r0+r1+r2,
    30 D(1)=15r0+10r1+6r2.

D(s)=r0*2**(-s)+r1*3**(-s)+r2*5**(-s) is an entire Dirichlet polynomial. Since each residual is nonnegative, D(0)=0 iff all rj=0. Analytic continuation of D is immediate (D is already entire). The **evolution acceptance rule is still a finite exact check**, not complex-analytic evaluation: an incompatible proposal is not accepted. An incompatible proposal can be preserved as an event in external persisted history.

An optional analytic compatibility interpretation is: require holomorphic F on a connected domain, F|_D = D_x, F|_U = 0 for two nonempty open subsets D and U. By the identity theorem this has a solution iff D_x identically zero, equivalent to vanishing residuals. This is a re-expression of specified constraints, not a universal security result.

## Semantic scope and size

- Conservative extension embeds every old state into a new distinct state, preserves every old transition on its image, and may add extra states and new entry points. It need not increase Turing computability.
- `command.txt` and the shell wrapper are each strictly under 2048 UTF-8 bytes, using zlib/base85 packing. The expanded readable core is larger.
- In this version, the 2048-byte upper bound for rule input is measured on the **decimal numeral of the transition code**; it is not an upper bound on the size of the binary machine description, the history, output, or the simulated tape.
- No SHA or cryptographic digest is used. The reversible event history can be replayed, but malicious rewriting and recomputation of the entire history cannot be prevented by reversible encoding alone.
- No universal halting decider, automatic proof of all program behaviors, or global analytic continuation solver is claimed.