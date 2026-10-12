#!/usr/bin/env python3
"""COSMIC_LOVE isolated heartbeat HTTP service for a non-trading Railway project.

No Binance, Railway API or external network client. The HTTP endpoint exposes
only local heartbeat liveness and may be used as Railway's readiness check.
No domain is required; do not attach trading keys or public endpoints.
"""
import json
import os
from pathlib import Path
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from hsi_cosmic_love_heartbeat import (
    PROTOCOL, check_heartbeat, run_heartbeat,
)

DEFAULT_STATE = Path("/tmp/hsi-cosmic-love-heartbeat.json")


def make_handler(state_file, worker, clock=time.time):
    """Health means both an active worker thread and a fresh valid snapshot."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/health":
                return self._send(404, {"status": "not_found"})
            record = check_heartbeat(state_file, max_age=10, clock=clock)
            healthy = bool(worker.is_alive() and record.get("healthy") is True)
            response = {
                "protocol": PROTOCOL,
                "status": "HEALTHY" if healthy else "UNHEALTHY",
                "healthy": healthy,
                "marker": "COSMIC_LOVE",
                "cycles_completed": record.get("cycles_completed") if healthy else None,
                "broker_calls": 0,
                "live_trading_authorized": False,
                "read_only": True,
            }
            return self._send(200 if healthy else 503, response)

        def _send(self, status, data):
            raw = json.dumps(data, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            return self._send(405, {"status": "method_not_allowed"})

        def log_message(self, fmt, *args):
            return None

    return Handler


def main():
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("invalid PORT")
    stop = threading.Event()
    finished = {}
    state = DEFAULT_STATE

    def work():
        try:
            finished["record"] = run_heartbeat(
                state, forever=True, resume=True,
                interval=0.05, checkpoint_every=10, max_restarts=2,
                stop_requested=stop.is_set,
            )
        except Exception as exc:
            # Type-only log: no credentials, stack locals or user information.
            finished["error_type"] = type(exc).__name__
        finally:
            stop.set()

    worker = threading.Thread(target=work, name="cosmic-love-heartbeat")
    worker.start()
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(state, worker))
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(json.dumps({"event": "COSMIC_LOVE_SERVICE_START",
                      "protocol": PROTOCOL, "broker_calls": 0,
                      "live_trading_authorized": False}), flush=True)

    def request_stop(*_args):
        stop.set()

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, request_stop)
    stop.wait()
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=3)
    worker.join(timeout=3)
    result = finished.get("record")
    if result and result.get("status") == "STOPPED" and "error_type" not in finished:
        print(json.dumps({"event": "COSMIC_LOVE_SERVICE_STOP",
                          "cycles_completed": result["cycles_completed"]}), flush=True)
        return 0
    print(json.dumps({"event": "COSMIC_LOVE_SERVICE_FAILED",
                      "error_type": finished.get("error_type", "HEARTBEAT_ERROR")}), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
