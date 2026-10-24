import unittest
from swingbot.shared_btc_eth_portfolio import shared_replay, PAIRS, START_EUR

def data(n=160):
 return [{"timestamp_ms":1700000100000+i*300000,
 "open":100+i*.01,"high":100.1+i*.01,"low":99.9+i*.01,
 "close":100+i*.01,"volume":100} for i in range(n)]

class SharedTests(unittest.TestCase):
 def test_single_balance_and_no_orders(self):
  result=shared_replay({"BTC-EUR":data(),"ETH-EUR":data()},
                       signal=lambda b,i:False)
  self.assertEqual(result["final_liquidation_estimate_eur"],5000)
  self.assertFalse(result["live_orders"])
  self.assertEqual(result["open_positions"],[])
 def test_no_sol_allowed(self):
  with self.assertRaises(ValueError):
   shared_replay({"BTC-EUR":data(),"SOL-EUR":data()})
 def test_misaligned_prices_fail_closed(self):
  x=data();y=data()
  y[10]["timestamp_ms"]+=300000
  with self.assertRaises(ValueError):
   shared_replay({"BTC-EUR":x,"ETH-EUR":y})
 def test_concurrent_signals_share_cash(self):
  r=shared_replay({"BTC-EUR":data(),"ETH-EUR":data()},
                  signal=lambda b,i:i==110)
  self.assertLessEqual(0,r["joint_eur_cash"])
  self.assertLessEqual(r["buys"],2)
  self.assertTrue(set(r["open_positions"]).issubset(PAIRS))
if __name__=="__main__":unittest.main()
