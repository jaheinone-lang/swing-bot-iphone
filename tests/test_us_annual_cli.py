"""Check manual multi-year SIP run is fail closed and has no symbol output."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import date

from swingbot.us_annual_cli import run_private_full_year_sip
from swingbot.us_watchlist import US_WATCHLIST_50
from swingbot.alpaca_iex import AlpacaUnavailable


def fake_report():
    return {
        "folds":[{
            "training_end":"2022-01-01",
            "holdout_start":"2022-01-04",
            "holdout_end":"2023-01-05",
            "holdout_calendar_days":366,
            "training_chosen_strategy":"A",
            "results":[{
                "case":"BASE",
                "holdout_return_pct":4.0,
                "holdout_cagr_pct":3.98,
                "holdout_max_drawdown_pct":10.0,
                "closed_trades":25,
                "holdout_profit_factor":1.2,
                "reference_return_pct":8.0,
                "target_met_in_this_historical_fold":False,
            },{
                "case":"SEVERE",
                "holdout_return_pct":1.0,
                "holdout_cagr_pct":0.99,
            }]
        }],
        "cost_scenarios":[{"case":"BASE","illustrative_chained_oos_cagr_pct":3.98}]
    }


class AnnualCliTests(unittest.TestCase):
    def test_no_explicit_rights_no_network(self):
        calls=[]
        def dangerous(*a,**k):
            calls.append(1)
            raise AssertionError("No requests allowed")
        r=run_private_full_year_sip(loader=dangerous)
        self.assertEqual(r["status"],"NOT_RUN_NEEDS_PERSONAL_SIP_BACKTEST_APPROVAL")
        self.assertEqual(r["requested"],0)
        self.assertEqual(calls,[])
        self.assertFalse(r["orders_enabled"])

    def test_empty_or_invalid_window_fail_closed(self):
        for window in (1,1799,3001,True,"2555"):
            with self.subTest(window=window):
                with self.assertRaises(ValueError):
                    run_private_full_year_sip(
                        research_permission_confirmed=True,
                        lookback_days=window,
                        loader=lambda *a,**k: (_ for _ in ()).throw(
                            AssertionError("Must not request quotes")))
                
    def test_all_50_must_validate_no_unseen_success_pool(self):
        calls=[]
        def fetch(symbol,**kw):
            calls.append((symbol,kw))
            if symbol=="AAPL":
                raise AlpacaUnavailable("Alpaca IEX request HTTP 403")
            return SimpleNamespace(
                ticker=symbol,
                source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"
            )
        with patch("swingbot.us_annual_cli.full_year_walkforward",
                   side_effect=AssertionError("Incomplete feed should not backtest")):
            r=run_private_full_year_sip(
                research_permission_confirmed=True,
                loader=fetch,
                as_of=date(2026,11,13))
        self.assertEqual(r["status"],"BLOCKED_INCOMPLETE_SIP_INPUT")
        self.assertFalse(r["annual_comparison_performed"])
        self.assertEqual(r["error_categories"],{"HTTP_403":1})
        self.assertLess(len(calls),len(US_WATCHLIST_50))
        self.assertNotIn("AAPL",json.dumps(r))
        self.assertFalse(r["orders_enabled"])

    def test_success_only_aggregates_returns_after_full_50(self):
        calls=[]
        def fetch(symbol,**kw):
            calls.append((symbol,kw))
            return SimpleNamespace(
                ticker=symbol,
                source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"
            )
        with patch("swingbot.us_annual_cli.full_year_walkforward",
                   return_value=fake_report()) as runner:
            r=run_private_full_year_sip(
                research_permission_confirmed=True,
                loader=fetch,
                as_of=date(2026,11,13),lookback_days=2555)
        self.assertEqual(len(calls),50)
        self.assertEqual(len({x[0] for x in calls}),50)
        self.assertTrue(all(x[1]["feed"]=="sip" and
                            x[1]["lookback_days"]==2555 for x in calls))
        runner.assert_called_once()
        self.assertEqual(r["validated"],50)
        self.assertEqual(r["folds"][0]["test_return_after_base_friction_pct"],4)
        self.assertEqual(r["folds"][0]["test_excess_vs_reference_percentage_points"],-4)
        self.assertEqual(r["folds"][0]["test_theoretical_reference_return_pct"],8)
        self.assertEqual(r["status"],"HISTORICAL_SIP_FULL_YEAR_RESEARCH_ONLY")
        self.assertFalse(r["profit_goal_proven_repeatable"])
        self.assertFalse(r["orders_enabled"])
        self.assertNotIn("AAPL",json.dumps(r))
        self.assertNotIn("MSFT",json.dumps(r))


if __name__=="__main__":
    unittest.main()
