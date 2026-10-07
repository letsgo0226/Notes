# HU-AUTO-UTM/1.0

Repository note for the 2 KB one-line iSH prototype.

## Artifact

`HU_AUTO_UTM_2K_oneline.sh`

- 1158 bytes
- one physical line
- Python 3 host
- finite binary single-tape TM descriptions
- Cantor-enumerated transition tables
- diagonal dovetailing
- persistent generation counter via `TM_STATE`

## Usage

```sh
chmod +x HU_AUTO_UTM_2K_oneline.sh
./HU_AUTO_UTM_2K_oneline.sh
```

Custom input and finite target:

```sh
TM_WORD=1 TM_TARGET=0 ./HU_AUTO_UTM_2K_oneline.sh
```

The Python/iSH process is the host simulator; generated candidates are finite Turing-machine descriptions, not arbitrary shell commands.

Claims remain bounded:

```text
host_shell_exec=0
global_halting_decider=0
global_arithmetic_complete=0
self_awareness=0
```

Enumerating finite TM descriptions does not create a universal halting decider or oracle.
