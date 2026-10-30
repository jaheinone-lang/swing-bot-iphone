import unittest
from datetime import datetime,timezone
from swingbot.alternative_entry_families import compute,POLICIES
from swingbot.distinct_strategy_families import run_period,RULES

def bars():
 t=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
 return [{"timestamp_ms":t+i*300000,"open":100.,"close":100.,"high":100.1,
          "low":99.9,"volume":100.} for i in range(300)]

class DistinctStrategyTests(unittest.TestCase):
 def test_no_future_data_and_no_made_up_profit(self):
  a=bars()
  x=compute(a)
  self.assertEqual(set(POLICIES),set(x))
  self.assertTrue(all(not v for v in x.values()))
  a[-1]["high"]=10000.
  self.assertEqual(x,compute(a))
 def test_cash_baseline_stays_flat(self):
  a=bars();b=bars()
  f={"BTC-EUR":a,"ETH-EUR":b}
  self.assertEqual(run_period([(f,{})],"cash_only")["ending_eur"],5000)
  self.assertEqual(run_period([(f,{})],"trend_continuation")["trades"],0)
  with self.assertRaises(ValueError):
   run_period([(f,{})],"next_year")
if __name__=="__main__":unittest.main()
