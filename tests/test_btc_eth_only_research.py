import unittest
from swingbot.btc_eth_only_research import (ACTIVE_PAIRS,OBSERVE_ONLY,
RISK_PER_TRADE_PCT,NET_TP_PCT,MAX_POSITION_PCT)

class ActiveMarketsTests(unittest.TestCase):
 def test_btc_eth_only(self):
  self.assertEqual(set(ACTIVE_PAIRS),{"BTC-EUR","ETH-EUR"})
  self.assertEqual(set(OBSERVE_ONLY),{"SOL-EUR"})
  self.assertTrue(set(ACTIVE_PAIRS).isdisjoint(OBSERVE_ONLY))
 def test_risk_limits(self):
  self.assertEqual(RISK_PER_TRADE_PCT,.25)
  self.assertEqual(NET_TP_PCT,1.)
  self.assertEqual(MAX_POSITION_PCT,20.)
if __name__=="__main__":unittest.main()
