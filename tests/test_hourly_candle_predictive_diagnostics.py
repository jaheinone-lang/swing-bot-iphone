import unittest
from datetime import datetime,timezone
from swingbot.hourly_candle_predictive_diagnostics import (
    observations,research,summarize,HORIZONS)
from swingbot.hourly_candle_hypotheses import PATTERNS

def bars(n=800):
    t=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
    return [{"timestamp_ms":t+i*300000,
             "open":100+i*.001,"high":100.2+i*.001,
             "low":99.8+i*.001,"close":100+i*.001,
             "volume":1000} for i in range(n)]

class PredictiveDiagnosticTests(unittest.TestCase):
    def test_summarize_empty(self):
        self.assertEqual(summarize([])["n"],0)
    def test_horizons_no_gap_no_future_leakage(self):
        b=bars()
        feed={"BTC-EUR":b,"ETH-EUR":[dict(x) for x in b]}
        prepared=[(feed,{})]
        base,pattern=observations(prepared)
        self.assertTrue(len(base)>0)
        self.assertEqual(set(pattern),set(PATTERNS))
        for row in base:
            for h in row["horizons"]:
                self.assertIn(h,HORIZONS)
        out=research(prepared)
        self.assertEqual(len(out["patterns"]),len(PATTERNS))
        self.assertFalse(out["approved_live"])
    def test_zero_signals_cannot_produce_winning_pattern(self):
        b=bars()
        feed={"BTC-EUR":b,"ETH-EUR":[dict(x) for x in b]}
        out=research([(feed,{})])
        self.assertTrue(all(item["events"]==0 for item in out["patterns"]))
        self.assertTrue(all(all(bucket["raw_pct"]["signal"]["mean"] is None
            for bucket in item["horizons"].values()) for item in out["patterns"]))
if __name__=="__main__":unittest.main()
