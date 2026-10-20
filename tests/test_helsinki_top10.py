import unittest
from datetime import date
from swingbot.helsinki_top10 import rank_helsinki_top10

class HelsinkiTop10Tests(unittest.TestCase):
    def test_no_price_feeds_never_create_fake_ranking(self):
        data=rank_helsinki_top10(instruments=[],feeds={},as_of=date(2026,10,20))
        self.assertEqual(data["watchlist_size"],40)
        self.assertEqual(data["top_candidates"],[])
        self.assertEqual(data["ranking_status"],"AWAITING_LICENSED_PRICE_DATA")
        self.assertFalse(data["orders_enabled"])

    def test_raw_eod_or_wrong_exchange_never_passes(self):
        records=[{"ticker":"BROKER_NOKIA","type":"STOCK","currencyCode":"EUR",
                  "isin":"FI0009000681"}]
        source={"research_symbol":"NOKIA.HE","exchange":"XHEL",
                "quote_currency":"EUR",
                "source":"EODHD raw","candles":[],
                "adjusted_for_corporate_actions":False}
        output=rank_helsinki_top10(instruments=records,feeds={
            "BROKER_NOKIA":source,
            "UNKNOWN":dict(source,exchange="XETRA"),
        },as_of=date(2026,10,20))
        self.assertEqual(output["feed_matched"],0)
        self.assertEqual(output["unverified_feed_rejections"],2)
        self.assertEqual(output["top_candidates"],[])
        self.assertFalse(output["public_ticker_ranking_authorized"])
