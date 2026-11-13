import unittest
from swingbot.trade_subgroup_uncertainty import wilson,summarize
class UncertaintyTests(unittest.TestCase):
 def test_intervals(self):
  self.assertEqual(wilson(0,0),None)
  lo,hi=wilson(5,19)
  self.assertLess(lo,27)
  self.assertGreater(hi,26)
 def test_partition_and_pnl(self):
  rows=[{"symbol":"BTC-EUR","day":"2022-01-01","exit":"STOP","net_eur":-12.5},
   {"symbol":"ETH-EUR","day":"2025-01-02","exit":"FULL_TP","net_eur":5.0}]
  a=summarize(rows)
  self.assertEqual(a["all"]["buys"],2)
  self.assertEqual(a["BTC-EUR"]["net_pnl_eur"],-12.5)
  self.assertEqual(a["2024-2026"]["completed_one_pct_net_targets"],1)
if __name__=="__main__":unittest.main()
