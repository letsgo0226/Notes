"""Finite numerical identities, bounded inputs and read-only API tests."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from unittest import TestCase
from zero_field.model import *
from zero_field.server import Handler

class FieldTests(TestCase):
    def test_seed_exact(self):self.assertEqual(STEP(0,0),(1,0,1))
    def test_all_transitions(self):
        for q in (0,1):
            for a in (0,1):self.assertEqual(STEP(q,a),(1-q,a,1-2*q))
    def test_coefficients(self):self.assertEqual(tm_coefficients(6),(1,2,1,2,1,2))
    def test_stated_zero(self):self.assertLess(evaluate(.5,DEFAULT_ZERO.imag)["energy_proxy"],1e-20)
    def test_conjugate_zero(self):self.assertLess(evaluate(.5,-DEFAULT_ZERO.imag)["energy_proxy"],1e-20)
    def test_normalize(self):self.assertAlmostEqual(evaluate(2,0)["field"]["re"],1,places=12)
    def test_custom_zero(self):self.assertLess(evaluate(.5,3,zeros=(.5+3j,))["energy_proxy"],1e-24)
    def test_amplitude(self):self.assertAlmostEqual(evaluate(2,0,amplitude=2)["field"]["re"],2)
    def test_zero_amp(self):self.assertEqual(evaluate(amplitude=0)["energy_proxy"],0)
    def test_n_bound(self):
        with self.assertRaises(ValueError):evaluate(n=65)
    def test_invalid_nan(self):
        with self.assertRaises(ValueError):evaluate(sigma="nan")
    def test_zero_normalization_reject(self):
        with self.assertRaises(ValueError):evaluate(zeros=(2+0j,))
    def test_reject_out_of_domain(self):
        with self.assertRaises(ValueError):evaluate(t=99)
    def test_no_physical_claim(self):
        d=evaluate();self.assertTrue(d["not_physical_energy"])
        self.assertFalse(d["universal_solution_proven"])

class ServerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.port=cls.server.server_address[1]
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def get(self,path):
        with urlopen("http://127.0.0.1:"+str(self.port)+path,timeout=5) as r:
            return r.status,json.load(r)
    def test_health(self):
        status,r=self.get("/health")
        self.assertEqual(status,200);self.assertTrue(r["seed_verified"])
    def test_eval(self):
        _,r=self.get("/evaluate?z=0.5%2C3&t=3&sigma=0.5")
        self.assertLess(r["energy_proxy"],1e-24)
    def test_405(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request("http://127.0.0.1:"+str(self.port)+"/evaluate",data=b"{}"),timeout=5)
        self.assertEqual(error.exception.code,405)
    def test_bad_query(self):
        with self.assertRaises(HTTPError) as error:
            self.get("/evaluate?secret=1")
        self.assertEqual(error.exception.code,400)
    def test_missing(self):
        with self.assertRaises(HTTPError) as error:
            self.get("/nonexistent")
        self.assertEqual(error.exception.code,404)
