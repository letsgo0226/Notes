"""Machine-generated finite Dirichlet zero discovery regression and API tests."""
import json
from math import pi,log
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from unittest import TestCase
from zero_field.model import *
from zero_field.server import Handler

class ModelTests(TestCase):
    def test_seed(self):self.assertEqual(SEED,55067263)
    def test_rules(self):
        for q in (0,1):
            for a in (0,1):self.assertEqual(STEP(q,a),(1-q,a,1-2*q))
    def test_coefficients(self):self.assertEqual(tm_coefficients(6),(1,2,1,2,1,2))
    def test_analytic_zero(self):
        r=solve(2,10)
        self.assertEqual(r["zeros"][0]["re"],1)
        self.assertLess(r["zeros"][0]["residual"],1e-8)
        self.assertAlmostEqual(abs(r["zeros"][0]["im"]),pi/log(2),places=10)
    def test_analytic_conjugate(self):
        r=solve(2,10)["zeros"]
        self.assertEqual(len(r),2)
        self.assertAlmostEqual(r[0]["im"],-r[1]["im"])
    def test_no_roots_in_small_analytic_window(self):
        self.assertEqual(len(solve(2,4)["zeros"]),0)
    def test_numeric_candidate_residual(self):
        r=solve(4,15)
        self.assertGreater(len(r["zeros"]),0)
        self.assertFalse(r["complete_within_window"])
        self.assertTrue(all(z["residual"]<=1e-8 for z in r["zeros"]))
    def test_no_root_factor(self):self.assertFalse(evaluate()["zero_factor_inserted"])
    def test_normalization(self):self.assertAlmostEqual(evaluate(2,0,n=4)["f"]["re"],1)
    def test_no_physical_claim(self):
        self.assertFalse(evaluate()["physical_energy_generated"])
        self.assertFalse(solve()["physical_energy_generated"])
    def test_zero_amplitude(self):self.assertEqual(evaluate(amplitude=0)["energy_proxy"],0)
    def test_reject_odd(self):
        with self.assertRaises(ValueError):solve(3)
    def test_reject_bad_n(self):
        with self.assertRaises(ValueError):evaluate(n=66)
    def test_reject_bad_sigma(self):
        with self.assertRaises(ValueError):evaluate(sigma="nan")
    def test_reject_bad_t(self):
        with self.assertRaises(ValueError):solve(4,tmax=100)

class ServerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.port=cls.server.server_address[1]
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def get(self,path):
        with urlopen("http://127.0.0.1:"+str(self.port)+path,timeout=10) as response:
            return response.status,json.load(response)
    def test_health(self):self.assertFalse(self.get("/health")[1]["predefined_zeros"])
    def test_eval(self):self.assertFalse(self.get("/evaluate?n=4")[1]["zero_factor_inserted"])
    def test_solve(self):self.assertEqual(self.get("/solve?n=2&tmax=10")[1]["zeros"][0]["re"],1)
    def test_reject_legacy_plant(self):
        with self.assertRaises(HTTPError) as e:self.get("/evaluate?z=0.5,14")
        self.assertEqual(e.exception.code,400)
    def test_read_only(self):
        with self.assertRaises(HTTPError) as e:
            urlopen(Request("http://127.0.0.1:"+str(self.port)+"/solve",data=b"{}"))
        self.assertEqual(e.exception.code,405)
    def test_404(self):
        with self.assertRaises(HTTPError) as e:self.get("/missing")
        self.assertEqual(e.exception.code,404)
