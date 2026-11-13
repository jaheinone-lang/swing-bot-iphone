"""Check frozen whole-account rules and chronological split integrity."""
import unittest
from datetime import datetime,timezone
from swingbot.positive_rules_5year import POLICIES,split_feeds,simulate
from swingbot.intraday_net_target import ExecutionCosts

STEP=300000
START=int(datetime(2023,12,30,tzinfo=timezone.utc).timestamp()*1000)

def synthetic(n=1200):
    return [{"timestamp_ms":START+i*STEP,"open":100.,"high":100.1,
             "low":99.9,"close":100.,"volume":100.} for i in range(n)]

class PositiveRulesTests(unittest.TestCase):
    def test_policy_grid(self):
        self.assertEqual(len(POLICIES),6)
        self.assertEqual(POLICIES[0],("reference_both",None,"morning_strict",1.5,1.))
        self.assertTrue(all(p[4]>=1 for p in POLICIES))
    def test_split_cannot_execute_before_2024_in_later_period(self):
        btc=synthetic();eth=[dict(v) for v in btc]
        feed={"BTC-EUR":btc,"ETH-EUR":eth}
        caches={s:{"morning_strict":set()} for s in feed}
        result=split_feeds([(feed,caches)])
        self.assertTrue(result["train"] and result["later"])
        threshold=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
        self.assertLess(result["train"][0][0]["BTC-EUR"][-1]["timestamp_ms"],threshold)
        # The later group may include lookback candles from 2023, but cannot
        # execute a signal there since first_entry_index=160.
        later=result["later"][0][0]["BTC-EUR"]
        self.assertGreaterEqual(later[160]["timestamp_ms"],threshold)
        for group in result.values():
            result_zero=simulate(group,POLICIES[0],ExecutionCosts())
            self.assertEqual(result_zero["trades"],0)
            self.assertEqual(result_zero["pnl_eur"],0)
    def test_symbol_restriction_and_no_sol(self):
        self.assertEqual({p[1] for p in POLICIES},{None,"BTC-EUR","ETH-EUR"})

if __name__=="__main__":
    unittest.main()
