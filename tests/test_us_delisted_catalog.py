"""US active+delisted common-stock directory source tests; offline only."""
import json
import unittest
from urllib.parse import parse_qs,urlsplit
from urllib.error import HTTPError
from unittest.mock import patch

from swingbot.broad_market_catalog import CatalogUnavailable
from swingbot.us_delisted_catalog import (
    fetch_eodhd_us_common_stocks,summarize_us_coverage
)


class Response:
    def __init__(self,obj):
        self.body=json.dumps(obj).encode("utf-8")
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.body[:n]


def fixture():
    return [
        {"Code":"AAPL","Exchange":"NASDAQ","Currency":"USD",
         "Type":"Common Stock","Isin":"US0378331005"},
        {"Code":"TEST","Exchange":"NYSE","Currency":"USD",
         "Type":"Common Stock","Isin":None},
        {"Code":"OTCSTOCK","Exchange":"PINK","Currency":"USD",
         "Type":"Common Stock","Isin":None},
        {"Code":"FAKE_ETF","Exchange":"NYSE","Currency":"USD",
         "Type":"ETF","Isin":None},
        {"Code":"GBPTEST","Exchange":"NYSE","Currency":"GBP",
         "Type":"Common Stock","Isin":None},
    ]


class USDelistedTests(unittest.TestCase):
    def test_get_active_and_delisted_in_two_independent_metadata_calls(self):
        requests=[]
        def opener(req,timeout):
            requests.append(req)
            return Response(fixture())
        active=fetch_eodhd_us_common_stocks(
            delisted=False,api_token="HIDDEN_TOKEN",opener=opener)
        delisted=fetch_eodhd_us_common_stocks(
            delisted=True,api_token="HIDDEN_TOKEN",opener=opener)
        self.assertEqual(len(requests),2)
        self.assertTrue(all(req.get_method()=="GET" for req in requests))
        self.assertEqual([parse_qs(urlsplit(req.full_url).query)["delisted"]
                          for req in requests],[["0"],["1"]])
        self.assertEqual([parse_qs(urlsplit(req.full_url).query)["type"]
                          for req in requests],[["common_stock"],["common_stock"]])
        self.assertEqual(len(active),2)
        self.assertEqual(len(delisted),2)
        self.assertTrue(all(row["kind"]=="COMMON_STOCK_SOURCE_LABEL"
                            for row in active))
        self.assertTrue(all(not row["real_order_authorized"] for row in active))
        report=summarize_us_coverage(active,delisted)
        self.assertEqual(report["active_major_exchange_common_stock_listings"],2)
        self.assertEqual(report["delisted_major_exchange_common_stock_listings"],2)
        self.assertEqual(report["symbols_appearing_in_both_statuses"],2)
        self.assertEqual(report["active_listing_counts_by_venue"],
                         {"NASDAQ":1,"NYSE":1})
        self.assertFalse(report["historical_point_in_time_membership_verified"])
        self.assertNotIn("HIDDEN_TOKEN",json.dumps(report))
        self.assertNotIn("AAPL",json.dumps(report))
        self.assertFalse(report["paper_orders_enabled"])

    def test_missing_token_fails_closed_before_network(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(CatalogUnavailable):
                fetch_eodhd_us_common_stocks(delisted=False)

    def test_duplicate_provenance_or_empty_source_rejected(self):
        with self.assertRaises(CatalogUnavailable):
            fetch_eodhd_us_common_stocks(
                delisted=False,api_token="X",
                opener=lambda req,timeout:Response(
                    [fixture()[0],fixture()[0]]))
        with self.assertRaises(CatalogUnavailable):
            fetch_eodhd_us_common_stocks(
                delisted=True,api_token="X",
                opener=lambda req,timeout:Response([]))
        with self.assertRaises(ValueError):
            fetch_eodhd_us_common_stocks(delisted=1,api_token="X")
        with self.assertRaises(ValueError):
            summarize_us_coverage([],[])

    def test_vendor_http_error_redacts_query_token(self):
        def opener(req,timeout):
            raise HTTPError(req.full_url,403,"Forbidden",{},None)
        with self.assertRaises(CatalogUnavailable) as err:
            fetch_eodhd_us_common_stocks(
                delisted=True,api_token="NEVER_PRINT_ME",opener=opener)
        self.assertNotIn("NEVER_PRINT_ME",str(err.exception))


if __name__=="__main__":
    unittest.main()
