"""Exercise the deployed HTTP contract and actual non-AI audio bytes."""
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from hsi_notes_service import Runtime, handler_for, fal_json
from hsi_notes_validate import measure_wav
from hsi_binance_orders import BinanceOrders


class HttpContractTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime(role='UTM')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.runtime))
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        shutil.rmtree(self.runtime.directory)

    def request(self, path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = urllib.request.Request(self.url + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            return response.code, raw if response.headers['Content-Type'] == 'audio/wav' else json.loads(raw)

    def sample(self):
        return {'system': 'UTM', 'status': 'UNRESOLVED', 'step': 1, 'previous_step': 0, 'budget': 32}

    def test_health_waits_for_completed_selftest(self):
        self.assertEqual(self.request('/health')[0], 503)
        self.runtime.selftest = {'status': 'PASSED'}
        status, body = self.request('/health')
        self.assertEqual(status, 200)
        self.assertEqual(body['notes']['source_count'], 57)
        self.assertEqual(body['default_engine'], 'native')

    def test_legacy_certify_preserves_contract_and_provenance(self):
        status, body = self.request('/certify', self.sample())
        self.assertEqual(status, 200)
        self.assertEqual(body['protocol'], 'HSI-3SYS/1.0')
        self.assertEqual(body['closed'], 1)
        self.assertFalse(body['order_submission'])
        self.assertEqual(body['notes']['manifest_sha256'], self.runtime.plan['manifest_sha256'])

    def test_strict_manifest_wrong_role_and_forbidden_claims_rejected(self):
        self.assertEqual(self.request('/notes/certify', self.sample())[0], 400)
        good = {**self.sample(), 'notes_manifest_sha256': self.runtime.plan['manifest_sha256']}
        self.assertEqual(self.request('/notes/certify', good)[0], 200)
        self.assertEqual(self.request('/certify', {**self.sample(), 'system': 'OMEGA'})[0], 422)
        self.assertEqual(self.request('/certify', {**self.sample(), 'claims': {'halting_decider': True}})[0], 422)

    def test_render_requires_token(self):
        self.assertEqual(self.request('/render', {'p': 'HSI-MUSIC-2K/1', 'q': 'pulse'})[0], 401)

    def test_account_check_is_operator_authenticated_before_broker_access(self):
        self.runtime.orders = BinanceOrders(self.runtime.directory / 'orders.sqlite', self.runtime.plan['manifest_sha256'])
        body = {'notes_manifest_sha256': self.runtime.plan['manifest_sha256']}
        with patch.dict(os.environ, {'HSI_ORDER_CONTROL_TOKEN': 'test-operator'}), patch.object(self.runtime.orders, 'broker', side_effect=[{'canTrade': True, 'accountType': 'SPOT'}, {'enableSpotAndMarginTrading': True}]) as broker:
            self.assertEqual(self.request('/orders/account-check', body)[0], 401)
            broker.assert_not_called()
            self.assertEqual(self.request('/orders/account-check', {'notes_manifest_sha256': 'bad'}, 'test-operator')[0], 400)
            broker.assert_not_called()
            status, result = self.request('/orders/account-check', body, 'test-operator')
            self.assertEqual(status, 200)
            self.assertEqual(result['status'], 'PERMISSIONS_VERIFIED')
            self.assertFalse(result['order_submission'])

    def test_non_object_and_large_inputs_rejected(self):
        self.assertEqual(self.request('/certify', [1, 2])[0], 400)
        self.assertEqual(self.request('/certify', {'q': 'a' * 17000})[0], 400)

    def test_authenticated_default_native_produces_measured_audio(self):
        self.runtime.role = 'MUSIC'
        with patch.dict(os.environ, {'HSI_BRIDGE_TOKEN': 'local-test-only', 'HSI_RENDER_ENGINE': 'native', 'HSI_ALLOW_PAID_AI': '0'}), patch('hsi_notes_service.fal_run') as paid:
            status, body = self.request('/render', {'p': 'HSI-MUSIC-2K/1', 'q': 'prime pulse', 'sr': 8000, 'bars': 4}, 'local-test-only')
            self.assertEqual(status, 200)
            self.assertFalse(body['external_ai'])
            download_status, raw = self.request(body['path'])
            self.assertEqual(download_status, 200)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), body['audio_sha256'])
            metrics = measure_wav(self.runtime.directory / body['id'] / 'song.wav', 8000)
            self.assertEqual(metrics['frames'], body['metrics']['frames'])
            self.assertGreater(metrics['duration_seconds'], 0)
            paid.assert_not_called()

    def test_paid_engine_disabled_before_submission(self):
        self.runtime.role = 'MUSIC'
        with patch.dict(os.environ, {'HSI_BRIDGE_TOKEN': 'local-test-only', 'HSI_ALLOW_PAID_AI': '0'}), patch('hsi_notes_service.fal_run') as paid:
            status, body = self.request('/render', {'p': 'HSI-MUSIC-2K/1', 'q': 'pulse', 'engine': 'fal'}, 'local-test-only')
            self.assertEqual(status, 502)
            self.assertEqual(body['http_status'], 503)
            paid.assert_not_called()

    def test_provider_key_cannot_be_sent_to_untrusted_url(self):
        for url in ('http://queue.fal.run/job', 'https://evil.example/job', 'https://user@queue.fal.run/job'):
            with self.subTest(url=url), patch('urllib.request.urlopen') as network, self.assertRaises(ValueError):
                fal_json(url, 'local-test-only')
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
