import unittest,tempfile,pathlib,csv
from trader42_paper.replay import replay
class ReplayTest(unittest.TestCase):
 def file(self,rows):
  d=tempfile.TemporaryDirectory();p=pathlib.Path(d.name)/'bars.csv'
  with p.open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['timestamp','price','signal','qty']);w.writerows(rows)
  self.addCleanup(d.cleanup);return p
 def test_paper_only(self):
  r=replay(self.file([['2026-01-01','100','BUY','1'],['2026-01-02','110','SELL','1']]))
  self.assertEqual(r['real_orders'],0);self.assertFalse(r['broker_connected']);self.assertEqual(len(r['fills']),2)
 def test_no_short(self):
  with self.assertRaisesRegex(ValueError,'short'):replay(self.file([['2026-01-01','100','SELL','1']]))
 def test_order_cap(self):
  with self.assertRaisesRegex(ValueError,'order limit'):replay(self.file([['2026-01-01','1000','BUY','1']]))
 def test_bad_order(self):
  with self.assertRaisesRegex(ValueError,'order'):replay(self.file([['2026-01-02','100','HOLD','0'],['2026-01-01','100','HOLD','0']]))
 def test_nan(self):
  with self.assertRaises(ValueError):replay(self.file([['2026-01-01','NaN','HOLD','0']]))
 def test_halt(self):
  r=replay(self.file([['2026-01-01','100','BUY','2'],['2026-01-02','1','HOLD','0']]))
  self.assertTrue(r['halted'])
if __name__=='__main__':unittest.main()
