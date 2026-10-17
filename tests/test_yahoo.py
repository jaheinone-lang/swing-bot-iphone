"""Yahoo unofficial source safety validation using mocked provider responses."""
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from swingbot.market_data import MarketDataError
from swingbot.yahoo_data import yahoo_eur_daily


def mock_payload(currency="EUR", days=83):
    start = date(2026, 7, 1)
    stamps, prices = [], {"open": [], "high": [], "low": [], "close": []}
    for idx in range(days):
        day = start + timedelta(days=idx)
        instant = datetime(day.year, day.month, day.day, 12,
                           tzinfo=ZoneInfo("Europe/Berlin"))
        stamps.append(int(instant.timestamp()))
        for key, val in (("open", 100), ("high", 102),
                         ("low", 98), ("close", 101)):
            prices[key].append(val)
    return {"chart": {"error": None, "result": [{
        "meta": {"currency": currency, "symbol": "SAP.DE"},
        "timestamp": stamps, "indicators": {"quote": [prices]}
    }]}}


class YahooTests(unittest.TestCase):
    def test_only_completed_euro_candles(self):
        with patch("swingbot.yahoo_data._yahoo_json",
                   return_value=mock_payload()):
            rows = yahoo_eur_daily("SAP.DE", today=date(2026, 9, 20))
        self.assertEqual(len(rows), 81)
        self.assertEqual(rows[-1].day, date(2026, 9, 19))

    def test_rejects_usd(self):
        with patch("swingbot.yahoo_data._yahoo_json",
                   return_value=mock_payload(currency="USD")):
            with self.assertRaises(MarketDataError):
                yahoo_eur_daily("SAP.DE", today=date(2026, 9, 20))

    def test_rejects_old_data(self):
        with patch("swingbot.yahoo_data._yahoo_json",
                   return_value=mock_payload()):
            with self.assertRaises(MarketDataError):
                yahoo_eur_daily("SAP.DE", today=date(2026, 10, 17))

    def test_only_approved_tickers(self):
        with self.assertRaises(MarketDataError):
            yahoo_eur_daily("AAPL")


if __name__ == "__main__":
    unittest.main()
