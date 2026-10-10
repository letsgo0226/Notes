"""HSI–CL–XY/2K read-only Railway canary: runs exactly one safe local smoke test.

This service does not accept user-defined UTM programs, trade, modify repositories,
or call remote services. One-Liner execution is isolated in a temporary directory.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

from verify_replay import verify

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / 'hsi_cl_xy_2k.sh'


def smoke():
    assert len((HERE / 'command.txt').read_bytes()) < 2048
    assert len(LAUNCHER.read_bytes()) < 2048
    with TemporaryDirectory(prefix='hsi-xy-smoke-') as temp:
        trials = []
        for rejected in (False, True):
            state = Path(temp) / ('bad.state' if rejected else 'good.state')
            env = {
                'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                'HSI_STATE': str(state),
                'HSI_PROGRAM': '2',
                'HSI_WORD': '1',
            }
            if rejected:
                env['HSI_CAND'] = '[99,0,[]]'
            result = run(['sh', str(LAUNCHER)], cwd=temp, env=env,
                         text=True, capture_output=True, timeout=10, check=True)
            output = json.loads(result.stdout)
            report = verify(json.loads(state.read_text()))
            assert report['verified'] is True
            assert output['protocol'] == 'HSI-CL-XY/2K'
            assert bool(output['accepted']) is not rejected
            assert (output['D0'] > 0) is rejected
            assert report['history'] == 1
            trials.append({
                'case': 'rejected_candidate' if rejected else 'accepted_step',
                'accepted': bool(output['accepted']),
                'dirichlet_D0': output['D0'],
                'step': output['step'],
                'replay_verified': report['verified'],
            })
    return {'protocol': 'HSI-CL-XY/2K', 'mode': 'read_only_canary',
            'one_liner_bytes': len((HERE / 'command.txt').read_bytes()),
            'shell_bytes': len(LAUNCHER.read_bytes()),
            'checks': trials, 'domain_trade_authority': False,
            'universal_halting_claim': False, 'automatic_railway_deploy': False}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/health', '/demo'):
            self.reply(404, {'error': 'not_found'})
            return
        self.reply(200, RESULT if self.path == '/demo' else
                   {'status': 'ok', 'protocol': RESULT['protocol'],
                    'mode': RESULT['mode'], 'verified': True})

    def do_POST(self):
        self.reply(405, {'error': 'read_only'})

    def reply(self, status, payload):
        data = (json.dumps(payload, separators=(',', ':')) + '\n').encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    RESULT = smoke()  # A failed check prevents health endpoint from going live.
    print(json.dumps(RESULT), flush=True)
    port = int(os.environ.get('PORT', '8080'))
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
