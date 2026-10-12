#!/usr/bin/env python3
"""Finite 1-second Pleiadian Blue heartbeat; no AI, remote actions or trading."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import signal
import sqlite3
import time
from pathlib import Path

STOP = False
MAX_SOURCE_BYTES = 1024 * 1024
MAX_TERMS = 128


def load_source(path):
    """Read bounded local evidence; absence is explicitly UNKNOWN, never success."""
    if path is None or not path.is_file():
        return [0.0], "UNKNOWN_NO_SOURCE", None
    if path.stat().st_size > MAX_SOURCE_BYTES:
        return [0.0], "UNKNOWN_OVERSIZED_SOURCE", None
    try:
        raw = path.read_bytes()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("not an object")
        assessments = data.get("review", [])
        if not isinstance(assessments, list) or len(assessments) > MAX_TERMS:
            raise ValueError("invalid review")
        residuals = []
        for item in assessments:
            value = item["residual"]
            if isinstance(value, bool) or not isinstance(value, (float, int)):
                raise ValueError("non-numeric residual")
            value = float(value)
            if not math.isfinite(value) or value < 0 or value > 1000000:
                raise ValueError("out-of-bounds residual")
            residuals.append(value)
        if not residuals:
            return [0.0], "UNKNOWN_EMPTY_REVIEW", hashlib.sha256(raw).hexdigest()
        return residuals, "LOCAL_EVIDENCE_ONLY", hashlib.sha256(raw).hexdigest()
    except (ValueError, KeyError, TypeError, OSError, UnicodeError):
        return [0.0], "UNKNOWN_INVALID_SOURCE", None


def dirichlet(residuals, s=complex(2, 1)):
    """Finite diagnostic sum; NOT a Riemann zeta evaluation or RH proof."""
    return sum((v / (i ** s) for i, v in enumerate(residuals, start=1)), 0j)


def init_db(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=8)
    connection.execute("PRAGMA busy_timeout=8000")
    connection.execute("CREATE TABLE IF NOT EXISTS heartbeat ("
                       "id INTEGER PRIMARY KEY CHECK (id=1), "
                       "ticks INTEGER NOT NULL, observed_at TEXT, "
                       "source_status TEXT, source_sha256 TEXT, "
                       "score_real REAL, score_imag REAL)")
    connection.execute("INSERT OR IGNORE INTO heartbeat "
                       "(id,ticks,source_status) VALUES (1,0,'UNKNOWN_UNSTARTED')")
    connection.commit()
    return connection


def step(connection, source_path, triple=None):
    residuals, source_status, source_digest = load_source(source_path)
    score = dirichlet(residuals)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    with connection:
        connection.execute("UPDATE heartbeat SET ticks=ticks+1, observed_at=?, "
                           "source_status=?, source_sha256=?, score_real=?, "
                           "score_imag=? WHERE id=1",
                           (now, source_status, source_digest, score.real, score.imag))
        ticks = connection.execute("SELECT ticks FROM heartbeat WHERE id=1").fetchone()[0]
    result = {"protocol": "HSI-PLEIADIAN-BLUE-DAEMON/1.0", "ticks": ticks,
            "observed_at": now, "source_status": source_status,
            "source_sha256": source_digest, "dirichlet_real": score.real,
            "dirichlet_imag": score.imag, "online_fetches": 0,
            "model_calls": 0, "orders": 0, "autonomous_changes": 0}
    if triple is not None:
        result["triple_kernel"] = triple
    return result


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def serve(db_path, status_path, source_path, interval, max_ticks,
          reload_every=60, triple_every=0, triple_p=1829, triple_bits="1", triple_steps=8):
    global STOP
    if not (0 < interval <= 60):
        raise ValueError("interval must be in (0,60]")
    if max_ticks < 0 or max_ticks > 1000000:
        raise ValueError("max_ticks must be 0..1000000")
    if not (0 <= triple_every <= 86400):
        raise ValueError("triple_every must be 0..86400")
    if not (0 <= triple_p <= 100000 and 0 <= triple_steps <= 256):
        raise ValueError("triple parameters out of bounds")
    if len(triple_bits) > 128 or any(b not in "01" for b in triple_bits):
        raise ValueError("triple_bits must be binary and <=128 bits")
    if reload_every < 1 or reload_every > 86400:
        raise ValueError("reload_every must be 1..86400")
    # Only one instance may own this database. SQLite BEGIN EXCLUSIVE does not
    # survive a commit, so keep a small persistent owner lock via flock.
    import fcntl
    lockfile = db_path.with_name(db_path.name + ".lock")
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a+b") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Daemon is already running") from exc
        with init_db(db_path) as connection:
            start = time.monotonic()
            cached = None
            triple_receipt = None
            for index in range(max_ticks if max_ticks else 10**18):
                if STOP:
                    break
                # Preserve monotonic, roughly 1-second spacing; do not catch up
                # using huge bursts after a slow or suspended interval.
                deadline = start + index * interval
                delay = deadline - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                if STOP:
                    break
                if index % reload_every == 0 or cached is None:
                    cached = source_path if source_path and source_path.is_file() else None
                if triple_every and index % triple_every == 0:
                    from pleiadian_blue.cross_kernel import compare
                    try:
                        checked = compare(triple_p, triple_bits, triple_steps)
                        triple_receipt = {"status": "FINITE_VERIFIED", **checked,
                                          "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()}
                    except Exception as exc:
                        triple_receipt = {"status": "FAILED", "error_type": type(exc).__name__,
                                          "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()}
                receipt = step(connection, cached, triple_receipt if triple_every else None)
                receipt["interval_requested_seconds"] = interval
                atomic_json(status_path, receipt)
                print(json.dumps({"ticks": receipt["ticks"],
                                  "source_status": receipt["source_status"]}),
                      flush=True)
                if time.monotonic() > deadline + interval:
                    start = time.monotonic() - index * interval


def _stop(*unused):
    global STOP
    STOP = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("pleiadian-blue-state.sqlite3"))
    parser.add_argument("--status", type=Path, default=Path("pleiadian-blue-status.json"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--max-ticks", type=int, default=0,
                        help="0 = continuous until stopped")
    parser.add_argument("--reload-every", type=int, default=60)
    parser.add_argument("--triple-every", type=int, default=0,
                        help="0=disabled; otherwise verify finite triple semantics every N ticks")
    parser.add_argument("--triple-p", type=int, default=1829)
    parser.add_argument("--triple-bits", default="1")
    parser.add_argument("--triple-steps", type=int, default=8)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    serve(args.db, args.status, args.source, args.interval,
          args.max_ticks, args.reload_every, args.triple_every,
          args.triple_p, args.triple_bits, args.triple_steps)


if __name__ == "__main__":
    main()
