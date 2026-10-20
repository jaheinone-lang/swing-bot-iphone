import unittest
from swingbot.helsinki_watchlist import HELSINKI_40, summary

class HelsinkiTests(unittest.TestCase):
    def test_research_watchlist_not_trade_universe(self):
        self.assertEqual(len(HELSINKI_40),40)
        self.assertEqual(len({s for _,s in HELSINKI_40}),40)
        self.assertIn(("Nokia","NOKIA.HE"),HELSINKI_40)
        self.assertIn(("Elisa","ELISA.HE"),HELSINKI_40)
        self.assertTrue(all(sym.endswith(".HE") for _,sym in HELSINKI_40))
        s=summary()
        for field in ("active_listings_verified",
                      "trading212_membership_verified",
                      "eodhd_symbol_mapping_verified",
                      "historical_tradability_verified",
                      "orders_enabled"):
            self.assertFalse(s[field])
