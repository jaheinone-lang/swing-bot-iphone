import unittest
from datetime import date,timedelta
from swingbot.equity_screen import DailyBar
from swingbot.us_stock_setup_research import scan,FAMILIES

def history(last=None):
    first=date(2025,1,1)
    rows=[]
    for i in range(220):
        p=10+i*.01
        rows.append(DailyBar(first+timedelta(days=i),p,p*1.01,p*.99,p,1_000_000))
    if last:
        v=rows[-1]
        rows[-1]=DailyBar(v.day,*last)
    return rows

class StockFocusTests(unittest.TestCase):
    def _scan(self,rows,**kw):
        return scan("FIXTURE",rows,as_of=date(2025,8,9),
            market_cap_usd=800_000_000,consolidated_volume=True,
            split_adjusted=True,verified_spread_bps=12,**kw)
    def test_smallcap_momentum_setup_is_watch_only(self):
        b=history((13.7,15.2,13.6,14.7,4_000_000))
        s=self._scan(b)
        self.assertTrue(s["family_signals"]["small_cap_momentum"])
        self.assertFalse(s["paper_order_authorized"])
        self.assertFalse(s["live_order_authorized"])
    def test_failed_gap_up_is_never_short_order(self):
        b=history((13.6,14.2,11.3,11.5,4_000_000))
        s=self._scan(b,borrow_locate_verified=True)
        self.assertTrue(s["family_signals"]["failed_gap_up"])
        self.assertFalse(s["short_order_authorized"])
    def test_no_consolidated_data_no_fake_liquidity(self):
        b=history()
        x=scan("FIXTURE",b,as_of=date(2025,8,9),
            market_cap_usd=800_000_000,consolidated_volume=False,
            split_adjusted=True,verified_spread_bps=12)
        self.assertEqual(x["status"],"REJECTED")
        self.assertFalse(any(x["family_signals"].values()))
    def test_missing_market_cap_no_setup(self):
        b=history()
        x=scan("FIXTURE",b,as_of=date(2025,8,9),
            market_cap_usd=None,consolidated_volume=True,
            split_adjusted=True,verified_spread_bps=12)
        self.assertEqual(x["status"],"REJECTED")
    def test_lookahead_no_completed_today(self):
        b=history()
        x=scan("FIXTURE",b,as_of=b[-1].day,
            market_cap_usd=800_000_000,consolidated_volume=True,
            split_adjusted=True,verified_spread_bps=12)
        self.assertEqual(x["status"],"REJECTED")
    def test_largecap_positive_gate(self):
        b=history((14.8,16.0,14.7,15.8,4_000_000))
        s=scan("FIXTURE",b,as_of=date(2025,8,9),
            market_cap_usd=20_000_000_000,consolidated_volume=True,
            split_adjusted=True,verified_spread_bps=12)
        self.assertTrue(s["family_signals"]["large_cap_breakout"])
        self.assertFalse(s["family_signals"]["small_cap_momentum"])
    def test_all_families_present(self):
        self.assertEqual(set(self._scan(history())["family_signals"]),set(FAMILIES))
if __name__=="__main__":unittest.main()
