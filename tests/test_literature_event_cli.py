"""No-order, consent-only Alpaca SIP event runner tests; mock transport."""
import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from swingbot.literature_event_cli import run_private_literature_patterns
from swingbot.us_watchlist import US_WATCHLIST_50
from swingbot.alpaca_iex import AlpacaUnavailable


def fake_study():
    return {
        "status":"EXPLORATORY_PRICE_PATTERN_EVENT_STUDY",
        "source":"ALPACA_DELAYED_SIP",
        "stocks_analyzed":50,
        "patterns":[],
        "annual_100pct_cagr_goal_proven":False,
        "real_orders_enabled":False,
    }


class LiteratureRunnerTests(unittest.TestCase):
    def test_requires_rights_no_provider_call_by_default(self):
        calls=[]
        def fail(*a,**kw):
            calls.append(1)
            raise AssertionError("No stock API allowed")
        result=run_private_literature_patterns(loader=fail)
        self.assertEqual(result["requested"],0)
        self.assertEqual(calls,[])
        self.assertFalse(result["study_executed"])

    def test_bad_history_window_does_not_read(self):
        for n in (0,1799,3001,True,"2555"):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    run_private_literature_patterns(
                        approved=True,lookback_days=n,
                        loader=lambda *a,**k: (_ for _ in ()).throw(
                            AssertionError("not allowed")))

    def test_51_complete_sip_histories_including_spy(self):
        seen=[]
        def loader(ticker,**kw):
            seen.append((ticker,kw))
            return SimpleNamespace(
                ticker=ticker,
                source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"
            )
        with patch("swingbot.literature_event_cli.study_pattern_events",
                   return_value=fake_study()) as study:
            result=run_private_literature_patterns(
                approved=True,as_of=date(2026,11,13),loader=loader)
        self.assertEqual(len(seen),51)
        self.assertEqual(len(set(t for t,_ in seen)),51)
        self.assertEqual([t for t,_ in seen].count("SPY"),1)
        self.assertEqual(result["validated_stock_histories"],50)
        self.assertTrue(result["spy_history_verified"])
        self.assertFalse(result["real_orders_enabled"])
        self.assertFalse(result["annual_100pct_cagr_goal_proven"])
        self.assertNotIn("AAPL",json.dumps(result))
        self.assertTrue(all(k["lookback_days"]==2555 for _,k in seen))
        spy=next(kwargs for ticker,kwargs in seen if ticker=="SPY")
        self.assertEqual(spy["allowed_symbols"],frozenset({"SPY"}))
        self.assertEqual(spy["feed"],"sip")
        study.assert_called_once()

    def test_any_missing_history_blocks_study_no_cherrypick(self):
        calls=[]
        def loader(ticker,**kw):
            calls.append(ticker)
            if ticker=="AAPL":
                raise AlpacaUnavailable("Alpaca IEX request HTTP 403")
            return SimpleNamespace(
                ticker=ticker,
                source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL")
        with patch("swingbot.literature_event_cli.study_pattern_events",
                   side_effect=AssertionError("Do not run partial history")):
            report=run_private_literature_patterns(
                approved=True,as_of=date(2026,11,13),loader=loader)
        self.assertEqual(report["status"],
                         "BLOCKED_INCOMPLETE_SIP_STOCK_OR_SPY_DATA")
        self.assertEqual(report["error_categories"],{"HTTP_403":1})
        self.assertFalse(report["study_executed"])
        self.assertFalse(report["orders_enabled"])
        self.assertNotIn("AAPL",json.dumps(report))
        self.assertLess(len(calls),51)


if __name__=="__main__":
    unittest.main()
