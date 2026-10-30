import unittest
from swingbot.regime_filter_replay import allowed,POLICIES
class RegimeTests(unittest.TestCase):
 def test_pre_entry_causal(self):
  b=[{"close":100+i*.05} for i in range(190)]
  first=[allowed(b,160,n) for n in POLICIES]
  for x in b[161:]:x["close"]=99999
  self.assertEqual(first,[allowed(b,160,n) for n in POLICIES])
 def test_reject_unknown(self):
  b=[{"close":100+i*.05} for i in range(190)]
  from swingbot.regime_filter_replay import replay
  with self.assertRaises(ValueError):replay([],"unrecognized")
if __name__=="__main__":unittest.main()
