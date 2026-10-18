"""Pure offline tests for a free US EOD provider; no API token and no HTTP."""
import io
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from dataclasses import replace
from unittest.mock import patch
from urllib.error import HTTPError

from swingbot.massive_free import (
    FreeMarketFeedUnavailable, WATCHLIST_USD, MIN_CALL_GAP_SEC,
    parse_massive_daily, private_us_research_score, check_free_feed,
    fetch_massive_us_daily,
)


AS_OF = date(2026, 10, 18)


def sample(ticker="AAPL", count=240, adjusted=True, start=date(2025, 12, 1)):
    records = []
    for i in range(count):
        d = start + timedelta(days=i)
        # In the tests, synthetic dates are observations, not actual market days.
        # Compute prices and dates only to check the parser and score contract.
        close = 100 + i*.15 + (5 if i==count-1 else 0)
        ts = int(datetime(d.year,d.month,d.day,tzinfo=timezone.utc).timestamp()*1000)
        records.append({"t":ts,"o":close-1,"h":close+1,"l":close-2,
                        "c":close,"v":1500000})
    return {"ticker":ticker,"adjusted":adjusted,"status":"OK",
            "queryCount":count,"resultsCount":count,"results":records}


class MassiveFreeTests(unittest.TestCase):
    def test_valid_completed_us_candles_research_only(self):
        as_of=date(2026, 7, 30)
        feed=parse_massive_daily(sample(),ticker="AAPL",as_of=as_of)
        self.assertEqual(feed.currency,"USD")
        self.assertEqual(len(feed.bars),240)
        self.assertFalse(feed.paper_trade_authorized)
        r=private_us_research_score(feed,as_of=as_of)
        self.assertEqual(r["symbol"],"AAPL")
        self.assertEqual(r["research_status"],"WATCHLIST_ONLY_NO_BROKER_OR_FX_VERIFICATION")
        self.assertFalse(r["paper_trade_authorized"])
        self.assertFalse(r["real_order_authorized"])
        self.assertIn(r["score"],range(101))

    def test_wrong_ticker_or_no_adjustment_fail(self):
        as_of=date(2026,7,30)
        with self.assertRaises(FreeMarketFeedUnavailable):
            parse_massive_daily(sample(),ticker="AMZN",as_of=as_of)
        with self.assertRaises(FreeMarketFeedUnavailable):
            parse_massive_daily(sample(adjusted=False),ticker="AAPL",as_of=as_of)

    def test_reject_duplicates_and_short_or_stale(self):
        as_of=date(2026,7,30)
        d=sample()
        d["results"][-1]["t"]=d["results"][-2]["t"]
        with self.assertRaises(FreeMarketFeedUnavailable):
            parse_massive_daily(d,ticker="AAPL",as_of=as_of)
        with self.assertRaises(FreeMarketFeedUnavailable):
            parse_massive_daily(sample(count=75),ticker="AAPL",as_of=as_of)
        with self.assertRaises(FreeMarketFeedUnavailable):
            parse_massive_daily(sample(),ticker="AAPL",as_of=date(2026,8,20))

    def test_future_or_current_date_excluded(self):
        as_of=date(2026,7,30)
        d=sample()
        # New next-day candle must not affect historical research
        d["results"].append({
            "t":int(datetime(2026,7,30,tzinfo=timezone.utc).timestamp()*1000),
            "o":999,"h":1001,"l":998,"c":1000,"v":1200000
        })
        feed=parse_massive_daily(d,ticker="AAPL",as_of=as_of)
        self.assertEqual(len(feed.bars),240)
        self.assertLess(feed.bars[-1].day,as_of)

    def test_free_api_key_missing_causes_zero_requests(self):
        with patch.dict("os.environ",{},clear=True):
            result=check_free_feed(today=AS_OF,sleep=lambda _:None)
        self.assertEqual(result["status"],"AWAITING_MASSIVE_FREE_API_KEY")
        self.assertEqual(result["attempted"],0)
        self.assertFalse(result["trades_enabled"])

    def test_http_error_sanitized_and_header_bearer(self):
        err=HTTPError("https://api.massive.com/endpoint",401,
                      "Unauthorized",None,None)
        with patch("swingbot.massive_free.urllib.request.urlopen",side_effect=err) as mocked:
            with self.assertRaises(FreeMarketFeedUnavailable) as ctx:
                fetch_massive_us_daily("AAPL",api_key="PRIVATE_KEY_XYZ",as_of=AS_OF)
        req=mocked.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"),"Bearer PRIVATE_KEY_XYZ")
        self.assertNotIn("PRIVATE_KEY",req.full_url)
        self.assertNotIn("PRIVATE_KEY",str(ctx.exception))

    def test_pacing_and_aggregate_without_price_or_symbols(self):
        calls=[]
        sleep=[]
        feed=parse_massive_daily(sample(),ticker="AAPL",as_of=date(2026,7,30))
        with patch("swingbot.massive_free.fetch_massive_us_daily",
                   side_effect=lambda sym,**kwargs: calls.append(sym) or replace(feed,ticker=sym)):
            result=check_free_feed(api_key="PRIVATE_KEY_XYZ",
                                   today=date(2026,7,30),
                                   sleep=sleep.append,
                                   symbols=("AAPL","MSFT","JPM"))
        self.assertEqual(calls,["AAPL","MSFT","JPM"])
        self.assertEqual(sleep,[MIN_CALL_GAP_SEC]*2)
        self.assertEqual(result["attempted"],3)
        self.assertEqual(result["validated"],3)
        self.assertNotIn("AAPL",json.dumps(result))
        self.assertNotIn("PRIVATE_KEY",json.dumps(result))
        self.assertFalse(result["trades_enabled"])


if __name__=="__main__":
    unittest.main()
