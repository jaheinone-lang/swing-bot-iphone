"""Offline synthetic checks for full-cash-allocation momentum hypotheses.

No market requests, no keys and NO broker orders.
"""
import json
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from swingbot.us_synthetic_lab import _prepare, WARMUP
from swingbot.us_momentum_rotation import (
    ROTATION_SPECS,_rotation_choices,simulate_rotation
)
from swingbot.us_aggressive_annual import compare_aggressive_annual
from swingbot.us_full_year_validation import full_year_walkforward
from tests.test_us_full_year_validation import prepared
from swingbot.equity_screen import DailyBar


class RotationTests(unittest.TestCase):
    def test_no_open_price_leakage_to_signal(self):
        histories,as_of=prepared(n=800)
        days,aligned=_prepare(histories,as_of=as_of,
                              licensed_non_display_use=False)
        idx=WARMUP+5
        first=_rotation_choices(aligned,idx=idx,spec=ROTATION_SPECS[0])
        shocked={}
        for sym,rows in aligned.items():
            changed=list(rows)
            bar=changed[idx]
            changed[idx]=DailyBar(
                bar.day,bar.open*2,bar.high*2,bar.low*2,
                bar.close*2,bar.volume
            )
            shocked[sym]=tuple(changed)
        second=_rotation_choices(shocked,idx=idx,spec=ROTATION_SPECS[0])
        self.assertEqual(first,second)

    def test_stock_rotation_no_leverage_no_percentage_stop(self):
        histories,as_of=prepared(n=810)
        days,aligned=_prepare(histories,as_of=as_of,
                              licensed_non_display_use=False)
        for spec in ROTATION_SPECS:
            x=simulate_rotation(aligned,days,spec,WARMUP+2,WARMUP+220)
            self.assertTrue(x["long_only_no_leverage"])
            self.assertFalse(x["fixed_percent_stop_or_drawdown_circuit"])
            self.assertFalse(x["fractional_shares_assumed"])
            self.assertFalse(x["broker_orders_enabled"])
            self.assertGreaterEqual(x["estimated_fees_usd"],0)
            self.assertTrue(-100<=x["return_pct"]<1e12)
            self.assertTrue(0<=x["max_drawdown_pct"]<=100)
            self.assertEqual(x["order_event_count"],
                             x["buy_events"]+x["sell_events"])

    def test_bad_costs_and_unregistered_spec_fail(self):
        histories,as_of=prepared(n=800)
        days,aligned=_prepare(histories,as_of=as_of,
                              licensed_non_display_use=False)
        for invalid in (-1,501,float("nan"),"10"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    simulate_rotation(aligned,days,ROTATION_SPECS[0],
                                      WARMUP+2,WARMUP+60,fee_bps=invalid)
        with self.assertRaises(ValueError):
            simulate_rotation(aligned,days,ROTATION_SPECS[0],10,120)

    def test_independent_annual_folds_and_training_only_selection(self):
        histories,as_of=prepared()
        report=compare_aggressive_annual(histories,as_of=as_of)
        baseline=full_year_walkforward(histories,as_of=as_of)
        self.assertEqual(len(report["folds"]),len(baseline["folds"]))
        self.assertEqual(len(report["scenarios"]),3)
        self.assertEqual(len(report["prespecified_new_variants"]),2)
        for actual,old in zip(report["folds"],baseline["folds"]):
            self.assertGreaterEqual(actual["calendar_days"],365)
            self.assertEqual(actual["test_start"],old["holdout_start"])
            self.assertEqual(actual["test_end"],old["holdout_end"])
            self.assertEqual(actual["baseline_abc_training_winner"],
                             old["training_chosen_strategy"])
            self.assertEqual(actual["baseline_abc_holdout_return_pct"],
                             old["results"][0]["holdout_return_pct"])
            self.assertEqual(len(actual["results"]),3)
            self.assertTrue(all("max_drawdown_pct" in row
                                for row in actual["results"]))
        self.assertFalse(report["live_orders_enabled"])
        self.assertFalse(report["paper_orders_enabled"])
        self.assertTrue(report[
            "known_prior_exposure_to_baseline_holdout_periods"])
        self.assertTrue(report[
            "untouched_independent_validation_not_yet_available"])
        self.assertNotIn("AAPL",json.dumps(report))
        self.assertNotIn("JPM",json.dumps(report))

    def test_unlicensed_data_blocked(self):
        histories,as_of=prepared()
        histories["AAPL"]=replace(histories["AAPL"],source="UNKNOWN_FEED")
        with self.assertRaises(PermissionError):
            compare_aggressive_annual(histories,as_of=as_of)

    def test_insufficient_full_year_refused(self):
        histories,as_of=prepared(n=780)
        with self.assertRaises(ValueError):
            compare_aggressive_annual(histories,as_of=as_of)


if __name__=="__main__":
    unittest.main()
