"""Broad US/Europe catalog tests. Entirely offline, no credentials or orders."""
import json
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from swingbot.broad_market_catalog import (
    CatalogUnavailable, EUROPE_VENUES, _json_get,
    fetch_alpaca_paper_assets, fetch_eodhd_exchanges,
    fetch_eodhd_common_stocks, plan_batches, safe_counts,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload=json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,size):
        return self.payload[:size]


def fake_alpaca(url):
    rows=[
        {"id":"asset-01","symbol":"AAPL","class":"us_equity",
         "exchange":"NASDAQ","status":"active","tradable":True},
        {"id":"asset-02","symbol":"SPY","class":"us_equity",
         "exchange":"ARCA","status":"active","tradable":True},
        {"id":"asset-03","symbol":"CHEAP","class":"us_equity",
         "exchange":"OTC","status":"active","tradable":False},
        {"id":"asset-04","symbol":"CRYPTO","class":"crypto",
         "exchange":"CRYPTO","status":"active","tradable":True},
        {"id":"asset-05","symbol":"OLD","class":"us_equity",
         "exchange":"NASDAQ","status":"inactive","tradable":False},
    ]
    return FakeResponse(rows)


class BroadCatalogTests(unittest.TestCase):
    def test_alpaca_paper_all_assets_not_old_50_and_no_order(self):
        calls=[]
        def opener(request,timeout):
            calls.append(request)
            return fake_alpaca(request)
        rows=fetch_alpaca_paper_assets(
            api_key="SECRET_ID",api_secret="SECRET_KEY",opener=opener)
        self.assertEqual({r["symbol"] for r in rows},{"AAPL","SPY","CHEAP"})
        self.assertTrue(calls[0].full_url.startswith(
            "https://paper-api.alpaca.markets/v2/assets?"))
        self.assertEqual(calls[0].get_method(),"GET")
        self.assertEqual(
            parse_qs(urlsplit(calls[0].full_url).query)["status"],["active"])
        self.assertNotIn("SECRET",json.dumps(rows))
        self.assertFalse(any(x["real_order_authorized"] for x in rows))
        self.assertFalse(next(x for x in rows if x["symbol"]=="CHEAP")[
            "broker_tradable_flag"])
        self.assertEqual(safe_counts(rows)["listing_count"],3)

    def test_europe_exchanges_include_non_eu_and_exclude_us(self):
        directory=[
            {"Code":"US","CountryISO2":"US"},
            {"Code":"XETRA","CountryISO2":"DE"},
            {"Code":"LSE","CountryISO2":"UK"},
            {"Code":"OSL","CountryISO2":"NO"},
            {"Code":"SWX","CountryISO2":"CH"},
            {"Code":"EUFUND","CountryISO2":"XX"},
        ]
        captured=[]
        def opener(request,timeout):
            captured.append(request.full_url)
            return FakeResponse(directory)
        rows=fetch_eodhd_exchanges(api_token="PRIVATE_TOKEN",opener=opener)
        self.assertEqual({r["venue_country"] for r in rows},
                         {"DE","GB","NO","CH"})
        self.assertIn("GB",EUROPE_VENUES)
        self.assertIn("api_token=PRIVATE_TOKEN",captured[0])
        self.assertNotIn("PRIVATE_TOKEN",json.dumps(rows))

    def test_europe_common_stocks_only_and_delisted_separate(self):
        rows=[
            {"Code":"SAP","Type":"Common Stock","Currency":"EUR",
             "Isin":"DE0007164600"},
            {"Code":"DBK","Type":"Stock","Currency":"EUR"},
            {"Code":"FUND","Type":"ETF","Currency":"EUR"},
            {"Code":"BAD","Type":"Preferred Stock","Currency":"EUR"},
        ]
        calls=[]
        def opener(request,timeout):
            calls.append(request.full_url)
            return FakeResponse(rows)
        active=fetch_eodhd_common_stocks(
            "XETRA",venue_country="DE",api_token="TOKEN",opener=opener)
        self.assertEqual([x["symbol"] for x in active],["DBK","SAP"])
        self.assertTrue(all(x["listing_state"]=="ACTIVE_CATALOG"
                            for x in active))
        self.assertTrue(all(not x["broker_availability_verified"]
                            for x in active))
        hist=fetch_eodhd_common_stocks(
            "XETRA",venue_country="DE",api_token="TOKEN",
            include_delisted=True,opener=opener)
        self.assertTrue(all(x["listing_state"]=="DELISTED_HISTORY_ONLY"
                            for x in hist))
        self.assertEqual(parse_qs(urlsplit(calls[1]).query)["delisted"],["1"])
        self.assertNotIn("TOKEN",json.dumps(active))

    def test_batches_cover_every_listing_once_with_no_top50_limit(self):
        records=[
            {"source":"EODHD","exchange_code":"XETRA",
             "symbol":f"EQ{i:04d}","venue_country":"DE",
             "quote_currency":"EUR"} for i in range(1101)
        ]
        slices=[plan_batches(records,batch_size=200,batch_index=i)
                for i in range(6)]
        self.assertEqual([len(x["listings"]) for x in slices],
                         [200,200,200,200,200,101])
        self.assertEqual(slices[0]["batch_count"],6)
        flattened=[r["symbol"] for x in slices for r in x["listings"]]
        self.assertEqual(len(set(flattened)),len(records))
        self.assertFalse(slices[0]["paper_order_authorized"])
        self.assertEqual(plan_batches(records,batch_index=6)["listings"],[])

    def test_duplicate_listing_detected_and_invalid_indices_rejected(self):
        item={"source":"X","venue":"Y","symbol":"ABC"}
        with self.assertRaises(ValueError):
            plan_batches([item,item])
        with self.assertRaises(ValueError):
            plan_batches([item],batch_size=0)
        with self.assertRaises(ValueError):
            plan_batches([item],batch_index=-1)
        with self.assertRaises(ValueError):
            plan_batches([item],batch_index=True)

    def test_no_credentials_fail_closed(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(CatalogUnavailable):
                fetch_alpaca_paper_assets()
            with self.assertRaises(CatalogUnavailable):
                fetch_eodhd_exchanges()
            with self.assertRaises(CatalogUnavailable):
                fetch_eodhd_common_stocks("XETRA",venue_country="DE")

    def test_http_error_redacts_url_and_token(self):
        def bad(request,timeout):
            raise HTTPError(request.full_url,403,"Forbidden",{},None)
        with self.assertRaises(CatalogUnavailable) as ctx:
            fetch_eodhd_exchanges(api_token="DO_NOT_EXPOSE",opener=bad)
        self.assertIn("HTTP 403",str(ctx.exception))
        self.assertNotIn("DO_NOT_EXPOSE",str(ctx.exception))


if __name__=="__main__":
    unittest.main()
