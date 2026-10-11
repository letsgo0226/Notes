#!/usr/bin/env python3
"""Notes-bound HTTP runtime for Music and the three finite invariant gates."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import runpy
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from hsi_notes_run import ROOT, verified_plan
from hsi_notes_validate import check_parameters, measure_wav, replay_utm, run_validation, verify_runtime

PROTOCOL = 'HSI-NOTES-SERVICE/1.0'


class ProviderError(Exception):
    def __init__(self, stage, status, message, request_id=None):
        self.detail = {'stage': stage, 'http_status': status, 'message': message, 'request_id': request_id}
        super().__init__(message)


def fal_json(url, key, data=None):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'queue.fal.run', 'queue.falrun.com'} or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError('provider returned an untrusted queue URL')
    request = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                     headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read(2 * 1024 * 1024))
    except urllib.error.HTTPError as exc:
        body = exc.read(2000).decode('utf-8', 'replace').replace(key, '[redacted]')
        raise ProviderError('provider', exc.code, body[:500]) from None
    except (urllib.error.URLError, TimeoutError):
        raise ProviderError('network', 503, 'Provider request could not complete; no automatic resubmission') from None


def fal_run(application, payload, key, deadline_seconds=180):
    job = fal_json('https://queue.fal.run/' + application, key, payload)
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        status = fal_json(job['status_url'], key)
        if status['status'] == 'COMPLETED':
            return fal_json(job['response_url'], key), job['request_id']
        time.sleep(2)
    # Preserve the remote request identity; never retry submission automatically.
    raise ProviderError('queue', 202, 'Provider job is still pending; do not resubmit automatically', job.get('request_id'))


class Runtime:
    def __init__(self, root=ROOT, role=None):
        self.root = Path(root)
        self.role = (role or os.getenv('HSI_SYSTEM', 'MUSIC')).upper()
        if self.role not in {'MUSIC', 'UTM', 'TRADER_42', 'OMEGA'}:
            raise ValueError('unsupported service role')
        self.plan = verified_plan(self.root)
        self.runtime_lock = json.loads((self.root / 'hsi_notes_runtime.lock.json').read_text())
        verify_runtime(self.root.resolve(), self.runtime_lock)
        self.core = runpy.run_path(str(self.root / 'validation_snapshots/hsi_three_system_core.py'))
        # Match the explicit service identity even when instantiated by tests.
        self.core['certify'].__globals__['ROLE'] = self.role
        self.directory = Path(tempfile.mkdtemp(prefix='hsi-notes-service-'))
        self.render_lock = threading.Lock()
        self.selftest = {'status': 'RUNNING', 'role': self.role}
        self.preview = None
        self.provider_probe = {'status': 'NOT_REQUESTED'}
        self.corpus_probe = {'status': 'NOT_REQUESTED'}
        self.jobs = {}
        self.orders = None
        if self.role == 'TRADER_42':
            from hsi_binance_orders import BinanceOrders
            journal = Path(os.getenv('HSI_ORDER_JOURNAL_DIR', str(self.directory))) / 'orders.sqlite'
            self.orders = BinanceOrders(journal, self.plan['manifest_sha256'])

    def provenance(self):
        return {'source_commit': self.plan['source_commit'], 'manifest_sha256': self.plan['manifest_sha256'],
                'source_count': self.plan['source_count'], 'plan_uid': self.plan['plan_uid'],
                'release_commit': os.getenv('RAILWAY_GIT_COMMIT_SHA', ''),
                'role': self.role, 'live_trading': bool(self.orders and os.getenv('LIVE_ARMED') == '1' and os.getenv('LIVE_DRY_RUN', '1') == '0'),
                'broker_calls': self.orders.broker_calls if self.orders else 0}

    def certify(self, request, require_manifest=False):
        if self.role == 'MUSIC':
            raise ValueError('Music service does not certify trading or governance requests')
        if require_manifest and request.get('notes_manifest_sha256') != self.plan['manifest_sha256']:
            raise ValueError('Notes manifest mismatch')
        result = self.core['certify'](request)
        result['notes'] = self.provenance()
        result['authorization'] = 'FORMAL_CERTIFICATE_ONLY'
        result['order_submission'] = False
        return result

    def initialize(self):
        try:
            if self.role == 'MUSIC':
                output = self.directory / 'validated-preview'
                evidence = run_validation(self.root, output)
                self.preview = output / 'native/song.wav'
                self.selftest = {'status': 'PASSED', 'local_validation': evidence['status'],
                                 'native': evidence['domain_results']['music_native'],
                                 'finite_release': evidence['finite_release']}
            else:
                req = {'system': self.role, 'status': 'UNRESOLVED', 'step': 1, 'previous_step': 0, 'budget': 32,
                       'subject_uid': self.plan['plan_uid']}
                if self.role == 'TRADER_42':
                    req.update(status='HOLD', operation='HOLD', from_state='FLAT', target_state='FLAT', order=0)
                good = self.certify(req)
                bad = self.certify({**req, 'claims': {'halting_decider': True}})
                if good['closed'] != 1 or bad['closed'] != 0:
                    raise ValueError('positive/negative gate self-test failed')
                self.selftest = {'status': 'PASSED', 'positive_accepted': True, 'forbidden_claim_rejected': True}
                if self.role == 'UTM':
                    self.selftest['bounded_utm'] = replay_utm(self.root, self.directory, self.plan)
            print(json.dumps({'event': 'NOTES_SELFTEST', 'provenance': self.provenance(), 'result': self.selftest}), flush=True)
        except Exception as exc:
            self.selftest = {'status': 'FAILED', 'error': type(exc).__name__, 'message': str(exc)[:500]}
            print(json.dumps({'event': 'NOTES_SELFTEST_FAILED', 'result': self.selftest}), flush=True)
            return
        if self.role == 'MUSIC' and os.getenv('HSI_PROVIDER_PROBE_ONCE') == '1':
            try:
                self.provider_probe = {'status': 'RUNNING', 'max_submissions': 'one lyrics request, then at most one song request'}
                request = {'p': 'HSI-MUSIC-2K/1', 'q': self.plan['domain_plans']['music_ai_bridge']['candidate_keywords']}
                response = self.render_fal(request)
                self.provider_probe = {'status': 'PASSED', 'request_id': response['task_id'], 'url': response['url']}
            except ProviderError as exc:
                self.provider_probe = {'status': 'BLOCKED', **exc.detail}
            except Exception as exc:
                self.provider_probe = {'status': 'FAILED', 'error': type(exc).__name__}
            print(json.dumps({'event': 'NOTES_PROVIDER_PROBE', 'result': self.provider_probe}), flush=True)
        if self.role == 'MUSIC' and os.getenv('HSI_CORPUS_PROBE_ONCE') == '1':
            import subprocess
            env = os.environ.copy()
            env.update(HSI_RC_MAX_CANDIDATES='2', HSI_CORPUS_ITEMS='2', HSI_OPENVERSE_RETRIES='1',
                       HSI_OPENVERSE_TIMEOUT='8', HSI_CORPUS_SR='16000', HSI_E257='0')
            destination = self.directory / 'corpus-probe'
            self.corpus_probe = {'status': 'RUNNING'}
            try:
                process = subprocess.run([os.sys.executable, str(self.root / 'hsi_notes_run.py'), 'corpus', 'ambient', '--out', str(destination)],
                                         env=env, capture_output=True, timeout=180)
                cert_path = destination / 'song.hsicert'
                cert = json.loads(cert_path.read_text()) if cert_path.exists() else None
                self.corpus_probe = {'status': 'PASSED' if process.returncode == 0 else 'UNRESOLVED',
                                     'exit_code': process.returncode, 'audio_verified': bool(cert and cert.get('technical_closed')),
                                     'rights_verified': bool(cert and cert.get('rights_closed')),
                                     'reason': process.stderr.decode('utf-8', 'replace')[-800:]}
                if cert:
                    self.corpus_probe['audio_sha256'] = cert.get('audio_sha256')
            except subprocess.TimeoutExpired:
                self.corpus_probe = {'status': 'UNRESOLVED', 'reason': 'finite cloud probe timeout'}
            print(json.dumps({'event': 'NOTES_CORPUS_PROBE', 'result': self.corpus_probe}), flush=True)

    def render_native(self, request):
        from hsi_native_renderer import build
        prompt = str(request.get('q', '')).strip()[:1200]
        sr, bpm, bars = request.get('sr', 24000), request.get('bpm', 120), request.get('bars', 4)
        check_parameters(sr, bpm, bars)
        prompt += ' ' + self.plan['domain_plans']['music_native']['candidate_keywords'] + ' notes-manifest-' + self.plan['manifest_sha256']
        uid = uuid.uuid4().hex
        output = self.directory / uid
        _, certificate = build(prompt, output, sr=sr, bpm=bpm, bars=bars)
        metrics = measure_wav(output / 'song.wav', sr)
        # Bound ephemeral storage; generated outputs expire on restart.
        import shutil
        generated = sorted((p for p in self.directory.iterdir() if len(p.name) == 32 and p.is_dir()), key=lambda p: p.stat().st_mtime)
        for stale in generated[:-16]:
            shutil.rmtree(stale)
        return {'status': 'SUCCEEDED', 'id': uid, 'path': '/audio/' + uid + '/song.wav', 'renderer': 'HSI-native-field',
                'external_ai': False, 'audio_sha256': certificate['audio_sha256'], 'metrics': metrics,
                'notes': self.provenance(), 'storage': 'ephemeral; download the output'}

    def render_fal(self, request):
        if os.getenv('HSI_ALLOW_PAID_AI', '0') != '1':
            raise ProviderError('configuration', 503, 'Paid AI is disabled; use the native engine')
        key = os.getenv('FAL_KEY', '')
        if not key:
            raise ProviderError('configuration', 503, 'FAL_KEY is not configured')
        keywords = str(request.get('q', '')).strip()[:1200] + ' ' + self.plan['domain_plans']['music_ai_bridge']['candidate_keywords']
        signature = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        if signature in self.jobs:
            return self.jobs[signature]
        self.jobs[signature] = {'status': 'PENDING', 'message': 'A request with this input has already been submitted in this runtime; no automatic resubmission'}
        try:
            lyrics_data, lyrics_id = fal_run('mureka/api/generate/lyrics', {'prompt': 'Write fully original song lyrics from these concepts: ' + keywords + '. Use verse, chorus and bridge sections. Do not quote existing songs.'}, key)
            lyrics = str(lyrics_data.get('lyrics', '')).strip()
            if not lyrics:
                raise ProviderError('lyrics', 502, 'Provider returned no lyrics', lyrics_id)
            model = os.getenv('HSI_MUREKA_MODEL', 'mureka-9.5')
            music, task_id = fal_run('mureka/api/generate/song', {'model': model, 'lyrics': lyrics,
                'prompt': str(request.get('s') or ('Original song with expressive singing: ' + keywords))[:1600]}, key)
            url = (music.get('audio') or {}).get('url')
            if not isinstance(url, str) or not url.startswith('https://'):
                raise ProviderError('song', 502, 'Provider returned no HTTPS audio URL', task_id)
            result = {'status': 'SUCCEEDED', 'url': url, 'task_id': task_id, 'renderer': 'fal-mureka:' + model,
                      'render_route': 'auto-lyrics-conditioned-song', 'lyrics': lyrics, 'title': lyrics_data.get('title', ''),
                      'duration_ms': music.get('duration'), 'song_id': music.get('song_id'), 'notes': self.provenance()}
            self.jobs[signature] = result
            return result
        except ProviderError as exc:
            self.jobs[signature] = {'status': 'BLOCKED' if exc.detail['http_status'] != 202 else 'PENDING', **exc.detail}
            raise

    def render_corpus(self, request):
        import subprocess
        uid = uuid.uuid4().hex
        output = self.directory / uid
        env = os.environ.copy()
        env.update(HSI_RC_MAX_CANDIDATES='8', HSI_CORPUS_ITEMS='2', HSI_OPENVERSE_RETRIES='1',
                   HSI_OPENVERSE_TIMEOUT='8', HSI_CORPUS_SR='16000', HSI_E257='0',
                   HSI_RIGHTS_VERIFIED='0')
        try:
            process = subprocess.run([os.sys.executable, str(self.root / 'hsi_notes_run.py'), 'corpus',
                request['q'][:1200], '--out', str(output)], env=env, capture_output=True, timeout=180)
        except subprocess.TimeoutExpired:
            return {'status': 'UNRESOLVED', 'renderer': 'HSI-open-corpus', 'external_ai': False,
                    'reason': 'finite network/render timeout', 'notes': self.provenance()}
        cert_path = output / 'song.hsicert'
        cert = json.loads(cert_path.read_text()) if cert_path.exists() else None
        success = process.returncode == 0 and cert and cert.get('technical_closed') and (output / 'song.wav').is_file()
        result = {'status': 'SUCCEEDED' if success else 'UNRESOLVED', 'renderer': 'HSI-open-corpus',
                  'external_ai': False, 'exit_code': process.returncode,
                  'rights_verified': bool(cert and cert.get('rights_closed')), 'notes': self.provenance()}
        if success:
            result.update(id=uid, path='/audio/' + uid + '/song.wav', audio_sha256=cert['audio_sha256'],
                          storage='ephemeral; download the output', source_count=len(cert.get('sources', [])))
        else:
            result['reason'] = process.stderr.decode('utf-8', 'replace')[-800:]
        return result


def handler_for(runtime):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json'):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == '/health':
                return self.send(200 if runtime.selftest['status'] == 'PASSED' else 503,
                    {'ok': runtime.selftest['status'] == 'PASSED', 'protocol': PROTOCOL, 'gate_protocol': 'HSI-3SYS/1.0',
                     'role': runtime.role, 'notes': runtime.provenance(), 'selftest': runtime.selftest['status'],
                     'configured': bool(os.getenv('HSI_BRIDGE_TOKEN')),
                     'paid_ai_enabled': os.getenv('HSI_ALLOW_PAID_AI', '0') == '1',
                     'provider': 'native', 'default_engine': os.getenv('HSI_RENDER_ENGINE', 'native'),
                     'optional_ai_provider': 'fal-mureka', 'model': os.getenv('HSI_MUREKA_MODEL', 'mureka-9.5'), 'accepts': 'HSI-MUSIC-2K/1'})
            if path == '/notes':
                return self.send(200, {'notes': runtime.provenance(), 'plan': runtime.plan})
            if path == '/selftest':
                return self.send(200, {'notes': runtime.provenance(), 'result': runtime.selftest,
                                       'provider_probe': runtime.provider_probe, 'corpus_probe': runtime.corpus_probe})
            if path == '/orders/status' and runtime.orders:
                return self.send(200, runtime.orders.status())
            if path == '/preview.wav' and runtime.preview:
                return self.send(200, runtime.preview.read_bytes(), 'audio/wav')
            parts = path.strip('/').split('/')
            if len(parts) == 3 and parts[0] == 'audio' and len(parts[1]) == 32 and all(c in '0123456789abcdef' for c in parts[1]) and parts[2] == 'song.wav':
                audio = runtime.directory / parts[1] / 'song.wav'
                if audio.is_file():
                    return self.send(200, audio.read_bytes(), 'audio/wav')
            return self.send(404, {'error': 'not_found'})

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            order_routes = {'/orders/prepare', '/orders/test', '/orders/submit', '/orders/reconcile'}
            if path not in {'/certify', '/notes/certify', '/render'} | order_routes:
                return self.send(404, {'error': 'not_found'})
            if path in order_routes:
                if not runtime.orders:
                    return self.send(404, {'error': 'not_found'})
                token = os.getenv('HSI_ORDER_CONTROL_TOKEN', '')
                supplied = self.headers.get('Authorization', '').removeprefix('Bearer ')
                if not token or not hmac.compare_digest(token, supplied):
                    return self.send(401, {'error': 'unauthorized'})
            if path == '/render':
                token = os.getenv('HSI_BRIDGE_TOKEN', '')
                supplied = self.headers.get('Authorization', '').removeprefix('Bearer ')
                if not token or not hmac.compare_digest(token, supplied):
                    return self.send(401, {'error': 'unauthorized'})
                if runtime.role != 'MUSIC':
                    return self.send(404, {'error': 'not_found'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    raise ValueError('invalid request size')
                request = json.loads(self.rfile.read(size))
                if not isinstance(request, dict):
                    raise ValueError('request must be an object')
                if path in order_routes:
                    method = path.rsplit('/', 1)[1]
                    result = getattr(runtime.orders, method)(request)
                    return self.send(202 if result['status'] == 'UNKNOWN' else 200, result)
                if path in {'/certify', '/notes/certify'}:
                    result = runtime.certify(request, require_manifest=path.startswith('/notes/'))
                    return self.send(200 if result['closed'] else 422, result)
                if request.get('p') != 'HSI-MUSIC-2K/1' or not isinstance(request.get('q'), str) or not request['q'].strip():
                    raise ValueError('invalid_hsi_request')
                if not runtime.render_lock.acquire(blocking=False):
                    return self.send(429, {'error': 'renderer_busy'})
                try:
                    engine = request.get('engine', os.getenv('HSI_RENDER_ENGINE', 'native'))
                    if engine not in {'native', 'corpus', 'fal'}:
                        raise ValueError('unknown engine')
                    result = {'native': runtime.render_native, 'corpus': runtime.render_corpus, 'fal': runtime.render_fal}[engine](request)
                    if result.get('path'):
                        domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
                        result['url'] = ('https://' + domain if domain else '') + result['path']
                    return self.send(200 if result['status'] == 'SUCCEEDED' else (422 if result['status'] in {'UNRESOLVED', 'BLOCKED'} else 202), result)
                finally:
                    runtime.render_lock.release()
            except ProviderError as exc:
                return self.send(502 if exc.detail['http_status'] != 202 else 202, {'error': 'renderer_error', **exc.detail})
            except (ValueError, KeyError, TypeError) as exc:
                return self.send(400, {'error': str(exc), 'closed': 0})
            except Exception as exc:
                return self.send(500, {'error': 'internal_error', 'type': type(exc).__name__, 'closed': 0})

        def log_message(self, fmt, *args):
            print(json.dumps({'event': 'HSI_NOTES_HTTP', 'message': fmt % args}), flush=True)
    return Handler


def main():
    runtime = Runtime()
    print(json.dumps({'event': 'HSI_NOTES_START', 'notes': runtime.provenance()}), flush=True)
    threading.Thread(target=runtime.initialize, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT', '8080'))), handler_for(runtime)).serve_forever()


if __name__ == '__main__':
    main()
