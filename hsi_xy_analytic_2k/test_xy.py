import json, os, pathlib, subprocess, tempfile, unittest
from fractions import Fraction
from analytic_bridge import encode_bytes,decode_bytes,interpolate,cardinal,dirichlet

BASE=pathlib.Path(__file__).resolve().parent
SCRIPT=BASE/'hsi_cl_xy_2k.sh'
class XY(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
  self.state=pathlib.Path(self.t.name)/'state.json'
 def call(self, **overrides):
  env={**os.environ,'HSI_STATE':str(self.state),'HSI_PROGRAM':'2','HSI_WORD':'1',**{a:str(b) for a,b in overrides.items()}}
  p=subprocess.run(['sh',str(SCRIPT)],env=env,text=True,capture_output=True,timeout=5)
  self.assertEqual(p.returncode,0,p.stderr)
  return json.loads(p.stdout)
 def test_xy_codes_are_reversible(self):
  out=self.call()
  x=json.loads(decode_bytes(int(out['x'])))
  y=json.loads(decode_bytes(int(out['y'])))
  d=json.loads(self.state.read_text())
  self.assertEqual(len(x),6)
  self.assertEqual(y,[d['p'],d['q'],d['h'],d['m']])
 def test_invalid_candidate_same_y_different_x(self):
  self.call();before=self.state.read_text();bad=self.call(HSI_CAND='[999,0,[]]')
  self.assertEqual(bad['accepted'],0)
  self.assertEqual(json.loads(decode_bytes(int(bad['y']))),[json.loads(before)[k] for k in ('p','q','h','m')])
  self.assertNotEqual(bad['x'],bad['y'])
 def test_exact_dirichlet_moments(self):
  self.call();out=self.call(HSI_CAND='[99,0,[]]')
  event=json.loads(decode_bytes(int(json.loads(self.state.read_text())['H'][-1])))
  residuals=event[-1]
  self.assertEqual(out['D0'],sum(residuals))
  self.assertEqual(Fraction(out['D1_num'],30),sum((Fraction(r,p) for r,p in zip(residuals,(2,3,5))),Fraction()))
  self.assertTrue(any(residuals))
 def test_interpolation_integer_nodes(self):
  b=[0,.125,.5,.75,.9]
  for n in range(len(b)):
   self.assertAlmostEqual(interpolate(b,n).real,b[n])
 def test_interpolation_complex_noderivative(self):
  self.assertAlmostEqual(abs(cardinal(2+0j,2)-(1+0j)),0)
  z=1.3+0.4j
  self.assertTrue(abs(interpolate([0.2,0.4,0.6],z))<5)
 def test_dirichlet_is_entire_finite(self):
  self.assertEqual(dirichlet((0,0,0),2+3j),0)
  self.assertEqual(dirichlet((1,0,0),0),1)
  self.assertEqual(dirichlet((0,1,0),1),1/3)
 def test_no_sha_and_strict_length(self):
  raw=(BASE/'command.txt').read_bytes();self.assertLess(len(raw),2048)
  self.assertNotIn(b'sha',raw.lower());self.assertLess(len(SCRIPT.read_bytes()),2048)

if __name__=='__main__':unittest.main(verbosity=2)
