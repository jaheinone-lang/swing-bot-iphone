"""Mock-only checks of Alpaca Basic IEX read-only US historical feed.

No credential is embedded here, and no HTTP request is made during tests.
Fixtures are NOT actual quotes, tradable signals or performance forecasts.
"""
import json
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError

from swingbot.alpaca_iex import (
    AlpacaUnavailable, fetch_iex_bars, parse_iex_pages,
    preliminary_iex_score, private_iex_50_scan,
)
from swingbot.us_watchlist import US_WATCHLIST_50


def fixture(symbol="AAPL", count=305, first=date(2025, 1, 2)):
    items=[]
    for k in range(count):
        d=first+timedelta(days=k)
        close=100+k*0.12
        items.append({
            "t":d.isoformat()+"T05:00:00Z",
            "o":close-0.3,"h":close+1,"l":close-1.4,
            "c":close,"v":1800000
        })
    return {"bars":items,"symbol":symbol,"next_page_token":None}


class FakeHTTP:
    def __init__(self, payload):
        self.payload=payload
    def __enter__(self):
        return self
    def __exit__(self,*exc):
        return False
    def read(self,n):
        return json.dumps(self.payload).encode()


class AlpacaTests(unittest.TestCase):
    def test_mock_free_iex_response(self):
        as_of=date(2025,11,6)
        feed=parse_iex_pages([fixture()],symbol="AAPL",as_of=as_of)
        self.assertEqual(feed.currency,"USD")
        self.assertEqual(feed.source,"ALPACA_BASIC_IEX_ONLY_NOT_CONSOLIDATED")
        self.assertEqual(len(feed.bars),305)
        score=preliminary_iex_score(feed,as_of=as_of)
        self.assertEqual(score["coverage"],"IEX_ONLY_PARTIAL_US_MARKET")
        self.assertFalse(score["consolidated_volume_verified"])
        self.assertFalse(score["live_order_authorized"])

    def test_no_permission_means_no_api_requests_or_trades(self):
        calls=[]
        def unsafe_loader(*args,**kwargs):
            calls.append(args)
            raise AssertionError("must not call provider")
        result=private_iex_50_scan(loader=unsafe_loader)
        self.assertEqual(result["attempted"],0)
        self.assertEqual(calls,[])
        self.assertEqual(result["status"],"AWAITING_ALPACA_PERSONAL_DATA_USE_CONFIRMATION")

    def test_fetch_uses_market_data_get_with_header_secrets(self):
        as_of=date(2025,11,6)
        calls=[]
        def fake_urlopen(request, timeout):
            calls.append(request)
            return FakeHTTP(fixture())
        feed=fetch_iex_bars("AAPL",key_id="PAPER_KEY_X",
                            secret_key="PAPER_SECRET_X",as_of=as_of,
                            urlopen=fake_urlopen)
        self.assertEqual(feed.ticker,"AAPL")
        self.assertEqual(len(calls),1)
        req=calls[0]
        self.assertTrue(req.full_url.startswith("https://data.alpaca.markets/v2/stocks/AAPL/bars?"))
        self.assertIn("feed=iex",req.full_url)
        self.assertIn("adjustment=split",req.full_url)
        self.assertEqual(req.get_header("Apca-api-key-id"),"PAPER_KEY_X")
        self.assertEqual(req.get_header("Apca-api-secret-key"),"PAPER_SECRET_X")
        self.assertNotIn("PAPER_SECRET",req.full_url)
        self.assertEqual(req.get_method(),"GET")

    def test_http_failure_redacts_credentials(self):
        fail=HTTPError("https://data.alpaca.markets/anything",403,
                       "Forbidden",None,None)
        with self.assertRaises(AlpacaUnavailable) as result:
            fetch_iex_bars("AAPL",key_id="MY_PRIVATE_KEY",
                           secret_key="MY_PRIVATE_SECRET",
                           as_of=date(2025,11,6),
                           urlopen=lambda *args,**kwargs: (_ for _ in ()).throw(fail))
        self.assertIn("403",str(result.exception))
        self.assertNotIn("MY_PRIVATE",str(result.exception))

    def test_duplicate_and_incomplete_pagination_fail_closed(self):
        today=date(2025,11,6)
        first=fixture()
        first["bars"][-1]["t"]=first["bars"][-2]["t"]
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages([first],symbol="AAPL",as_of=today)
        second=fixture()
        second["next_page_token"]="still-more"
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages([second],symbol="AAPL",as_of=today)

    def test_short_stale_and_foreign_stock_rejected(self):
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages([fixture(count=100)],symbol="AAPL",as_of=date(2025,11,6))
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages([fixture()],symbol="AAPL",as_of=date(2025,12,6))
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages([fixture()],symbol="OUTSIDE",as_of=date(2025,11,6))

    def test_no_symbol_or_quote_publication_from_scan(self):
        as_of=date(2025,11,6)
        x=parse_iex_pages([fixture()],symbol="AAPL",as_of=as_of)
        def loader(symbol,as_of):
            return replace(x,ticker=symbol)
        report=private_iex_50_scan(
            today=as_of,symbols=("AAPL","MSFT"),
            loader=loader,research_permission_confirmed=True)
        self.assertEqual(report["attempted"],2)
        self.assertEqual(report["verified"],2)
        self.assertEqual(report["top20_count"],2)
        self.assertFalse(report["price_data_redistributed"])
        self.assertFalse(report["eur_paper_portfolio_changed"])
        self.assertNotIn("AAPL",json.dumps(report))
        self.assertFalse(report["broker_orders_enabled"])


if __name__=="__main__":
    unittest.main()
