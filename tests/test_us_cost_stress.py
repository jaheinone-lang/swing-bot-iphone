"""Cost stress tests are fully offline and use manufactured stock bars."""
import unittest
from dataclasses import replace
from datetime import timedelta

from swingbot.us_quality_cli import _synthetic_fixture
from swingbot.us_synthetic_lab import compare_abc_offline
from swingbot.us_cost_stress import COST_CASES, run_us_cost_stress


def fixtures():
    histories = {
        ticker: _synthetic_fixture(ticker, "V_SHOCK", offset=i * 7)
        for i, ticker in enumerate(("AAPL", "MSFT", "JPM"))
    }
    as_of = next(iter(histories.values())).bars[-1].day + timedelta(days=1)
    return histories, as_of


class USCostStressTests(unittest.TestCase):
    def test_no_change_to_existing_default_backtest(self):
        histories, as_of = fixtures()
        old = compare_abc_offline(histories, as_of=as_of)
        explicit = compare_abc_offline(
            histories, as_of=as_of, fee_bps=10, slippage_bps=10
        )
        self.assertEqual(old, explicit)
        self.assertEqual(old["fee_bps_each_side"], 10)
        self.assertEqual(old["benchmark_holdout"]["slippage_bps_open"], 10)

    def test_bad_cost_inputs_fail_closed(self):
        histories, as_of = fixtures()
        for fee, slippage in (
            (-1, 10), (10, -1), (501, 10), (10, 501),
            (float("nan"), 10), (10, float("inf")), ("10", 10)
        ):
            with self.subTest(fee=fee, slippage=slippage):
                with self.assertRaises(ValueError):
                    compare_abc_offline(
                        histories, as_of=as_of,
                        fee_bps=fee, slippage_bps=slippage
                    )

    def test_fixed_train_selection_and_explicit_costs(self):
        histories, as_of = fixtures()
        report = run_us_cost_stress(histories, as_of=as_of)
        cases = report["cost_cases"]
        self.assertEqual(len(cases), len(COST_CASES))
        self.assertEqual(
            [row["case"] for row in cases],
            [name for name, _, _ in COST_CASES]
        )
        self.assertEqual(
            {row["frozen_strategy"] for row in cases},
            {report["frozen_strategy"]}
        )
        for row, (name, fee, slip) in zip(cases, COST_CASES):
            self.assertEqual(row["fee_bps_per_side"], fee)
            self.assertEqual(row["slippage_bps_per_side"], slip)
            self.assertFalse(row["holdout_reference_is_investable"])
        self.assertEqual(report["selected_using"], "BASE_TRAINING_ONLY")
        self.assertTrue(report["source_is_entirely_synthetic"])
        self.assertFalse(report["real_data_research_evidence"])
        self.assertFalse(report["strategy_outperformance_proven"])
        self.assertFalse(report["paper_order_authorized"])
        self.assertFalse(report["real_order_authorized"])
        self.assertFalse(report["eur_paper_modified"])

    def test_unlicensed_market_data_stays_blocked(self):
        histories, as_of = fixtures()
        histories["AAPL"] = replace(histories["AAPL"], source="UNLICENSED_FEED")
        with self.assertRaises(PermissionError):
            run_us_cost_stress(histories, as_of=as_of)

    def test_empty_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            run_us_cost_stress({}, as_of=fixtures()[1])


if __name__ == "__main__":
    unittest.main()
