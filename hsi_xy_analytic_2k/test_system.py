"""Behavior-preserving extension regression and independent replay tests."""
import base64,copy,json,os,pathlib,re,subprocess,sys,tempfile,unittest,zlib
from verify_replay import verify,code_text,trans,decode,nxt,check_extension

BASE=pathlib.Path(__file__).resolve().parent

def machine(k,d):
 B=4*(k+1);c=sum(v*B**j for j,v in enumerate(d));z=c+k-1
 return z*(z+1)//2+c

def embed(old,K,pi,extra=None):
 k,_=decode(old);d=[0]*(2*K)
 for q in range(k):
  for a in (0,1):
   v=trans(old,q,a);r=v%(k+1)
   d[2*pi[q]+a]=(pi[r] if r<k else K)+(v//(k+1))*(K+1)
 for (q,a),v in (extra or {}).items():d[2*q+a]=v
 return machine(K,d)

OLD=machine(1,[3,0]);NEW=embed(OLD,2,[0],{(1,0):11,(1,1):11});ALT=embed(OLD,2,[1],{(0,0):11,(0,1):11})

class TestExtension(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'trace.json'
 def tearDown(self):self.tmp.cleanup()
 def call(self,expect_ok=True,**env):
  e={**os.environ,'HSI_STATE':str(self.path),**{k:str(v) for k,v in env.items()}}
  p=subprocess.run(['sh',str(BASE/'hsi_cl_xy_2k.sh')],env=e,capture_output=True,text=True,timeout=20)
  if expect_ok:self.assertEqual(p.returncode,0,p.stderr)
  if p.returncode:return p
  return json.loads(p.stdout)
 def state(self):return json.loads(self.path.read_text())
 def init(self):return self.call(HSI_PROGRAM=OLD,HSI_WORD='0')
 def test_01_command_size(self):self.assertLess(len((BASE/'command.txt').read_bytes()),2048)
 def test_02_shell_size(self):self.assertLess(len((BASE/'hsi_cl_xy_2k.sh').read_bytes()),2048)
 def test_03_compression_matches_readable(self):
  txt=(BASE/'command.txt').read_text();m=re.search('b85decode\\("([^"]+)"\\)',txt)
  self.assertIsNotNone(m);self.assertEqual(zlib.decompress(base64.b85decode(m.group(1))),(BASE/'core_readable.py').read_bytes())
 def test_04_original_preserved(self):
  raw=(BASE/'HSI_UTM_original.sh').read_bytes();self.assertEqual(len(raw),1907);self.assertIn(b'HSI-UTM/1.0',raw)
 def test_05_godel_roundtrip(self):
  from functools import reduce
  ev=['E',NEW,[0],[0,0,0]];j=json.dumps(ev,separators=(',',':'))
  code=reduce(lambda n,b:n*257+b+1,j.encode(),1)
  self.assertEqual(code_text(str(code)),j)
 def test_06_state_count_growth(self):
  self.assertEqual(decode(OLD)[0],1);self.assertEqual(decode(NEW)[0],2)
 def test_07_injection_certificate(self):self.assertEqual(check_extension(OLD,NEW,[0]),[0,0,0])
 def test_08_alternate_injection_certificate(self):self.assertEqual(check_extension(OLD,ALT,[1]),[0,0,0])
 def test_09_old_step_conjugacy_many_tapes(self):
  for q in (0,1):
   for h in (-2,0,3):
    for m in ([],[0],[-2,0,3]):
     o=nxt(OLD,q,h,m)
     n=nxt(NEW,0 if q==0 else 2,h,m)
     self.assertEqual(n, None if o is None else (0 if o[0]==0 else 2,o[1],o[2]))
 def test_10_accept_extension(self):
  self.init();o=self.call(HSI_RULE=NEW)
  self.assertEqual((o['accepted'],o['kind'],o['states']), (1,'EVOLVE',2))
  self.assertEqual(verify(self.state())['accepted_extensions'],1)
 def test_11_extra_entry_adds_behavior(self):
  new_state=pathlib.Path(self.tmp.name)/'new.json'
  self.path=new_state
  o=self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1)
  self.assertEqual(o['accepted'],1)
  self.assertEqual((self.state()['q'],self.state()['h'],self.state()['m']),(2,1,[0]))
  self.assertEqual(verify(self.state())['accepted_steps'],1)
 def test_12_default_old_entry_retains_behavior(self):
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=0)
  self.assertEqual((self.state()['q'],self.state()['h'],self.state()['m']),(2,1,[]))
 def test_13_old_halt_maps_new_halt(self):
  self.init();self.assertEqual(self.state()['q'],1)
  o=self.call(HSI_RULE=NEW)
  self.assertTrue(o['accepted']);self.assertEqual(o['q'],2)
  self.assertEqual(self.call()['kind'],'HALTED')
 def test_14_reject_bad_mapping(self):
  self.init();o=self.call(HSI_RULE=NEW,HSI_PERM='[2]')
  self.assertEqual(o['accepted'],0);self.assertEqual(self.state()['p'],OLD)
  self.assertEqual(verify(self.state())['rejections'],1)
 def test_15_reject_bad_old_transition(self):
  self.init();bad=embed(machine(1,[3,0]),2,[0],{(1,0):1,(1,1):2})
  k,c=decode(bad);B=4*(k+1);v=c%B
  c+=1-v%B
  z=c+k-1;bad=z*(z+1)//2+c
  o=self.call(HSI_RULE=bad)
  self.assertEqual(o['accepted'],0);self.assertEqual(self.state()['p'],OLD)
 def test_16_reject_duplicate_mapping(self):
  self.init();o=self.call(HSI_RULE=NEW,HSI_PERM='[0,0]');self.assertFalse(o['accepted'])
 def test_17_reject_invalid_json(self):
  self.init();self.assertFalse(self.call(HSI_RULE=NEW,HSI_PERM='notjson')['accepted'])
 def test_18_reject_negative_rule(self):
  self.init();self.assertFalse(self.call(HSI_RULE=-1)['accepted'])
 def test_19_reject_malformed_step(self):
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1,HSI_RULE=NEW)
  o=self.call(HSI_CAND='[0,0,[]]');self.assertEqual(o['accepted'],0)
  self.assertEqual(verify(self.state())['rejections'],1)
 def test_20_reject_python_expression_not_exec(self):
  marker=pathlib.Path(self.tmp.name)/'MARKER'
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1,HSI_RULE=NEW)
  self.call(HSI_CAND=f'__import__("os").system("touch {marker}")')
  self.assertFalse(marker.exists());self.assertEqual(verify(self.state())['rejections'],1)
 def test_21_reject_2048_rule_bytes(self):
  self.init();bad=int('1'+'0'*2047)
  o=self.call(HSI_RULE=bad);self.assertFalse(o['accepted'])
  self.assertEqual(self.state()['p'],OLD)
 def test_22_reject_2048_origin_bytes(self):
  p=self.call(expect_ok=False,HSI_PROGRAM='1'+'0'*2047)
  self.assertNotEqual(p.returncode,0);self.assertFalse(self.path.exists())
 def test_23_history_mutation_detected(self):
  self.init();self.call(HSI_RULE=NEW)
  d=self.state();d['H'][1]='257'
  with self.assertRaises((ValueError,UnicodeError,json.JSONDecodeError)):verify(d)
 def test_24_history_fake_certificate_detected(self):
  self.init();o=self.call(HSI_RULE=ALT,HSI_PERM='[0]');self.assertFalse(o['accepted'])
  d=self.state();ev=json.loads(code_text(d['H'][-1]));ev[-1]=[0,0,0]
  from functools import reduce
  d['H'][-1]=str(reduce(lambda n,b:n*257+b+1,json.dumps(ev,separators=(',',':')).encode(),1))
  with self.assertRaises(ValueError):verify(d)
 def test_25_final_tape_tamper_detected(self):
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1)
  d=self.state();d['m']=[]
  with self.assertRaises(ValueError):verify(d)
 def test_26_mixed_conservative_evolutions(self):
  self.init();self.assertTrue(self.call(HSI_RULE=NEW)['accepted'])
  self.assertTrue(self.call(HSI_RULE=ALT,HSI_PERM='[1,0]')['accepted'])
  self.assertEqual(verify(self.state())['accepted_extensions'],2)
 def test_27_relabel_supported(self):
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1)
  self.assertTrue(self.call(HSI_RULE=ALT,HSI_PERM='[1,0]')['accepted'])
 def test_28_rejection_no_step_progress(self):
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1,HSI_RULE=NEW)
  previous=self.state();self.call(HSI_CAND='[99,0,[]]')
  after=self.state();self.assertEqual((after['n'],after['q'],after['m']),(previous['n'],previous['q'],previous['m']))
 def test_29_candidate_bool_not_int(self):
  self.call(HSI_PROGRAM=NEW,HSI_WORD='0',HSI_START=1,HSI_RULE=NEW)
  self.assertFalse(self.call(HSI_CAND='[true,1,[0]]')['accepted'])
 def test_30_dirichlet_zero_equivalence(self):
  self.init();self.assertEqual(self.call(HSI_RULE=NEW)['D0'],0)
  self.assertGreater(self.call(HSI_RULE=ALT,HSI_PERM='[0,1]')['D0'],0)

if __name__=='__main__':unittest.main(verbosity=2)
