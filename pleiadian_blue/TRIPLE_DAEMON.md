# Triple-kernel heartbeat integration

The Pleiadian Blue daemon can now **optionally** run a finite three-way
semantic check against HSI-ST/1, HSI Original-XY and HSI-UVCM reference
transition implementations. This does not run the full original scripts or
prove bytewise equivalence of checkpoint formats.

From repository root:

```bash
python3 -m pleiadian_blue.daemon --db ./state.sqlite3 --status ./status.json --interval 1 --max-ticks 3 --triple-every 1 --triple-p 1829 --triple-bits 1 --triple-steps 8
```

Use `--max-ticks 0` only on an explicitly chosen always-on host. The
cross-kernel test is disabled by default (`--triple-every 0`). To reduce
CPU consumption, set `--triple-every 60` or `3600` rather than running
the finite simulation every second. The heartbeat is a local operation; it
does not fetch the web or call AI models. Missing observer data remains
UNKNOWN and is not inferred from a passing cross-kernel test.

`triple_kernel.status=FINITE_VERIFIED` means only that one bounded case
matched at the recorded time. A failed check records FAILED, rather than
silently treating it as success. The cached result can be older than the
heartbeat timestamp; read `triple_kernel.checked_at` to distinguish.

GitHub-hosted Actions verifies three real one-second ticks; it is not
a continuously resident daemon. Persistent 24/7 running requires a host
and durable storage. No trading or paid services are activated.
