"""Adversarial tests for identity restoration and E257 reversible receipts."""
import json
import random
import subprocess
import sys
import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from .core import e257, un257
from .identity import MAX_INPUT_BYTES, proof, tape_encode, tape_decode, transitions, twice
from .server import Handler


class IdentityTests(unittest.TestCase):
    def test_four_decoded_rules(self):
        rules = transitions()
        self.assertEqual([rules[q, a] for q in (0, 1) for a in (0, 1)],
                         [(1, 0, 1), (1, 1, 1), (0, 0, -1), (0, 1, -1)])

    def test_empty(self):
        self.assertEqual(twice(b''), b'')

    def test_zeros(self):
        for s in (b'\x00', b'\x00\x00', b'abc\x00', b'\x00abc\x00'):
            self.assertEqual(twice(s), s)

    def test_all_bytes(self):
        s = bytes(range(256))
        self.assertEqual(twice(s), s)
        self.assertEqual(un257(e257(s)), s)

    def test_unicode(self):
        s = '星光與愛🛸'.encode('utf-8')
        self.assertEqual(twice(s), s)

    def test_repeatable_random(self):
        rng = random.Random(55067263)
        for length in (1, 5, 32, 128, 256):
            s = rng.randbytes(length)
            self.assertEqual(twice(s), s)

    def test_maximum_bounded_input(self):
        s = b'\xff' * MAX_INPUT_BYTES
        self.assertEqual(twice(s), s)

    def test_over_limit_rejected(self):
        with self.assertRaises(ValueError):
            twice(b'x' * (MAX_INPUT_BYTES + 1))

    def test_tape_marker_avoids_trailing_zero_collision(self):
        self.assertNotEqual(tape_encode(b'A'), tape_encode(b'A\x00'))
        self.assertEqual(tape_decode(tape_encode(b'A\x00')), b'A\x00')

    def test_tape_marker_corruption_rejected(self):
        with self.assertRaises(ValueError):
            tape_decode({1})

    def test_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            twice('not bytes')

    def test_godel_receipt_reversible(self):
        sample = b'\x00\xffCOSMIC_LOVE\x00'
        record = proof(sample)
        self.assertEqual(record['s_hex'], record['result_hex'])
        self.assertEqual(un257(int(record['godel_hex'], 16)), sample)
        self.assertTrue(record['validated'])
        self.assertFalse(record['trading_authorized'])

    def test_malformed_code_rejected(self):
        with self.assertRaises(ValueError):
            un257(257)

    def test_cli_binary_stdin(self):
        s = b'\x00\xfeHi\x00'
        cp = subprocess.run([sys.executable, '-m', 'godel_zero_field.identity', '--stdin'],
                            input=s, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True, timeout=15)
        record = json.loads(cp.stdout)
        self.assertEqual(bytes.fromhex(record['result_hex']), s)

    def test_python_optimize_does_not_disable_verification(self):
        cp = subprocess.run([sys.executable, '-O', '-m', 'godel_zero_field.identity', '--hex', '00ff'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True, timeout=15)
        self.assertEqual(json.loads(cp.stdout)['result_hex'], '00ff')


class IdentityEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.address = 'http://127.0.0.1:' + str(cls.server.server_address[1])
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_identity_proof_endpoint(self):
        with urlopen(self.address + '/identity-proof', timeout=5) as r:
            d = json.load(r)['receipt']
        self.assertEqual(d['s_hex'], b'COSMIC_LOVE'.hex())
        self.assertEqual(d['result_hex'], d['s_hex'])
        self.assertEqual(un257(int(d['godel_hex'], 16)), b'COSMIC_LOVE')

    def test_reject_endpoint_parameters(self):
        with self.assertRaises(HTTPError) as e:
            urlopen(self.address + '/identity-proof?s_hex=deadbeef', timeout=5)
        self.assertEqual(e.exception.code, 400)

    def test_health_includes_identity_selftest(self):
        with urlopen(self.address + '/health', timeout=5) as r:
            d = json.load(r)
        self.assertTrue(d['two_step_identity_selftest'])


if __name__ == '__main__':
    unittest.main()
