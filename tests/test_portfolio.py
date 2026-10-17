import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from swingbot.market_data import MarketDataError, kraken_eur_daily, stooq_eur_daily
from swingbot.multi_cli import synthetic_dataset
from swingbot.portfolio import Bar, backtest


def stock_bars(extended=True):
    start = date(2025, 1, 1)
    prices = [100.] * 60 + [120.]
    if extended:
        prices += [121., 122.]
    bars = []
    for i, close in enumerate(prices):
        bars.append(Bar(start + timedelta(days=i),
                        close - 1, close + 2, close - 2, close))
    return bars


class PortfolioTests(unittest.TestCase):
    def test_signal_executes_next_day_not_signal_day(self):
        bars = stock_bars()
        symbol = "TEST_STOCK"
        before = backtest({symbol: bars[:61]}, {symbol: "stock"})
        self.assertEqual(before["trade_events"], [])
        self.assertIn(symbol, before["pending_signals"])
        after = backtest({symbol: bars[:62]}, {symbol: "stock"})
        buys = [e for e in after["trade_events"] if e["side"] == "BUY"]
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]["day"], bars[61].day.isoformat())
        self.assertLessEqual(buys[0]["quantity"] * buys[0]["price"], 1000.01)

    def test_cash_never_negative_due_to_fees(self):
        data, markets = synthetic_dataset()
        report = backtest(data, markets)
        self.assertIn("DEMO_EUR_STOCK", report["symbols"])
        self.assertIn("DEMO_BTCEUR", report["symbols"])
        self.assertEqual(report["mode"], "BACKTEST_ONLY_NO_REAL_ORDERS")
        self.assertGreaterEqual(report["estimated_fees_eur"], 0)

    def test_portfolio_halting_after_gap(self):
        start = date(2025, 1, 1)
        stock = stock_bars(extended=False)
        # 5 independent symbols can fill up to 20% each. Subsequent correlated
        # overnight gap shocks can exceed the 25% drawdown guard.
        series = []
        for b in stock:
            series.append(b)
        d61 = start + timedelta(days=61)
        d62 = start + timedelta(days=62)
        series.extend([
            Bar(d61, 121, 123, 119, 121),
            Bar(d62, 12, 14, 10, 12),
        ])
        keys = [f"ASSET{i}" for i in range(5)]
        result = backtest({k: series for k in keys},
                          {k: "crypto" for k in keys})
        self.assertTrue(result["halted_new_entries"])
        self.assertGreaterEqual(result["max_drawdown_pct"], 25)
        self.assertTrue(any(e["reason"] == "stop" for e in result["trade_events"]))

    def test_rejects_unordered_dates(self):
        b = stock_bars()
        with self.assertRaises(ValueError):
            backtest({"A": list(reversed(b))}, {"A": "stock"})


class ProviderParsingTests(unittest.TestCase):
    def test_stock_excludes_today_and_rejects_invalid(self):
        rows = ["Date,Open,High,Low,Close,Volume"]
        for n in range(64):
            d = date(2025, 1, 1) + timedelta(days=n)
            rows.append(f"{d},100,102,98,100,1000")
        with patch("swingbot.market_data._request_text", return_value="\n".join(rows)):
            bars = stooq_eur_daily("sap.de", today=date(2025, 3, 5))
        self.assertEqual(len(bars), 63)
        with self.assertRaises(MarketDataError):
            stooq_eur_daily("aapl.us")

    def test_kraken_always_drops_unfinished_last(self):
        base = date(2025, 1, 1)
        entries = []
        from datetime import datetime, timezone
        for n in range(65):
            day = base + timedelta(days=n)
            stamp = int(datetime(day.year, day.month, day.day,
                                 tzinfo=timezone.utc).timestamp())
            entries.append([stamp, "100", "102", "98", "100",
                            "100", "10", 1])
        payload = json.dumps({"error": [], "result": {
            "XXBTZEUR": entries, "last": 0
        }})
        with patch("swingbot.market_data._request_text", return_value=payload):
            bars = kraken_eur_daily("XBTEUR", today=date(2025, 4, 1))
        self.assertEqual(len(bars), 64)
        self.assertNotEqual(bars[-1].day, base + timedelta(days=64))


if __name__ == "__main__":
    unittest.main()
