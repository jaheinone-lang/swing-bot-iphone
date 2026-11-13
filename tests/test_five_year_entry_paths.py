"""Entry outcome diagnostics: use only pre-entry features and censor after exit."""
import unittest
from datetime import datetime,timezone
from swingbot.five_year_entry_paths import features_before_entry,diagnose,HORIZONS
from swingbot.five_year_fast_signals import generate_frozen_signals

def candles(n=600):
 t=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
 return [{"timestamp_ms":t+i*300000,"open":100+i*.03,"close":100.02+i*.03,
          "high":100.05+i*.03,"low":99.92+i*.03,"volume":1000+i%13}
          for i in range(n)]

class EntryPathTests(unittest.TestCase):
 def test_pre_entry_inputs_ignore_future(self):
  data=candles()
  old=features_before_entry(data,220)
  data[220]["close"]=99999
  data[221]["volume"]=999999
  self.assertEqual(features_before_entry(data,220),old)
 def test_empty_buys_are_reported_without_fabrication(self):
  btc=candles();eth=[dict(b) for b in btc]
  feeds={"BTC-EUR":btc,"ETH-EUR":eth}
  cache={s:{k:set() for k in ("morning_strict",)} for s in feeds}
  v=diagnose([(feeds,cache)])
  self.assertEqual(v["total_trades"],0)
  self.assertEqual(v["full_tp"]["count"],0)
  self.assertIsNone(v["stop_loss"]["metrics"]["held_15m_change_pct"]["median"])
if __name__=="__main__":unittest.main()
