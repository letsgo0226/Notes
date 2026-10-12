"""Adversarial tests for exact Gödel arithmetic without floats."""
import json
import tempfile
import unittest
from fractions import Fraction
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from .core import *
from .server import Handler

class ExactTests(unittest.TestCase):
 def test_seed_rules(self):self.assertEqual(machine_rules(),((1,0,1),(1,1,1),(0,0,-1),(0,1,-1)))
 def test_periodic_coefficients(self):self.assertEqual(coefficients(8),(1,2,1,2,1,2,1,2))
 def test_exact_D_2(self):self.assertEqual(exact_D(2,2),Fraction(3,2))
 def test_exact_normalization(self):
  r=evaluate_integer(2,2)
  self.assertEqual(decode_rational(r['F_godel']),Fraction(1))
  self.assertEqual(decode_rational(r['E_godel']),Fraction(1))
 def test_exact_integer_sample(self):
  r=evaluate_integer(2,0)
  self.assertEqual(decode_rational(r['F_godel']),Fraction(2))
  self.assertEqual(decode_rational(r['E_godel']),Fraction(4))
 def test_fraction_negative_integer_argument(self):
  r=evaluate_integer(2,-1)
  self.assertEqual(decode_rational(r['F_godel']),Fraction(10,3))
 def test_E257_roundtrip_binary(self):
  for blob in (b'',b'\x00\xff',bytes(range(256)),b'Cosmic Love'):
   self.assertEqual(un257(e257(blob)),blob)
 def test_rational_roundtrip(self):
  for q in (Fraction(0),Fraction(7,19),Fraction(-121,33)):
   self.assertEqual(decode_rational(rational_code(q)),q)
 def test_reject_float(self):
  with self.assertRaises(ValueError):pack({'x':.1})
 def test_reject_float_nested(self):
  with self.assertRaises(ValueError):pack({'x':[{'z':1.0}]})
 def test_reject_forged_unreduced_fraction(self):
  with self.assertRaises(ValueError):decode_rational(pack({'type':'Q','num':'2','den':'4'}))
 def test_reject_zero_denominator(self):
  with self.assertRaises(ValueError):decode_rational(pack({'type':'Q','num':'1','den':'0'}))
 def test_invalid_e257_zero_digit(self):
  with self.assertRaises(ValueError):un257(257)
 def test_reject_bad_n(self):
  with self.assertRaises(ValueError):model_certificate(65)
 def test_reject_noninteger_s(self):
  with self.assertRaises(ValueError):evaluate_integer(16,Fraction(1,2))
 def test_reject_nonpositive_amp_den(self):
  with self.assertRaises(ValueError):evaluate_integer(16,0,1,0)
 def test_receipt_independent_replay(self):
  receipt=evaluate_integer(16,-3,3,7)
  self.assertTrue(verify_evaluation(receipt))
 def test_tampering_rejected(self):
  receipt=evaluate_integer(2,0)
  receipt['F_godel']=rational_code(Fraction(7))
  with self.assertRaises(ValueError):verify_evaluation(receipt)
 def test_model_all_godel(self):
  r=model_certificate(64)
  model=unpack(r['model_godel'])
  self.assertEqual(model['terms'][0]['coefficient'],'1')
  self.assertEqual(model['terms'][1]['coefficient'],'2')
  self.assertEqual(len(model['terms']),64)
 def test_symbolic_root_no_floats(self):
  d=symbolic_root_n2(1)
  root=unpack(d['root_godel'])
  self.assertEqual(root['im']['numerator'],'3')
  self.assertEqual(root['im']['denominator'],'log(2)')
  self.assertFalse(d['root_is_approximation'])
 def test_no_prescribed_zero_for_n16(self):
  d=model_certificate(16)
  self.assertEqual(d['zero_search_status'],'EXACT_ROOTS_UNRESOLVED_FOR_GENERAL_N')
 def test_receipt_digest_deterministic(self):
  x=model_certificate(6)
  self.assertEqual(receipt_digest(x),receipt_digest(x))
 def test_no_approximate_literals_in_receipt(self):
  r=evaluate_integer(16,0)
  self.assertNotIn('.',json.dumps(r))

class APITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  cls.port=cls.srv.server_address[1]
  cls.t=Thread(target=cls.srv.serve_forever,daemon=True)
  cls.t.start()
 @classmethod
 def tearDownClass(cls):
  cls.srv.shutdown();cls.srv.server_close();cls.t.join()
 def get(self,path):
  with urlopen('http://127.0.0.1:'+str(self.port)+path,timeout=5) as r:
   return json.load(r)
 def test_health_read_only(self):
  d=self.get('/health');self.assertTrue(d['read_only']);self.assertFalse(d['float_mode_enabled'])
 def test_exact_api(self):
  x=self.get('/evaluate?n=2&s=0')['receipt']
  self.assertEqual(decode_rational(x['F_godel']),Fraction(2))
 def test_model_api(self):
  x=self.get('/model?n=16')['receipt']
  self.assertEqual(len(unpack(x['model_godel'])['terms']),16)
 def test_symbolic_api(self):
  d=self.get('/symbolic-root?k=3')['receipt']
  self.assertEqual(unpack(d['root_godel'])['im']['numerator'],'7')
 def test_decimal_query_rejected(self):
  with self.assertRaises(HTTPError) as e:self.get('/evaluate?s=0.5')
  self.assertEqual(e.exception.code,400)
 def test_post_disabled(self):
  with self.assertRaises(HTTPError) as e:urlopen(Request('http://127.0.0.1:'+str(self.port)+'/evaluate',data=b'{}'),timeout=5)
  self.assertEqual(e.exception.code,405)
 def test_unknown_field_rejected(self):
  with self.assertRaises(HTTPError) as e:self.get('/model?binance_key=demo')
  self.assertEqual(e.exception.code,400)

if __name__=='__main__':unittest.main()
