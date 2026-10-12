# Finite host-resource correspondence

Run `python3 -m pleiadian_blue.resource_correspondence --p 1829 --bits 1 --steps 8 --output resource.json` from the repository root.

The semantic SHA-256 is intended to remain equal across deterministic hosts
for the same inputs. Wall-clock nanoseconds, CPU nanoseconds, and peak
process resident set size are host-specific observations, and may vary between
runs. On Linux `ru_maxrss` is reported in KiB; on macOS it is bytes.
Peak RSS is a process lifetime maximum, not the incremental memory cost of
one simulation. The resulting JSON is a finite experimental record, not
a universal hardware-limit theorem or a zero-entropy claim.

The workflow executes only on PR or manual dispatch. It does not perform
24/7 measurements, trade, or provision a paid server.
