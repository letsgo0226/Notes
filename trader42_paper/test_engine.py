import unittest
from trader42_paper.engine import PaperEngine,Limits,run
class PaperSafetyTests(unittest.TestCase):
 def test_simulated_buy_and_sell(self):
  e=PaperEngine()
  e.trade("BUY","100","1")
  e.trade("SELL","110","1")
  self.assertEqual(e.units,0)
  self.assertTrue(e.realized>0)
 def test_no_exchange_authority(self):
  x=run({"actions":[{"kind":"BUY","price":"100","qty":"1"}]})
  self.assertEqual(x["orders_submitted"],0)
  self.assertFalse(x["broker_connected"])
  self.assertFalse(x["real_funds_used"])
 def test_position_ceiling(self):
  with self.assertRaisesRegex(ValueError,"POSITION"):
   PaperEngine().trade("BUY","1","11")
 def test_notional_ceiling(self):
  with self.assertRaisesRegex(ValueError,"NOTIONAL"):
   PaperEngine().trade("BUY","501","1")
 def test_no_short(self):
  with self.assertRaisesRegex(ValueError,"SHORT"):
   PaperEngine().trade("SELL","10","1")
 def test_negative_qty(self):
  with self.assertRaises(ValueError):PaperEngine().trade("BUY","10","-1")
 def test_nan_rejected(self):
  with self.assertRaises(ValueError):PaperEngine().trade("BUY","NaN","1")
 def test_daily_loss_halts(self):
  e=PaperEngine(Limits(max_daily_loss="20"))
  e.trade("BUY","100","1")
  self.assertTrue(e.mark("50")["halted"])
  with self.assertRaisesRegex(ValueError,"HALT"):e.trade("SELL","50","1")
 def test_no_cash_overdraft(self):
  e=PaperEngine(Limits(initial_cash="50",max_notional="1000"))
  with self.assertRaisesRegex(ValueError,"CASH"):e.trade("BUY","100","1")
 def test_no_unknown_action(self):
  with self.assertRaises(ValueError):run({"actions":[{"kind":"LIVE_BUY","price":"1","qty":"1"}]})
 def test_reject_unexpected_broker_keys(self):
  with self.assertRaises(ValueError):run({"api_key":"secret","actions":[]})
 def test_reject_unexpected_trade_fields(self):
  with self.assertRaises(ValueError):run({"actions":[{"kind":"BUY","price":"1","qty":"1","exchange":"binance"}]})
 def test_mark_to_market(self):
  e=PaperEngine()
  e.trade("BUY","100","1")
  m=e.mark("110")
  self.assertTrue(float(m["pnl"])>0)
 def test_limit_configuration(self):
  with self.assertRaises(ValueError):PaperEngine(Limits(fee_rate="-1"))
if __name__=="__main__":unittest.main()
