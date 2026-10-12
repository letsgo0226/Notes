# HSI-UVCM v1: bounded virtual correspondence

A finite binary-tape Turing machine emulator in Python standard library. The explicit input is a transition table and a finite initial tape; the output is a serialized state, a status, and a SHA-256-checked atomic checkpoint. The E257-like code uses canonical sorted-key JSON, and **is not byte-for-byte equivalent to the earlier HSI Original-XY unsorted serialization**.

Run:

```bash
python3 -m unittest discover -s pleiadian_blue -p test_uvcm.py -v
python3 pleiadian_blue/uvcm.py --spec pleiadian_blue/uvcm_example.json --checkpoint /tmp/uvcm.json --steps 1
python3 pleiadian_blue/uvcm.py --checkpoint /tmp/uvcm.json --resume --steps 1
```

A split run and a continuous run agree under the same deterministic transition semantics. A SHA-256 digest detects accidental corruption; it does not authenticate against a malicious actor who can edit both file and hash. Atomic rename reduces torn-file risk but is not a full crash-consistent database transaction on every filesystem. The finite residual score checks only local invariants, not arbitrary program correctness. The code does not solve the halting problem, bypass hardware resource limits, or continuously run without a host. There is no trading, paid service, remote execution, self-modification or AI call. This is a **prototype**, not a universal proof or the original HSI-ST/1 bit-packed format; future adapters require explicit semantic-equivalence tests.
