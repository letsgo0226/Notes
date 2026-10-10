# HSI–CL–XY/2K — UTM x-axis and analytic y-axis

A reproducible prototype linking finite UTM candidate descriptions to certified successor configurations, with reversible Gödel coordinates and an entire-interpolation theorem for their discrete graph.

## Contents

- `command.txt`: one-line `python3 -c` command, under 2048 bytes
- `hsi_cl_xy_2k.sh`: runnable shell wrapper, under 2048 bytes
- `core_readable.py`: equivalent unpacked Python source
- `HSI_UTM_original.sh`: preserved original 1907-byte HSI-UTM v1.0
- `verify_replay.py`: independent state and history checker
- `test_system.py`: 30 inherited conservative-extension tests
- `analytic_bridge.py`: demonstration of finite entire interpolation and Dirichlet residual
- `test_xy.py`: 7 additional x/y, Dirichlet, and size tests
- `XY_SPEC.md`: mathematical formulation and explicit limitations

## Example

In a new writable directory, use the full path to `hsi_cl_xy_2k.sh`:

```sh
HSI_PROGRAM=2 HSI_WORD=1 HSI_STATE=xy.state sh /path/to/hsi_cl_xy_2k.sh
HSI_STATE=xy.state HSI_CAND='[99,0,[]]' sh /path/to/hsi_cl_xy_2k.sh
python3 /path/to/verify_replay.py xy.state
```

The JSON keys `x` and `y` are reversible decimal-string Gödel coordinates, for candidate input and actual successor configuration respectively. `D0` is the residual sum; `D1_num` is 30 times its exact Dirichlet value at s=1. `accepted=0` leaves the computation state unchanged; an event is nevertheless added to history.

For a computer-readable entire interpolation toy example:

```sh
python3 /path/to/analytic_bridge.py
```

For checks:

```sh
cd /path/to/HSI_XY_ANALYTIC_2K
python3 -m unittest test_system test_xy -q
```

**Scope**: The compressed One-Liner is a fixed interpreter, not a <2048-byte unpacked source. It implements exact UTM transition and rule-conservative-extension checks for a chosen machine class, not arbitrary finite/infinite safety checking. The full analytic function is supplied by mathematical construction and demonstrated in finite approximation, not directly computed as an infinite function by the One-Liner. No SHA is used. See `XY_SPEC.md`.