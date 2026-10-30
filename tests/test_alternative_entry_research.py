import unittest
from datetime import datetime,timezone
from swingbot.alternative_entry_families import compute,POLICIES
from swingbot.alternative_entry_research import evaluate
from swingbot.intraday_net_target import ExecutionCosts
def candles(n=700):
 t=int(datetime(2025,7,1,tzinfo=timezone.utc).timestamp()*1000)
 return [{"timestamp_ms":t+i*300000,"open":100+i*.005,
          "close":100+i*.005+.02,"high":100+i*.005+.05,
          "low":100+i*.005-.05,"volume":100} for i in range(n)]
class AltTests(unittest.TestCase):
 def test_cash_baseline(self):
  x=candles(); feeds={"BTC-EUR":x,"ETH-EUR":[dict(b) for b in x]}
  r=evaluate([(feeds,{})],"cash_only",ExecutionCosts())
  self.assertEqual(r["pnl_eur"],0)
  self.assertEqual(r["buys"],0)
 def test_future_bar_doesnt_change_prior_signal(self):
  a=candles();p=compute(a)
  a[350]["close"]=100000
  q=compute(a)
  for name in POLICIES:
   self.assertEqual(349 in p[name],349 in q[name])
if __name__=="__main__":unittest.main()
