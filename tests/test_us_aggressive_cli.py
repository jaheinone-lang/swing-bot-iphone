"""No-network checks for the experiment's read-only SIP orchestrator."""
import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from swingbot.us_aggressive_cli import run_aggressive_sip
from swingbot.us_watchlist import US_WATCHLIST_50
from swingbot.alpaca_iex import AlpacaUnavailable


def fake_result():
    return {
        "folds":[{
            "training_end":"2022-01-02",
            "test_start":"2022-01-03",
            "test_end":"2023-01-04",
            "selected_using_training_only":"D – 6kk momentum 3 osaketta",
            "winner_is_new_experimental_variant":True,
            "baseline_abc_training_winner":"A – perus",
            "baseline_abc_holdout_return_pct":3.5,
            "results":[{
                "case":"BASE","return_pct":9.2,"cagr_pct":9.1,
                "max_drawdown_pct":28.4,"worst_day_pct":-9.5,
                "total_order_events":35,"hit_100pct_this_year":False,
            },{
                "case":"SEVERE","return_pct":-2.0,"cagr_pct":-1.99,
            }],
        }],
        "prespecified_new_variants":["D – 6kk momentum 3 osaketta",
                                    "E – 3kk breakout 1 osake"],
        "scenarios":[{"case":"BASE","illustrative_chained_annual_pct":9.1}],
    }


class AggressiveCliTests(unittest.TestCase):
    def test_no_credentials_or_network_before_permission(self):
        calls=[]
        def loader(*a,**k):
            calls.append(1)
            raise AssertionError("must not use API")
        report=run_aggressive_sip(loader=loader)
        self.assertEqual(report["status"],
                         "NOT_RUN_WITHOUT_SIP_PERSONAL_RESEARCH_PERMISSION")
        self.assertEqual(calls,[])
        self.assertFalse(report["orders_enabled"])

    def test_full_50_required_before_any_backtest(self):
        calls=[]
        def loader(symbol,**kw):
            calls.append(symbol)
            if symbol=="AAPL":
                raise AlpacaUnavailable("Alpaca IEX request HTTP 403")
            return SimpleNamespace(
                ticker=symbol,
                source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL")
        with patch("swingbot.us_aggressive_cli.compare_aggressive_annual",
                   side_effect=AssertionError("must not backtest incomplete")):
            r=run_aggressive_sip(
                permission_confirmed=True,
                as_of=date(2026,11,13),loader=loader)
        self.assertEqual(r["status"],"INCOMPLETE_STOCK_HISTORY_NO_BACKTEST")
        self.assertLess(len(calls),len(US_WATCHLIST_50))
        self.assertEqual(r["failure_types"],{"HTTP_403":1})
        self.assertFalse(r["backtest_performed"])
        self.assertNotIn("AAPL",json.dumps(r))

    def test_success_public_log_contains_no_tickers_or_quotes(self):
        calls=[]
        def loader(symbol,**kw):
            calls.append((symbol,kw))
            return SimpleNamespace(
                ticker=symbol,
                source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL")
        with patch("swingbot.us_aggressive_cli.compare_aggressive_annual",
                   return_value=fake_result()) as runner:
            r=run_aggressive_sip(
                permission_confirmed=True,as_of=date(2026,11,13),
                lookback_days=2555,loader=loader)
        self.assertEqual(len(calls),50)
        self.assertTrue(all(c[1]["feed"]=="sip" and
                            c[1]["lookback_days"]==2555 for c in calls))
        runner.assert_called_once()
        self.assertEqual(r["validated"],50)
        self.assertEqual(r["folds"][0]["new_test_return_base_pct"],9.2)
        self.assertEqual(r["folds"][0]["baseline_abc_test_return_pct"],3.5)
        self.assertTrue(r["fresh_untouched_prospective_validation_missing"])
        self.assertFalse(r["orders_enabled"])
        self.assertNotIn("AAPL",json.dumps(r))
        self.assertNotIn("JPM",json.dumps(r))

    def test_invalid_lookback_rejected_without_network(self):
        calls=[]
        def loader(*args,**kwargs):
            calls.append(1)
        for value in (0,1799,3001,True,"2555"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    run_aggressive_sip(permission_confirmed=True,
                                       lookback_days=value,loader=loader)
        self.assertEqual(calls,[])


if __name__=="__main__":
    unittest.main()
