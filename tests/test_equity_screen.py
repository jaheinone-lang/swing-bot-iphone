import unittest
from datetime import date,timedelta
from swingbot.equity_screen import DailyBar,screen_equity


def fixture(count=215, last_breakout=True, low_volume=False):
    first=date(2025,1,1)
    bars=[]
    for day in range(count):
        close=100+day*.25
        if day==count-1 and last_breakout:
            close+=15
        volume=100 if low_volume else 150000
        d=first+timedelta(days=day)
        bars.append(DailyBar(d,close-1,close+1,close-2,close,volume))
    return bars


class EquityGatesTests(unittest.TestCase):
    def test_valid_trending_eur_stock_passes_research_only(self):
        bars=fixture()
        x=screen_equity("TEST.DE","STOCK","EUR",bars,
                        as_of=bars[-1].day+timedelta(days=1),
                        adjusted_for_corporate_actions=True,
                        verified_spread_bps=8)
        self.assertEqual(x["status"],"SCREENED")
        self.assertEqual(x["signal"],"RESEARCH_CANDIDATE")
        self.assertFalse(x["paper_trade_authorized"])
        self.assertFalse(x["live_order_authorized"])

    def test_absent_price_adjustment_blocks_false_breakout(self):
        bars=fixture()
        r=screen_equity("TEST.DE","STOCK","EUR",bars,
                        as_of=bars[-1].day+timedelta(days=1),
                        adjusted_for_corporate_actions=False,
                        verified_spread_bps=5)
        self.assertEqual(r["signal"],"NO_DATA")

    def test_currency_spread_liquidity_rejection(self):
        bars=fixture()
        args=dict(ticker="ABC",asset_type="ETF",currency="EUR",candles=bars,
                  as_of=bars[-1].day+timedelta(days=1),
                  adjusted_for_corporate_actions=True,verified_spread_bps=5)
        self.assertEqual(screen_equity(**{**args,"currency":"USD"})["status"],"REJECTED")
        self.assertEqual(screen_equity(**{**args,"verified_spread_bps":None})["status"],"WATCH_ONLY_NO_EXECUTION")
        self.assertEqual(screen_equity(**{**args,"verified_spread_bps":60})["status"],"WATCH_ONLY_NO_EXECUTION")
        self.assertEqual(screen_equity(**{**args,"verified_spread_bps":None})["spread_status"],"UNKNOWN")
        self.assertEqual(screen_equity(**{**args,"candles":fixture(low_volume=True)})["status"],"REJECTED")

    def test_future_filing_does_not_boost(self):
        bars=fixture()
        report={
            "fundamentals_status":"PARTIAL","as_of":bars[-1].day.isoformat(),
            "revenue_filed":(bars[-1].day+timedelta(days=1)).isoformat(),
            "source_url":"https://data.sec.gov/api/xbrl/companyfacts/CIK0000123456.json",
            "points":55,
        }
        result=screen_equity("TEST.DE","STOCK","EUR",bars,
                             as_of=bars[-1].day+timedelta(days=1),
                             adjusted_for_corporate_actions=True,
                             verified_spread_bps=5,
                             sec_fundamentals=report)
        self.assertEqual(result["status"],"REJECTED")


if __name__=="__main__":
    unittest.main()
