"""Safety tests for crypto-only read-only historical research."""
import unittest
from datetime import date, timedelta

from swingbot.crypto_alpha_research import (
    CANDIDATES, MARKETS, SYMBOLS, aligned_crypto_data, analyse,
)
from swingbot.portfolio import Bar
from swingbot.crypto_validation import (
    WARMUP_BARS, contiguous_windows, hold_benchmarks, window_summary
)
from swingbot.strategy_lab import research_backtest


def synthetic_crypto(days=410):
    start = date(2024, 1, 1)
    data = {}
    for index, symbol in enumerate(SYMBOLS):
        bars = []
        for i in range(days):
            day = start + timedelta(days=i)
            # Uptrend, downturn and bounce, with modest periodic noise.
            trend = (100 + .35 * i) if i < 200 else (
                170 - .27 * (i - 200) if i < 310 else
                140.3 + .45 * (i - 310)
            )
            close = trend * (1 + (index - 1) * .0004 * i) + (i % 17) * .08
            bars.append(Bar(day, close, close * 1.02,
                            close * .98, close))
        data[symbol] = bars
    return data


class CryptoResearchTests(unittest.TestCase):
    def test_crypto_only_three_eur_pairs(self):
        self.assertEqual(set(MARKETS), set(SYMBOLS))
        self.assertTrue(all(market == "crypto" for market in MARKETS.values()))
        self.assertEqual(len(CANDIDATES), 3)

    def test_refuse_missing_or_gapped_pairs(self):
        data = synthetic_crypto()
        with self.assertRaises(ValueError):
            aligned_crypto_data({k: v for k, v in data.items()
                                 if k != "SOL-EUR"})
        data["BTC-EUR"].pop(200)
        with self.assertRaises(ValueError):
            aligned_crypto_data(data)

    def test_refuse_short_or_invalid_history(self):
        with self.assertRaises(ValueError):
            aligned_crypto_data(synthetic_crypto(290))
        data = synthetic_crypto()
        data["BTC-EUR"].append(data["BTC-EUR"][-1])
        with self.assertRaises(ValueError):
            aligned_crypto_data(data)

    def test_research_returns_training_selected_and_held_out_metrics(self):
        r = analyse(synthetic_crypto())
        self.assertEqual(r["mode"], "RESEARCH_ONLY_NO_ORDERS")
        self.assertEqual(r["calendar_days"], 410)
        self.assertEqual(len(r["candidates"]), 3)
        self.assertEqual(set(r["hold_benchmarks"]),
                         {"BTC only", "Equal BTC-ETH-SOL"})
        self.assertEqual(
            r["hold_benchmarks"]["BTC only"]["warmup_bars"], WARMUP_BARS)
        self.assertTrue(
            all(b["invest_after"] == r["hold_benchmarks"]["BTC only"]["invest_after"]
                for b in r["hold_benchmarks"].values()))
        winner = max(r["candidates"], key=lambda x: (
            x["training_score"], x["name"]))
        self.assertEqual(r["winner_on_training"], winner["name"])
        self.assertEqual(r["later_result_of_selected"],
                         winner["later_period"])
        for row in r["candidates"]:
            self.assertGreater(row["full_period_after_tax_eur"], 0)
            self.assertGreater(row["fee_stress_after_tax_eur"], 0)
            self.assertIn("max_drawdown_pct", row["later_period"])
            self.assertIn("max_drawdown_pct", row["development"])
            self.assertGreater(row["risk_cap_3pct_after_tax_eur"], 0)
            self.assertGreaterEqual(
                row["risk_cap_3pct_max_drawdown_pct"], 0)
            self.assertGreaterEqual(
                row["nonoverlapping_90d_windows"]["windows_count"], 1)

    def test_no_future_data_leak_into_earlier_equity_on_extension(self):
        data = synthetic_crypto()
        prefix = {k: v[:350] for k, v in data.items()}
        earlier = research_backtest(prefix, MARKETS, CANDIDATES[1])
        later = research_backtest(data, MARKETS, CANDIDATES[1])
        self.assertEqual(earlier["daily_curve"], later["daily_curve"][:350])


    def test_invalid_portfolio_risk_limits_fail_closed(self):
        d = synthetic_crypto()
        for bad in (-0.01, 0.0, 1.01, float("nan")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    research_backtest(
                        d, MARKETS, CANDIDATES[1],
                        portfolio_risk_limit_fraction=bad
                    )

    def test_nonoverlapping_windows_and_no_partial_window(self):
        d = synthetic_crypto()
        r = research_backtest(d, MARKETS, CANDIDATES[1])
        windows = contiguous_windows(
            r["daily_curve"], begin_day=d["BTC-EUR"][WARMUP_BARS].day.isoformat()
        )
        self.assertGreaterEqual(len(windows), 2)
        self.assertEqual(
            sum((__import__("datetime").date.fromisoformat(w["end"])
                 - __import__("datetime").date.fromisoformat(w["start"])).days
                for w in windows),
            90 * len(windows),
        )
        self.assertTrue(
            all(x["end"] == y["start"] for x, y in zip(windows, windows[1:]))
        )
        summary = window_summary(windows)
        self.assertEqual(summary["windows_count"], len(windows))
        self.assertLessEqual(summary["losing_windows"], len(windows))
        with self.assertRaises(ValueError):
            window_summary([])

    def test_benchmarks_are_read_only_and_identical_start(self):
        d = synthetic_crypto()
        before = [x.close for x in d["BTC-EUR"]]
        controls = hold_benchmarks(
            d, MARKETS, 5000., d["BTC-EUR"][280].day.isoformat()
        )
        self.assertEqual([x.close for x in d["BTC-EUR"]], before)
        self.assertEqual(
            controls["BTC only"]["invest_after"],
            controls["Equal BTC-ETH-SOL"]["invest_after"],
        )
        self.assertGreater(controls["BTC only"]["final_equity_eur"], 0)


if __name__ == "__main__":
    unittest.main()
