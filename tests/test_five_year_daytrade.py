"""No-future, accurate five-year downloader and signal-cache regression."""
import json
import random
import unittest
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from swingbot.bitvavo_five_year import (
    BAR_MS, PAGE_BARS, PublicPacer, _five_minute_page)
from swingbot.daytrade_one_per_day import confirmed_upward_move
from swingbot.five_year_fast_signals import generate_frozen_signals
from swingbot.five_year_daytrade import align_segments,simulate,cached_segments
from swingbot.market_data import MarketDataError


def realistic_history(n=600):
    rng=random.Random(23548)
    clock=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
    close=1900.
    rows=[]
    for i in range(n):
        op=close
        move=.00052+rng.uniform(-.006,.007)
        close=op*(1+move)
        hi=max(close,op)*(1+rng.uniform(.0002,.002))
        lo=min(close,op)*(1-rng.uniform(.0002,.002))
        rows.append({
            "timestamp_ms":clock+i*BAR_MS,
            "open":op,"high":hi,"low":lo,"close":close,
            "volume":float(rng.randrange(100,25000))
        })
    return rows


class FiveYearDataTests(unittest.TestCase):
    def test_public_api_page_never_uses_orders_and_parses_ohlc(self):
        start=int(datetime(2024,3,3,tzinfo=timezone.utc).timestamp()*1000)
        def fake(url):
            self.assertIn("/BTC-EUR/candles?",url)
            q=parse_qs(urlparse(url).query)
            self.assertEqual(q["interval"],["5m"])
            self.assertEqual(q["limit"],[str(PAGE_BARS)])
            return json.dumps([
                [start, "100", "101", "99", "100", "23"],
                [start+BAR_MS,"100", "102", "98", "101", "25"]
            ])
        rows=_five_minute_page("BTC-EUR",start,start+2*BAR_MS,
                              fetch=fake,pacer=PublicPacer(spacing=0))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]["close"],101.)

    def test_malformed_timestamp_fails_closed(self):
        start=int(datetime(2024,3,3,tzinfo=timezone.utc).timestamp()*1000)
        with self.assertRaises(MarketDataError):
            _five_minute_page("ETH-EUR",start,start+BAR_MS,
                              fetch=lambda _:json.dumps([
                                  [start+3*BAR_MS,10,11,9,10,3]
                              ]))

    def test_fast_cache_matches_original_on_same_bars(self):
        data=realistic_history()
        calc=generate_frozen_signals(data)
        direct={i for i in range(160,len(data)-1)
                if (9<=datetime.fromtimestamp(
                    data[i+1]["timestamp_ms"]/1000,timezone.utc).hour+3<20)
                and confirmed_upward_move(data,i)}
        # The test dataset in September is EEST UTC+3, so direct local
        # hours are equivalent to UTC+3 for all bars.
        self.assertEqual(calc["confirmed_reference"],direct)
        self.assertTrue(calc["morning_strict"].issubset(
            calc["confirmed_morning"]))
        self.assertTrue(calc["confirmed_morning"].issubset(
            calc["confirmed_reference"]))
        self.assertTrue(all(i < len(data)-1 for i in
                            calc["confirmed_reference"]))

    def test_shared_one_trade_per_day_no_borrowing(self):
        b=realistic_history(650)
        e=[dict(x,close=x["close"]*1.1,open=x["open"]*1.1,
                high=x["high"]*1.1,low=x["low"]*1.1) for x in b]
        segments,count=align_segments({"BTC-EUR":b,"ETH-EUR":e})
        self.assertEqual(count,len(b))
        prep=cached_segments(segments)
        result=simulate(prep,"confirmed_reference")
        self.assertLessEqual(result["buys"],result["distinct_traded_fi_dates"])
        self.assertEqual(result["initial_eur"],5000)
        self.assertEqual(sum(x["trades"] for x in result["annual"].values()),
                         result["buys"])


if __name__=="__main__":
    unittest.main()
