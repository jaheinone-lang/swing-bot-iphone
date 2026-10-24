import unittest
from datetime import datetime,timezone
from swingbot.daytrade_one_per_day import replay_one_per_day
from swingbot.intraday_net_target import ExecutionCosts

def candles():
 t=int(datetime(2026,9,30,21,tzinfo=timezone.utc).timestamp()*1000)
 return [{"timestamp_ms":t+i*300000,"open":100.,"high":100.2,
          "low":99.9,"close":100.,"volume":100.} for i in range(576)]

class FillSensitivityTests(unittest.TestCase):
 def test_touch_requires_extra_high_for_buffered_limit(self):
  b=candles();e=candles()
  for j in (171,172,173):
   b[j]["high"]=102.0
  a=replay_one_per_day({"BTC-EUR":b,"ETH-EUR":e},
   signal=lambda rows,i:rows is b and i==170)
  self.assertEqual(a["full_take_profits"],1)
  buffered=replay_one_per_day({"BTC-EUR":b,"ETH-EUR":e},
   signal=lambda rows,i:rows is b and i==170,
   tp_fill_buffer_bps=50)
  self.assertEqual(buffered["full_take_profits"],0)
 def test_negative_or_invalid_buffer_fails_closed(self):
  b=candles();e=candles()
  for bps in (-1,600,float("nan")):
   with self.assertRaises(ValueError):
    replay_one_per_day({"BTC-EUR":b,"ETH-EUR":e},
      tp_fill_buffer_bps=bps)
 def test_maker_exit_assumption_keeps_net_gain(self):
  b=candles();e=candles()
  b[171]["high"]=102
  a=replay_one_per_day({"BTC-EUR":b,"ETH-EUR":e},
    signal=lambda rows,i:rows is b and i==170,
    take_profit_costs=ExecutionCosts(25,15,15,0))
  self.assertEqual(a["full_take_profits"],1)
  sell=[v for v in a["events"] if v["type"]=="FULL_TP"]
  self.assertGreaterEqual(sell[0]["net_return_pct_on_position"],1)
if __name__=="__main__":unittest.main()
