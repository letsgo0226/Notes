#!/usr/bin/env python3
"""POSIX-local, bounded-recovery COSMIC_LOVE heartbeat. NO trading/network.

Default is finite. --forever must be explicitly requested, and even then
the process stops on SIGINT, SIGTERM, or an operator-created stop file.
No Railway deployment, scheduler, Binance API, or external service calls.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import threading
import time

from hsi_cosmic_love import PROGRAM, MARKER, EXPECTED_TABLE, transition, verify

PROTOCOL = "HSI-COSMIC-LOVE-HEARTBEAT/1"
STATUSES = frozenset(("RUNNING", "STOPPED", "ERROR"))
MAX_STATE_BYTES = 16384


def _checksum(data):
    payload = {key: value for key, value in data.items() if key != "sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot(cycles, restarts, status, clock=time.time):
    record = {
        "protocol": PROTOCOL, "marker": MARKER, "program": PROGRAM,
        "status": status, "q": 0, "head": 0, "tape": {},
        "cycles_completed": cycles, "transitions_completed": cycles * 2,
        "recovery_attempts": restarts, "updated_at_ms": int(clock() * 1000),
        "pid": os.getpid(), "broker_calls": 0,
        "live_trading_authorized": False,
        "meaning": "two-step identity heartbeat only; not an AI or trading system",
    }
    record["sha256"] = _checksum(record)
    return record


def _validate(record):
    if not isinstance(record, dict) or record.get("protocol") != PROTOCOL:
        raise ValueError("invalid heartbeat protocol")
    digest = record.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or digest != _checksum(record):
        raise ValueError("heartbeat checkpoint hash mismatch")
    if (record.get("marker") != MARKER or type(record.get("program")) is not int
            or record["program"] != PROGRAM or record.get("status") not in STATUSES
            or record.get("q") != 0 or record.get("head") != 0
            or record.get("tape") != {}
            or record.get("live_trading_authorized") is not False
            or record.get("broker_calls") != 0):
        raise ValueError("invalid or unsafe heartbeat configuration")
    n = record.get("cycles_completed")
    t = record.get("transitions_completed")
    r = record.get("recovery_attempts")
    updated = record.get("updated_at_ms")
    pid = record.get("pid")
    if (any(type(x) is not int or x < 0 for x in (n, t, r, updated, pid))
            or t != 2 * n or updated <= 0 or pid <= 0):
        raise ValueError("inconsistent heartbeat checkpoint")
    return record


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("heartbeat checkpoint missing, linked or oversized")
    try:
        return _validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("unreadable heartbeat checkpoint") from exc


def _write(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("refuse to replace symlink checkpoint")
    descriptor, tmp = tempfile.mkstemp(prefix=".cosmic-heartbeat-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(record, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def _exclusive_lock(path):
    """Nonblocking advisory lock released even if this POSIX process crashes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    if lock_path.is_symlink():
        raise ValueError("refuse symlink lock path")
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_heartbeat(
    state_file, *, cycles=10, forever=False, interval=0.05,
    checkpoint_every=10, max_restarts=2, resume=False, stop_file=None,
    stepper=transition, sleeper=time.sleep, clock=time.time,
    stop_requested=lambda: False,
):
    """Commit only complete two-step identity cycles to durable state.

    Recover a bounded number of *transient in-process* step faults by
    rechecking the table and restarting from the known identity state.
    After an OS crash, an external supervisor must explicitly relaunch
    this command with --resume; no service is installed automatically.
    """
    if (type(cycles) is not int or cycles < 0 or cycles > 1000000
            or type(forever) is not bool or (forever and cycles != 10)
            or type(checkpoint_every) is not int or not 1 <= checkpoint_every <= 1000
            or type(max_restarts) is not int or not 0 <= max_restarts <= 5
            or type(interval) not in (int, float) or not 0 <= interval <= 5):
        raise ValueError("invalid bounded heartbeat settings")
    verify(PROGRAM)
    path = Path(state_file)
    if resume and path.exists():
        old = _read(path)
        if old["status"] == "ERROR":
            raise ValueError("cannot auto-resume an ERROR checkpoint")
        completed = old["cycles_completed"]
        restarts = old["recovery_attempts"]
    else:
        if not resume and path.exists():
            raise ValueError("checkpoint exists; use --resume or another state file")
        completed = restarts = 0
    _write(path, _snapshot(completed, restarts, "RUNNING", clock))
    done_this_run = 0
    stop_path = Path(stop_file) if stop_file else None
    failed = False
    while forever or done_this_run < cycles:
        if stop_requested() or (stop_path is not None and stop_path.exists()):
            break
        try:
            start = ((0, 0), {})
            one = stepper(*start, EXPECTED_TABLE)
            sleeper(interval)
            two = stepper(*one, EXPECTED_TABLE)
            sleeper(interval)
            if two != start:
                raise ValueError("COSMIC_LOVE two-step invariant violation")
            completed += 1
            done_this_run += 1
            if done_this_run % checkpoint_every == 0:
                _write(path, _snapshot(completed, restarts, "RUNNING", clock))
        except Exception:
            restarts += 1
            if restarts > max_restarts:
                failed = True
                break
            verify(PROGRAM)
            # An internal restart never changes state or replays a broker action.
            sleeper(min(0.05 * restarts, 0.25))
    final = _snapshot(completed, restarts, "ERROR" if failed else "STOPPED", clock)
    _write(path, final)
    return final


