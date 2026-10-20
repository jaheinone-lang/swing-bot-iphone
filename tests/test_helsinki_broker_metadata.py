import unittest
from swingbot.helsinki_broker_metadata import helsinki_broker_candidates

class HelsinkiBrokerTests(unittest.TestCase):
    def test_fi_isin_counts_do_not_claim_exchange_or_publish_tickers(self):
        rows=[
            {"type":"STOCK","ticker":"PRIVATE1","isin":"FI0009000681","currencyCode":"EUR"},
            {"type":"STOCK","ticker":"PRIVATE2","isin":"FI0009000681","currencyCode":"USD"},
            {"type":"STOCK","ticker":"PRIVATE2","isin":"FI0009000681","currencyCode":"USD"},
            {"type":"ETF","ticker":"FUND","isin":"FI0009000000","currencyCode":"EUR"},
            {"type":"STOCK","ticker":"US","isin":"US0009000000","currencyCode":"EUR"},
        ]
        r=helsinki_broker_candidates(rows)
        self.assertEqual(r["fi_isin_stock_instruments"],2)
        self.assertEqual(r["fi_isin_eur_quoted_instruments"],1)
        self.assertFalse(r["nasdaq_helsinki_venue_verified"])
        self.assertFalse(r["top10_ready"])
        self.assertFalse(r["orders_enabled"])
        self.assertNotIn("PRIVATE1",str(r))
