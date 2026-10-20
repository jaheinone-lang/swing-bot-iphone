"""Offline tests of EU-27 exchange/currency and Trading 212 metadata guards."""
import unittest

from swingbot.eu_watchlist import (
    EU27, EU_WATCHLIST_50, EU_BY_SYMBOL, eu_isin_prefix_counts,
    eu_research_readiness,
)


class EUWatchlistTests(unittest.TestCase):
    def test_50_unique_eu27_listings_and_currencies(self):
        self.assertEqual(len(EU_WATCHLIST_50), 50)
        self.assertEqual(len(EU_BY_SYMBOL), 50)
        self.assertTrue(all(row.country in EU27 for row in EU_WATCHLIST_50))
        self.assertTrue(all(row.currency in {"EUR", "DKK", "SEK"}
                            for row in EU_WATCHLIST_50))
        self.assertFalse(any(row.country in {"GB", "CH", "NO"}
                             for row in EU_WATCHLIST_50))

    def test_scandinavian_quotes_not_implicitly_eur(self):
        self.assertEqual(EU_BY_SYMBOL["NOVO-B.CO"].currency, "DKK")
        self.assertEqual(EU_BY_SYMBOL["VOLV-B.ST"].currency, "SEK")
        self.assertEqual(EU_BY_SYMBOL["SAP.DE"].currency, "EUR")
        report = eu_research_readiness()
        self.assertEqual(report["curated_listings"], 50)
        self.assertEqual(report["fx_history_required_for"], ["DKK", "SEK"])
        self.assertEqual(report["broker_matches_verified"], 0)
        self.assertFalse(report["eu_abc_backtest_ready"])
        self.assertFalse(report["orders_enabled"])

    def test_eu_isin_prefix_counts_are_not_issuer_domicile_claims(self):
        records = [
            {"ticker": "EX1", "type": "STOCK", "currencyCode": "EUR",
             "isin": "DE0000000001"},
            {"ticker": "EX2", "type": "STOCK", "currencyCode": "SEK",
             "isin": "SE0000000001"},
            {"ticker": "EX3", "type": "STOCK", "currencyCode": "USD",
             "isin": "US0000000001"},
            {"ticker": "EX4", "type": "ETF", "currencyCode": "EUR",
             "isin": "FR0000000001"},
            {"ticker": "EX5", "type": "STOCK", "currencyCode": "EUR",
             "isin": "BAD"},
            {"ticker": "EX1", "type": "STOCK", "currencyCode": "EUR",
             "isin": "DE0000000001"},  # duplicate exact instrument
        ]
        result = eu_isin_prefix_counts(records)
        self.assertEqual(result["stocks_with_eu_isin_prefix"], 2)
        self.assertEqual(result["eur_quoted_eu_isin_prefix_stocks"], 1)
        self.assertEqual(result["by_isin_prefix"], {"DE": 1, "SE": 1})
        self.assertEqual(result["by_quote_currency"], {"EUR": 1, "SEK": 1})
        self.assertFalse(result["eu_issuer_domicile_verified"])
        self.assertFalse(result["price_history_verified"])
        self.assertFalse(result["strategy_returns_computed"])
        self.assertFalse(result["real_or_paper_orders_enabled"])
        self.assertNotIn("EX1", str(result))

    def test_country_currency_not_mistaken_for_eu_identity(self):
        result = eu_isin_prefix_counts([
            {"ticker": "US_USD", "type": "STOCK", "currencyCode": "EUR",
             "isin": "US0000000001"},
            {"ticker": "IE_GBP", "type": "STOCK", "currencyCode": "GBP",
             "isin": "IE0000000001"},
            {"ticker": "GB_EUR", "type": "STOCK", "currencyCode": "EUR",
             "isin": "GB0000000001"},
        ])
        self.assertEqual(result["stocks_with_eu_isin_prefix"], 1)
        self.assertEqual(result["eur_quoted_eu_isin_prefix_stocks"], 0)
        self.assertEqual(result["by_quote_currency"], {"GBP": 1})


if __name__ == "__main__":
    unittest.main()
