import unittest
from datetime import date, timedelta
from unittest.mock import patch

from swingbot.dashboard_report import build_snapshot
from swingbot.market_data import MarketDataError
from swingbot.portfolio import Bar


def fixture_prices():
    start = date(2025, 1, 1)
    result = []
    for i in range(75):
        close = 100 + i * 0.25
        result.append(Bar(start + timedelta(days=i),
                          close - 0.5, close + 2, close - 2, close))
    return result


class DashboardTests(unittest.TestCase):
    def test_all_feeds_produce_a_snapshot(self):
        with patch("swingbot.dashboard_report.bitvavo_eur_daily",
                   return_value=fixture_prices()), patch(
            "swingbot.dashboard_report.stooq_eur_daily",
            return_value=fixture_prices()
        ):
            report = build_snapshot()
        self.assertEqual(len(report["instruments"]), 4)
        self.assertTrue(all(x["status"] == "ok" for x in report["instruments"]))
        self.assertIsNotNone(report["portfolio_backtest"])
        self.assertEqual(report["mode"], "READ_ONLY_RESEARCH")
        self.assertEqual(report["initial_eur"], 5000.0)

    def test_failure_does_not_fabricate_portfolio_results(self):
        with patch("swingbot.dashboard_report.bitvavo_eur_daily",
                   return_value=fixture_prices()), patch(
            "swingbot.dashboard_report.stooq_eur_daily",
            side_effect=MarketDataError("API not available")
        ):
            report = build_snapshot()
        self.assertIsNone(report["portfolio_backtest"])
        stock = next(x for x in report["instruments"] if x["market"] == "stock")
        self.assertEqual(stock["signal"], "NO_DATA")
        self.assertNotIn("last_completed_close_eur", stock)


if __name__ == "__main__":
    unittest.main()
