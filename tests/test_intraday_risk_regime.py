import unittest
from swingbot.intraday_risk_regime import regime,max_affordable_units

class RegimeRiskTests(unittest.TestCase):
 def test_risk_capped_and_costs_included(self):
  qty=max_affordable_units(5000,5000,100,stop_raw_price=98.5)
  self.assertGreater(qty,0)
  self.assertLess(qty,10)
  self.assertLessEqual(qty*(100*1.0015*1.0025-98.5*.9985*.9975),12.50001)
 def test_no_data_means_no_trade(self):
  self.assertEqual(regime([{"close":100} for _ in range(101)],40),"INSUFFICIENT")
 def test_bad_stop_rejected(self):
  with self.assertRaises(ValueError):
   max_affordable_units(5000,5000,100,stop_raw_price=101)
if __name__=="__main__":unittest.main()
