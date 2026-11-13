"""Safety tests for true multi-day swing replay; no broker access."""
import unittest
from datetime import datetime,timezone
from swingbot.four_hour_swing_research import (
    four_hour_signals,era_segments,replay,RULES,STRESS)
from swingbot.daytrade_one_per_day import PAIRS

def bars(n=2800,base=100.):
    start=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
    return [{"timestamp_ms":start+i*300000,"open":base,"high":base+0.1,
             "low":base-.1,"close":base,"volume":100.} for i in range(n)]

class SwingTests(unittest.TestCase):
    def test_flat_candles_no_phantom_profits(self):
        x=bars()
        f={s:[dict(a) for a in x] for s in PAIRS}
        for rule in RULES:
            row=replay([(f,0)],rule)
            self.assertEqual(row["trades"],0)
            self.assertEqual(row["pnl_eur"],0)
    def test_only_complete_4h_no_future(self):
        x=bars()
        a=four_hour_signals(x,"breakout")
        self.assertEqual(a,set())
        x[-1]["high"]=999
        self.assertEqual(a,four_hour_signals(x,"breakout"))
    def test_invalid_strategy(self):
        with self.assertRaises(ValueError):
            four_hour_signals(bars(),"profit_guarantee")
    def test_eras_no_pre_boundary_trade(self):
        x=bars()
        f={s:[dict(a) for a in x] for s in PAIRS}
        e=era_segments([(f,{})])
        self.assertEqual(e["early"],[])
        self.assertEqual(len(e["later"]),1)
        self.assertGreaterEqual(e["later"][0][1],int(
            datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000))
    def test_cost_stress_not_more_profitable_flat(self):
        x=bars()
        f={s:[dict(a) for a in x] for s in PAIRS}
        self.assertEqual(replay([(f,0)],RULES[0],STRESS)["pnl_eur"],0)
if __name__=="__main__":unittest.main()