def check_heartbeat(path, *, max_age=10.0, clock=time.time):
    """A freshness check, NOT an OS process-liveness or broker health claim."""
    if type(max_age) not in (int, float) or not 0 < max_age <= 3600:
        raise ValueError("invalid freshness window")
    try:
        record = _read(path)
    except (OSError, ValueError):
        return {"protocol": PROTOCOL, "healthy": False,
                "reason": "INVALID_OR_MISSING_CHECKPOINT",
                "live_trading_authorized": False}
    age = clock() - record["updated_at_ms"] / 1000
    fresh = -2 <= age <= max_age
    healthy = record["status"] == "RUNNING" and fresh
    return {
        "protocol": PROTOCOL, "healthy": healthy,
        "reason": "FRESH_HEARTBEAT_ONLY_NOT_PROCESS_PROOF" if healthy
                  else ("STALE_OR_FUTURE_CHECKPOINT" if not fresh else "NOT_RUNNING"),
        "status": record["status"],
        "cycles_completed": record["cycles_completed"],
        "transitions_completed": record["transitions_completed"],
        "recovery_attempts": record["recovery_attempts"],
        "age_seconds": round(age, 3),
        "broker_calls": 0, "live_trading_authorized": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="operation", required=True)
    run = sub.add_parser("run", help="finite by default; --forever is opt-in")
    run.add_argument("--state-file", type=Path, required=True)
    modes = run.add_mutually_exclusive_group()
    modes.add_argument("--cycles", type=int, default=10)
    modes.add_argument("--forever", action="store_true")
    run.add_argument("--interval", type=float, default=0.05)
    run.add_argument("--checkpoint-every", type=int, default=10)
    run.add_argument("--max-restarts", type=int, default=2)
    run.add_argument("--resume", action="store_true")
    run.add_argument("--stop-file", type=Path)
    check = sub.add_parser("check", help="check local snapshot freshness")
    check.add_argument("--state-file", type=Path, required=True)
    check.add_argument("--max-age", type=float, default=10)
    a = p.parse_args()
    if a.operation == "check":
        try:
            report = check_heartbeat(a.state_file, max_age=a.max_age)
        except ValueError as exc:
            p.exit(2, "INVALID_CHECK: " + str(exc) + "\n")
        print(json.dumps(report, sort_keys=True), flush=True)
        return 0 if report["healthy"] else 1
    stop = threading.Event()
    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, lambda *_: stop.set())
    try:
        with _exclusive_lock(a.state_file):
            print(MARKER, flush=True)
            report = run_heartbeat(
                a.state_file, cycles=a.cycles, forever=a.forever,
                interval=a.interval, checkpoint_every=a.checkpoint_every,
                max_restarts=a.max_restarts, resume=a.resume,
                stop_file=a.stop_file, stop_requested=stop.is_set,
            )
            print(json.dumps(report, sort_keys=True), flush=True)
            return 2 if report["status"] == "ERROR" else 0
    except (ValueError, OSError, BlockingIOError) as exc:
        p.exit(2, "HEARTBEAT_BLOCKED: " + type(exc).__name__ + "\n")
    finally:
        for signum, old in previous.items():
            signal.signal(signum, old)


if __name__ == "__main__":
    raise SystemExit(main())
