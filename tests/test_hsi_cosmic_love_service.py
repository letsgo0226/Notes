"""HTTP health-only contract; no Binance key, broker, or trading route."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from hsi_cosmic_love_heartbeat import _snapshot, _write
from hsi_cosmic_love_service import make_handler


class Worker:
    def __init__(self, alive=True):
        self.alive = alive

    def is_alive(self):
        return self.alive


class CosmicLoveServiceHealthTests(unittest.TestCase):
    def request(self, server, method="GET", path="/health"):
        host, port = server.server_address
        req = urllib.request.Request(
            "http://127.0.0.1:" + str(port) + path, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_live_worker_plus_fresh_checkpoint_is_required(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            _write(path, _snapshot(7, 0, "RUNNING", clock=lambda: 2000))
            worker = Worker()
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), make_handler(path, worker, clock=lambda: 2001)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                code, body = self.request(server)
                self.assertEqual(code, 200)
                self.assertTrue(body["healthy"])
                self.assertEqual(body["cycles_completed"], 7)
                self.assertEqual(body["broker_calls"], 0)
                self.assertFalse(body["live_trading_authorized"])
                self.assertEqual(body["read_only"], True)
                self.assertNotIn("pid", body)
                self.assertNotIn("tape", body)
                worker.alive = False
                code, body = self.request(server)
                self.assertEqual(code, 503)
                self.assertFalse(body["healthy"])
                worker.alive = True
                self.assertEqual(self.request(server, "GET", "/orders/submit")[0], 404)
                self.assertEqual(self.request(server, "POST", "/health")[0], 405)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_stale_or_invalid_checkpoint_returns_unhealthy(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            _write(path, _snapshot(2, 0, "RUNNING", clock=lambda: 2000))
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                make_handler(path, Worker(), clock=lambda: 2020)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                code, body = self.request(server)
                self.assertEqual(code, 503)
                self.assertFalse(body["healthy"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
