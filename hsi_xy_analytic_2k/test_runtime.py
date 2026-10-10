import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import server


class Runtime(unittest.TestCase):
    def test_smoke_and_godel_replay(self):
        output = server.smoke()
        self.assertEqual(output['one_liner_bytes'], 1799)
        self.assertLess(output['shell_bytes'], 2048)
        self.assertEqual([x['accepted'] for x in output['checks']], [True, False])
        self.assertTrue(all(x['replay_verified'] for x in output['checks']))

    def test_http_health_demo_and_no_post(self):
        server.RESULT = server.smoke()
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        try:
            base = 'http://127.0.0.1:' + str(httpd.server_port)
            with urlopen(base + '/health', timeout=3) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read())
                self.assertEqual(data['status'], 'ok')
            with urlopen(base + '/demo', timeout=3) as response:
                self.assertEqual(json.loads(response.read())['checks'][1]['accepted'], False)
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + '/health', data=b'x', method='POST'), timeout=3)
            self.assertEqual(caught.exception.code, 405)
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
