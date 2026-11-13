"""Return-target tests use only arithmetic and synthetic portfolios."""
import unittest
from datetime import date, timedelta

from swingbot.return_target import TARGET_ANNUAL_RETURN_PCT, goal_report
from swingbot.us_quality_cli import _synthetic_fixture
from swingbot.us_synthetic_lab import compare_abc_offline
from swingbot.us_cost_stress import run_us_cost_stress
from swingbot.strategy_lab import walkforward_research
from tests.test_strategy_lab import sample_data


class ReturnGoalTests(unittest.TestCase):
    def test_doubling_in_one_year_is_at_least_100_cagr(self):
        r=goal_report(initial_equity=5000,final_equity=10000,
                      start=date(2025,1,1),end=date(2026,1,1),
                      synthetic_or_unverified=False)
        self.assertEqual(r["target_annual_return_pct"],100.0)
        self.assertGreaterEqual(r["historical_annualized_return_pct"],100)
        self.assertTrue(r["target_met_on_this_sample"])
        self.assertEqual(r["evidence_status"],
                         "HISTORICAL_SAMPLE_ONLY_NOT_PREDICTION")
        self.assertFalse(r["sustainable_100pct_return_proven"])
        self.assertFalse(r["real_orders_authorized"])

    def test_short_anecdote_or_synthetic_never_proves_target(self):
        short=goal_report(initial_equity=5000,final_equity=7000,
                          start=date(2026,1,1),end=date(2026,2,1),
                          synthetic_or_unverified=False)
        self.assertTrue(short["target_met_on_this_sample"])
        self.assertEqual(short["evidence_status"],
                         "SHORT_WINDOW_ANNUALIZED_NOT_PROOF")
        synthetic=goal_report(initial_equity=5000,final_equity=10000,
                              start=date(2025,1,1),end=date(2026,1,1))
        self.assertEqual(synthetic["evidence_status"],
                         "UNVERIFIED_OR_SYNTHETIC_DATA_NOT_PROOF")

    def test_insufficient_balance_and_time_refused(self):
        for bad in (float("nan"),float("inf"),-1):
            with self.assertRaises(ValueError):
                goal_report(initial_equity=5000,final_equity=bad,
                            start=date(2025,1,1),end=date(2026,1,1))
        with self.assertRaises(ValueError):
            goal_report(initial_equity=5000,final_equity=10000,
                        start=date(2026,1,1),end=date(2025,1,1))

    def test_full_loss_is_not_false_success(self):
        r=goal_report(initial_equity=5000,final_equity=0,
                      start=date(2025,1,1),end=date(2026,1,1))
        self.assertEqual(r["historical_annualized_return_pct"],-100)
        self.assertFalse(r["target_met_on_this_sample"])

    def test_us_model_selects_train_return_not_drawdown_score(self):
        symbols=("AAPL","MSFT","JPM")
        histories={sym:_synthetic_fixture(sym,"V_SHOCK",offset=i*7)
                   for i,sym in enumerate(symbols)}
        as_of=next(iter(histories.values())).bars[-1].day+timedelta(days=1)
        report=compare_abc_offline(histories,as_of=as_of)
        expected=max(report["variants"],key=lambda v:(
            v["training"]["return_pct"],
            v["training"]["completed_round_trips"],
            v["strategy"]))["strategy"]
        self.assertEqual(report["training_selected_strategy"],expected)
        self.assertEqual(report["target_annual_return_pct"],100)
        self.assertIn("selected_holdout_annual_goal",report)
        self.assertFalse(report["selected_holdout_annual_goal"][
            "sustainable_100pct_return_proven"])
        stressed=run_us_cost_stress(histories,as_of=as_of)
        self.assertEqual(stressed["research_annual_return_target_pct"],100)
        self.assertEqual(stressed["selection_objective"],
                         "HIGHEST_TRAINING_RETURN_NO_DRAWDOWN_PENALTY")
        self.assertTrue(all("holdout_annual_goal" in row
                            for row in stressed["cost_cases"]))

    def test_eur_model_chooses_development_return(self):
        prices, markets = sample_data()
        report=walkforward_research(prices,markets)
        expected=max(report["variants"],key=lambda v:(
            v["development"]["total_return_pct"],
            v["name"]))["name"]
        self.assertEqual(report["training_selected_variant"],expected)
        self.assertEqual(report["target_annual_return_pct"],100)
        self.assertTrue(report["selection_rule"].startswith("highest"))
        self.assertFalse(report["auto_trading_changes"])
        self.assertFalse(report["holdout_annual_goal"][
            "sustainable_100pct_return_proven"])


if __name__=="__main__":
    unittest.main()
