import unittest
from datetime import datetime,timezone
from swingbot.monthly_hold_research import simulate,study
from swingbot.daily_swing_research import DAY,PAIRS,STRESS

def bars(n=80,btc=100.,eth=200.):
    t=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()*1000)
    def make(p):
        return [{"timestamp_ms":t+i*DAY,"open":p,"high":p*1.01,
                 "low":p*.99,"close":p,"volume":10} for i in range(n)]
    return {"BTC-EUR":make(btc),"ETH-EUR":make(eth)}

class MonthlyHoldTests(unittest.TestCase):
    def test_cash_contributions_separate_from_pnl(self):
        f=bars()
        result=simulate([(f,0)])
        self.assertEqual(result["months_funded"],3)
        self.assertEqual(result["contributions_eur"],600.)
        self.assertLess(result["net_market_pnl_eur"],0)
        self.assertEqual(result["real_orders"],0)
        self.assertEqual(result["deposit_schedule"][0]["date"],"2026-01-01")
    def test_more_fees_cannot_improve_flat_price(self):
        f=bars()
        a=simulate([(f,0)])
        b=simulate([(f,0)],STRESS)
        self.assertLess(b["estimated_liquidation_eur"],a["estimated_liquidation_eur"])
        self.assertEqual(a["contributions_eur"],b["contributions_eur"])
    def test_zero_or_negative_deposit_rejected(self):
        f=bars()
        with self.assertRaises(ValueError):simulate([(f,0)],monthly=0)
        with self.assertRaises(ValueError):simulate([(f,0)],monthly=-200)
    def test_no_future_months_recorded(self):
        f=bars()
        a=simulate([(f,0)])
        f2={s:xs[:35] for s,xs in f.items()}
        b=simulate([(f2,0)])
        self.assertEqual(b["months_funded"],2)
        self.assertEqual(a["months_funded"],3)
if __name__=="__main__":unittest.main()
