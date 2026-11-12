import unittest
from datetime import datetime,timezone
from swingbot.hourly_candle_hypotheses import signals,completed_hours,PATTERNS
from swingbot.hourly_candle_research import run_segmented

def sample(start_minute=0):
 t=int(datetime(2026,8,1,tzinfo=timezone.utc).timestamp()*1000)+start_minute*60000
 return [{"timestamp_ms":t+i*300000,"open":100,"close":100,
         "high":100.1,"low":99.9,"volume":500} for i in range(500)]

class CandlePatternTests(unittest.TestCase):
 def test_only_completed_hours_even_midhour_start(self):
  b=sample(35);h=completed_hours(b)
  self.assertGreater(len(h),20)
  self.assertEqual(b[h[0]["idx"]]["timestamp_ms"]%3600000,55*60000)
 def test_causal_signal_no_future_bar(self):
  b=sample()
  x=signals(b)
  self.assertEqual(set(x),set(PATTERNS))
  b[-1]["high"]=90000
  self.assertEqual(x,signals(b))
 def test_no_phantom_trades(self):
  b=sample()
  feeds={"BTC-EUR":b,"ETH-EUR":[dict(x) for x in b]}
  x=run_segmented([(feeds,{})],"bullish_harami")
  self.assertEqual(x["trades"],0)
  self.assertEqual(x["pnl_eur"],0)
if __name__=="__main__":unittest.main()
