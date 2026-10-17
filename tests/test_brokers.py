"""Mock public data and demonstration-only broker credentials."""
import base64
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from swingbot.bitvavo_data import bitvavo_eur_daily
from swingbot.market_data import MarketDataError
from swingbot.market_scan import scan
from swingbot.trading212_demo import demo_cash_balance, DemoCredentialsMissing


def candles():
    start = date(2025, 1, 1)
    rows = []
    for i in range(65):
        d = start + timedelta(days=i)
        stamp = int(datetime(d.year, d.month, d.day,
                             tzinfo=timezone.utc).timestamp() * 1000)
        rows.append([stamp, "100", "102", "98", "100", "3"])
    return json.dumps(list(reversed(rows)))


class PublicCryptoTests(unittest.TestCase):
    def test_bitvavo_completed_bars_sorted(self):
        with patch("swingbot.bitvavo_data._request_text", return_value=candles()):
            bars = bitvavo_eur_daily("BTC-EUR", today=date(2025, 3, 6))
        self.assertEqual(len(bars), 64)
        self.assertEqual(bars[0].day, date(2025, 1, 1))
        self.assertEqual(bars[-1].day, date(2025, 3, 5))

    def test_rejects_unsupported_pair(self):
        with self.assertRaises(MarketDataError):
            bitvavo_eur_daily("BTC-USD")

    def test_read_only_scan_outputs_signals_without_orders(self):
        with patch("swingbot.bitvavo_data._request_text", return_value=candles()):
            data = scan(crypto=True, stocks=False)
        self.assertEqual(data["mode"], "READ_ONLY_MARKET_SCAN")
        self.assertEqual(len(data["signals"]), 3)
        self.assertTrue(all(s["quote_currency"] == "EUR" for s in data["signals"]))


class Trading212SafetyTests(unittest.TestCase):
    def test_demo_keys_required(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(DemoCredentialsMissing):
                demo_cash_balance()

    def test_demo_connection_is_get_only_and_never_live(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, *_):
                return b'{"free":1000}'
        def fake_open(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertIn("demo.trading212.com", request.full_url)
            self.assertNotIn("live.trading212.com", request.full_url)
            expected = "Basic " + base64.b64encode(b"testkey:testsecret").decode()
            self.assertEqual(request.get_header("Authorization"), expected)
            return FakeResponse()
        with patch("swingbot.trading212_demo.urllib.request.urlopen",
                   side_effect=fake_open):
            value = demo_cash_balance(api_key="testkey", api_secret="testsecret")
        self.assertEqual(value["free"], 1000)


if __name__ == "__main__":
    unittest.main()
