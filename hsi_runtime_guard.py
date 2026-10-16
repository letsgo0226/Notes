#!/usr/bin/env python3
"""Supervise one Railway process with bounded, local runtime health probes."""
import argparse
from collections import deque
import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import wave
from hsi_cosmic_quantum import certificate as quantum_certificate


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def check_notes(health, evidence, audio, expected_revision):
    require(health.get('ok') is True and health.get('selftest') == 'PASSED', 'notes_unhealthy')
    require(health.get('role') == 'MUSIC', 'unexpected_service_role')
    revision = health.get('notes', {}).get('release_commit')
    require(not expected_revision or revision == expected_revision, 'release_mismatch')
    require(evidence.get('notes', {}).get('release_commit') == revision, 'evidence_release_mismatch')
    core = evidence.get('result', {}).get('quantum', {})
    require(core.get('protocol') == 'HSI-COSMIC-QUANTUM-SELF-CLOSURE/QTM-1.0' and
            all(core.get(k) is True for k in ('transition_verified', 'norm_preserved', 'U2_identity')),
            'quantum_selftest_missing')
    native = evidence.get('result', {}).get('native', {})
    require(native.get('status') == 'LOCAL_AUDIO_VERIFIED', 'native_validation_missing')
    require(hashlib.sha256(audio).hexdigest() == native.get('audio_sha256'), 'preview_hash_mismatch')
    with wave.open(io.BytesIO(audio)) as wav:
        require(wav.getnframes() > 0 and wav.getsampwidth() == 2, 'invalid_preview_audio')
        require(len(wav.readframes(wav.getnframes())) > 0, 'empty_preview_audio')
    require(native.get('metrics', {}).get('rms', 0) > 0, 'silent_preview')
    quantum = quantum_certificate()
    return {'healthy': True, 'release_commit': revision, 'audio_verified': True,
            'quantum_verified': True, 'core_protocol': quantum['protocol']}


def check_daemon(state, expected_revision, generation, now, max_age):
    stamp = datetime.datetime.fromisoformat(state['timestamp'].replace('Z', '+00:00')).timestamp()
    require(0 <= now - stamp <= max_age, 'stale_daemon_cycle')
    require(state.get('runtime_generation') == generation, 'previous_process_state')
    require(not expected_revision or state.get('release_commit') == expected_revision, 'release_mismatch')
    require(all(state.get(k) is True for k in ('core_ok', 'controller_ok', 'daemon_healthy')), 'daemon_unhealthy')
    require(state.get('errors') == 0, 'daemon_stage_errors')
    return {'healthy': True, 'release_commit': state.get('release_commit'),
            'cycle': state.get('cycle'), 'cycle_age_sec': round(now - stamp, 1)}


class Budget:
    def __init__(self, maximum=3, window=3600):
        self.maximum, self.window, self.events = maximum, window, deque()

    def take(self, now):
        while self.events and self.events[0] <= now - self.window:
            self.events.popleft()
        if len(self.events) >= self.maximum:
            return False
        self.events.append(now)
        return True


class Guard:
    def __init__(self, kind, command, interval=60, startup=180, failures=3, max_age=180):
        self.kind, self.command = kind, command
        self.interval, self.startup = interval, startup
        self.failures, self.max_age = failures, max_age
        self.port = int(os.environ.get('PORT', '8080'))
        self.revision = os.environ.get('RAILWAY_GIT_COMMIT_SHA', '')
        self.state_path = Path(os.environ.get('STATUS_DIR', '/tmp/status')) / 'LATEST_DAEMON_STATE.json'
        self.stop = threading.Event()
        self.child = None
        self.generation = ''
        self.budget = Budget()
        self.started = 0

    def read(self, path, limit):
        # Only the child process on loopback is queried; never follow redirects.
        request = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect).open(request, timeout=10) as response:
            body = response.read(limit + 1)
            require(len(body) <= limit, 'probe_response_too_large')
            return body

    def probe(self):
        try:
            require(self.child is not None and self.child.poll() is None, 'child_not_running')
            if self.kind == 'notes':
                return check_notes(json.loads(self.read('/health', 65536)),
                                   json.loads(self.read('/selftest', 262144)),
                                   self.read('/preview.wav', 2 * 1024 * 1024), self.revision)
            return check_daemon(json.loads(self.state_path.read_text()), self.revision,
                                self.generation, time.time(), self.max_age)
        except (OSError, ValueError, KeyError, TypeError, wave.Error) as exc:
            # Do not log response bodies, environment values, or credentials.
            return {'healthy': False, 'reason': type(exc).__name__}

    def log(self, event, **fields):
        print(json.dumps({'event': event, 'kind': self.kind, 'release_commit': self.revision, **fields}), flush=True)

    def launch(self):
        self.generation = uuid.uuid4().hex
        self.started = time.monotonic()
        self.child = subprocess.Popen(self.command, stdin=subprocess.DEVNULL,
                                      env={**os.environ, 'RUNTIME_GUARD_GENERATION': self.generation},
                                      start_new_session=True)
        self.log('RUNTIME_GUARD_START', child_pid=self.child.pid)

    def terminate(self):
        if self.child is None:
            return
        # Kill the process group even when the direct child already exited.
        try:
            os.killpg(self.child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.child.wait(timeout=5)

    def serve_daemon_health(self):
        guard = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/health':
                    self.send_error(404)
                    return
                result = guard.probe()
                body = json.dumps({'protocol': 'RAILWAY-RUNTIME-GUARD/1.0', **result}).encode()
                self.send_response(200 if result['healthy'] else 503)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('0.0.0.0', self.port), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server

    def run(self):
        server = None
        bad = 0
        try:
            self.launch()
            if self.kind == 'daemon':
                server = self.serve_daemon_health()
            while not self.stop.is_set():
                result = self.probe()
                self.log('RUNTIME_GUARD_PROBE', **result)
                exited = self.child.poll() is not None
                warming = time.monotonic() - self.started < self.startup
                bad = 0 if result['healthy'] or (warming and not exited) else bad + 1
                if exited or bad >= self.failures:
                    if not self.budget.take(time.monotonic()):
                        self.log('RUNTIME_GUARD_EXHAUSTED', restarts_in_window=3)
                        return 1
                    self.log('RUNTIME_GUARD_RESTART', consecutive_failures=bad)
                    self.terminate()
                    if self.stop.wait(10):
                        break
                    self.launch()
                    bad = 0
                self.stop.wait(self.interval)
            return 0
        finally:
            self.terminate()
            if server:
                server.shutdown()
                server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['notes', 'daemon'], required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    parser.error('child command is required') if not command else None
    guard = Guard(args.kind, command)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: guard.stop.set())
    return guard.run()


if __name__ == '__main__':
    sys.exit(main())
