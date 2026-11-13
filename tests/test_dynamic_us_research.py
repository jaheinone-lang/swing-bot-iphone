"""Broad US screening safety tests. Synthetic price data, no HTTP."""
import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from swingbot.alpaca_iex import AlpacaUnavailable, parse_iex_pages, fetch_iex_bars
from swingbot.dynamic_us_research import private_wide_us_scan


def fixtures(symbol):
    first=date(2025,1,1)
    bars=[]
    for k in range(270):
        close=100+k*.20
        bars.append({
            "t":(first+timedelta(days=k)).isoformat()+"T04:00:00Z",
            "o":close-.5,"h":close+1.5,"l":close-2,
            "c":close,"v":2000000,
        })
    as_of=first+timedelta(days=270)
    return {"bars":bars,"next_page_token":None},as_of


def assets():
    return [
        {"source":"ALPACA_PAPER_ASSETS","asset_id":"one","symbol":"ZZZZ",
         "venue":"NASDAQ","broker_tradable_flag":True,"venue_country":"US"},
        {"source":"ALPACA_PAPER_ASSETS","asset_id":"two","symbol":"AAPL",
         "venue":"NYSE","broker_tradable_flag":True,"venue_country":"US"},
        {"source":"ALPACA_PAPER_ASSETS","asset_id":"three","symbol":"PINKY",
         "venue":"OTC","broker_tradable_flag":True,"venue_country":"US"},
        {"source":"ALPACA_PAPER_ASSETS","asset_id":"four","symbol":"HALTED",
         "venue":"NASDAQ","broker_tradable_flag":False,"venue_country":"US"},
    ]


class DynamicUSResearchTests(unittest.TestCase):
    def test_non50_ticker_requires_verified_allowlist(self):
        payload, as_of=fixtures("ZZZZ")
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages([payload],symbol="ZZZZ",as_of=as_of)
        outside=parse_iex_pages(
            [payload],symbol="ZZZZ",as_of=as_of,
            allowed_symbols=frozenset({"ZZZZ"}))
        self.assertEqual(outside.ticker,"ZZZZ")
        self.assertFalse(outside.paper_trade_authorized)
        with self.assertRaises(AlpacaUnavailable):
            parse_iex_pages(
                [payload],symbol="ZZZZ",as_of=as_of,
                allowed_symbols=frozenset({"AAPL"}))

    def test_fetch_dynamic_ticker_restricts_endpoint_and_method(self):
        payload, as_of=fixtures("ZZZZ")
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit): return json.dumps(payload).encode()
        request_log=[]
        def opener(req,timeout):
            request_log.append(req)
            return Response()
        with self.assertRaises(AlpacaUnavailable):
            fetch_iex_bars(
                "ZZZZ",key_id="X",secret_key="Y",
                as_of=as_of,urlopen=opener)
        self.assertEqual(request_log,[])
        result=fetch_iex_bars(
            "ZZZZ",key_id="X",secret_key="Y",
            as_of=as_of,urlopen=opener,
            allowed_symbols=frozenset({"ZZZZ"}))
        self.assertEqual(result.ticker,"ZZZZ")
        self.assertIn("/v2/stocks/ZZZZ/bars",request_log[0].full_url)
        self.assertEqual(request_log[0].get_method(),"GET")

    def test_no_research_rights_skips_all_api_calls(self):
        def fail(*args,**kwargs):
            raise AssertionError("No request should occur")
        with patch("swingbot.dynamic_us_research.fetch_alpaca_paper_assets",side_effect=fail):
            result=private_wide_us_scan(loader=fail)
        self.assertEqual(result["attempted"],0)
        self.assertFalse(result["asset_catalog_loaded"])
        self.assertFalse(result["paper_order_authorized"])

    def test_private_screen_over_all_provider_approved_symbols(self):
        payload, as_of=fixtures("ZZZZ")
        calls=[]
        def loader(symbol,**kwargs):
            calls.append(symbol)
            return parse_iex_pages([payload],symbol=symbol,
                as_of=kwargs["as_of"],feed=kwargs["feed"],
                allowed_symbols=kwargs["allowed_symbols"])
        report=private_wide_us_scan(
            inventory=assets(),as_of=as_of,batch_size=2,
            personal_research_data_rights_confirmed=True,
            loader=loader)
        self.assertEqual(set(calls),{"AAPL","ZZZZ"})
        self.assertEqual(report["attempted"],2)
        self.assertEqual(report["lit_venue_tradable_candidates"],2)
        self.assertEqual(report["qualified_ranks"],2)
        self.assertFalse(report["private_symbols_published"])
        self.assertFalse(report["annual_returns_proven"])
        self.assertFalse(report["broker_order_requests_made"])
        self.assertFalse(report["real_order_authorized"])
        self.assertNotIn("ZZZZ",json.dumps(report))

    def test_no_duplicate_active_broker_symbols_in_batch(self):
        duplicates=assets()
        duplicates[1]={**duplicates[1],"symbol":"ZZZZ"}
        with self.assertRaises(ValueError):
            private_wide_us_scan(
                inventory=duplicates,as_of=fixtures("ZZZZ")[1],
                personal_research_data_rights_confirmed=True,
                loader=lambda *a,**k: (_ for _ in ()).throw(AssertionError()))

    def test_bad_batches_and_feed_fail_before_api(self):
        for kwargs in ({"batch_size":0},{"batch_size":101},
                       {"batch_index":-1},{"feed":"invalid"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    private_wide_us_scan(
                        inventory=assets(),
                        personal_research_data_rights_confirmed=True,
                        **kwargs)


if __name__=="__main__":
    unittest.main()
