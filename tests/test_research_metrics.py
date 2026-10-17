"""Historical benchmark and risk reporting regression tests."""
import unittest
from datetime import date, timedelta
from math import isfinite

from swingbot.portfolio import Bar, backtest
from swingbot.research_metrics import _metrics, buy_and_hold_equal_weight, compare_to_hold


def candles(count=260):
    start = date(2025, 1, 1)
    stock = []
    crypto = []
    for day_no in range(count):
        day = start + timedelta(days=day_no)
        c = 100 + day_no * .11 + (5 if day_no % 47 > 39 else 0)
        if day.weekday() < 5:
            stock.append(Bar(day, c-.6, c+2, c-2, c))
        x = 100 + day_no * .14 + (3 if day_no % 23 > 19 else 0)
        crypto.append(Bar(day, x-.7, x+2, x-2, x))
    return {"STOCK": stock, "CRYPTO": crypto}, {
        "STOCK": "stock", "CRYPTO": "crypto"
    }


class RiskMetricsTests(unittest.TestCase):
    def test_flat_curve_has_zero_return_and_drawdown(self):
        rows = [{"day": (date(2025, 1, 1)+timedelta(days=i)).isoformat(),
                 "equity_eur": 5000} for i in range(100)]
        r = _metrics(rows)
        self.assertEqual(r["total_return_pct"], 0)
        self.assertEqual(r["max_drawdown_pct"], 0)
        self.assertEqual(r["annualized_volatility_pct"], 0)
        self.assertIsNone(r["sharpe_zero_cash_rate"])

    def test_falling_curve_reports_nonzero_drawdown(self):
        rows = [
            {"day": "2025-01-01", "equity_eur": 5000},
            {"day": "2025-01-02", "equity_eur": 5500},
            {"day": "2025-01-03", "equity_eur": 4400},
        ]
        r = _metrics(rows)
        self.assertEqual(r["max_drawdown_pct"], 20)
        self.assertEqual(r["total_return_pct"], -12)
        self.assertIsNone(r["cagr_pct"])

    def test_equal_weight_hold_does_not_rebalance_and_no_lookahead(self):
        data, markets = candles()
        hold = buy_and_hold_equal_weight(data, markets)
        self.assertEqual(hold["positions_bought"], 2)
        self.assertEqual(hold["expected_positions"], 2)
        self.assertEqual(hold["daily_curve"][0]["equity_eur"], 5000)
        self.assertTrue(all(x["day"] > hold["invest_after"]
                            for x in hold["fills"].values()))
        # Unused cash is possible because stock positions use whole shares
        self.assertGreater(hold["final_equity_eur"], 0)

    def test_same_day_range_and_risk_values(self):
        data, markets = candles()
        swing = backtest(data, markets)
        c = compare_to_hold(data, markets, swing)
        self.assertEqual(c["kind"], "RESEARCH_ONLY_HISTORICAL_SIMULATION")
        self.assertEqual(c["comparison_window"]["start"],
                         swing["daily_curve"][0]["day"])
        self.assertEqual(c["comparison_window"]["end"],
                         swing["daily_curve"][-1]["day"])
        self.assertEqual(c["swing"]["total_return_pct"],
                         swing["return_pct"])
        self.assertTrue(isfinite(c["buy_hold"]["max_drawdown_pct"]))
        self.assertIsNotNone(c["last_180_days"])
        self.assertTrue(c["benchmark_final_equity_eur"] > 0)

    def test_rejects_broken_curve_dates(self):
        with self.assertRaises(ValueError):
            _metrics([{"day": "2025-01-02", "equity_eur": 10},
                      {"day": "2025-01-01", "equity_eur": 11}])


if __name__ == "__main__":
    unittest.main()
