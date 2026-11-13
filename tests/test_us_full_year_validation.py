"""Offline full-calendar-year USD walk-forward safety and arithmetic tests.

Artificial OHLCV only. No broker calls, provider tokens or licensed history.
"""
import json
import unittest
from dataclasses import replace
from datetime import timedelta, date
from urllib.parse import urlsplit, parse_qs

from swingbot.alpaca_iex import fetch_iex_bars, AlpacaUnavailable
from swingbot.us_full_year_validation import (
    full_year_walkforward, MIN_HOLDOUT_DAYS, TRAINING_SESSIONS,
)
from swingbot.us_cost_stress import COST_CASES
from swingbot.us_synthetic_lab import (
    _prepare, _simulation, SPECS, WARMUP,
)
from tests.test_us_synthetic_lab import synthetic


def prepared(n=1300):
    histories={ticker:synthetic(ticker,count=n) for ticker in ("AAPL","JPM")}
    as_of=next(iter(histories.values())).bars[-1].day+timedelta(days=1)
    return histories,as_of


class AnnualWalkforwardTests(unittest.TestCase):
    def test_two_independent_nonoverlapping_full_year_holdouts(self):
        histories,as_of=prepared()
        result=full_year_walkforward(histories,as_of=as_of)
        folds=result["folds"]
        self.assertEqual(len(folds),2)
        self.assertEqual(result["research_annual_cagr_target_pct"],100)
        self.assertEqual(result["rolling_training_sessions"],TRAINING_SESSIONS)
        self.assertTrue(result["holdout_folds_nonoverlapping"])
        for i,fold in enumerate(folds):
            with self.subTest(fold=i):
                self.assertGreaterEqual(fold["holdout_calendar_days"],MIN_HOLDOUT_DAYS)
                self.assertEqual(fold["training_sessions"],252)
                self.assertLess(fold["training_end"],fold["holdout_start"])
                self.assertEqual([row["case"] for row in fold["results"]],
                                 [x[0] for x in COST_CASES])
                self.assertEqual(len({row["case"] for row in fold["results"]}),3)
                self.assertTrue(all(not row["reference_is_investable"]
                                    for row in fold["results"]))
                self.assertTrue(all(row["annual_evidence_status"]==
                                    "UNVERIFIED_OR_SYNTHETIC_DATA_NOT_PROOF"
                                    for row in fold["results"]))
            if i:
                self.assertLess(folds[i-1]["holdout_end"],fold["holdout_start"])
        self.assertFalse(result["overall_100pct_repeatability_proven"])
        self.assertFalse(result["broker_orders_enabled"])
        self.assertFalse(result["paper_orders_enabled"])
        self.assertFalse(result["portfolio_modified"])
        self.assertFalse(result["no_licensed_per_symbol_prices_published"] is False)
        self.assertNotIn("AAPL",json.dumps(result))
        self.assertNotIn("JPM",json.dumps(result))

    def test_training_selected_no_holdout_or_worse_case_tuning(self):
        histories,as_of=prepared()
        result=full_year_walkforward(histories,as_of=as_of)
        dates,aligned=_prepare(histories,as_of=as_of,
                               licensed_non_display_use=False)
        for fold in result["folds"]:
            t0=dates.index(date.fromisoformat(fold["training_start"]))
            t1=dates.index(date.fromisoformat(fold["holdout_start"]))
            scores=[]
            for cfg in SPECS:
                train=_simulation(aligned,dates,cfg,t0,t1,fee_bps=10,slippage_bps=10)
                scores.append((cfg,train))
            expected=max(scores,key=lambda it:(
                it[1]["return_pct"],it[1]["completed_round_trips"],it[0].name
            ))[0].name
            self.assertEqual(fold["training_chosen_strategy"],expected)
            self.assertTrue(all(row["fee_bps_each_side"]>=10
                                for row in fold["results"]))

    def test_annualized_short_window_is_rejected(self):
        histories,as_of=prepared(800)
        with self.assertRaisesRegex(ValueError,"Insufficient completed market history"):
            full_year_walkforward(histories,as_of=as_of)

    def test_sources_must_be_homogeneous_and_sip_needs_permission(self):
        histories,as_of=prepared()
        histories["JPM"]=replace(histories["JPM"],source="UNLICENSED_DATA")
        with self.assertRaises(PermissionError):
            full_year_walkforward(histories,as_of=as_of)
        histories,as_of=prepared()
        histories["AAPL"]=replace(
            histories["AAPL"],source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"
        )
        with self.assertRaises(PermissionError):
            full_year_walkforward(histories,as_of=as_of)
        histories,as_of=prepared()
        with self.assertRaises(ValueError):
            full_year_walkforward(
                histories,as_of=as_of,licensed_non_display_use=True)

    def test_out_of_sample_results_ignore_future_bars(self):
        histories,as_of=prepared()
        report=full_year_walkforward(histories,as_of=as_of)
        extra=next(iter(histories.values())).bars[-1]
        next_day=as_of
        more={}
        for ticker,old in histories.items():
            last=old.bars[-1]
            after=replace(last,day=next_day,
                          close=last.close*1.03,
                          open=last.open*1.03,
                          high=last.high*1.03,
                          low=last.low*1.03)
            more[ticker]=replace(old,bars=old.bars+(after,))
        same=full_year_walkforward(more,as_of=as_of)
        self.assertEqual(report,same)


class HistoryWindowTests(unittest.TestCase):
    def test_extended_sip_request_preserves_get_and_adjustment(self):
        from tests.test_alpaca_iex import FakeHTTP,fixture
        as_of=date(2025,11,6)
        calls=[]
        def opener(req,timeout):
            calls.append(req)
            return FakeHTTP(fixture())
        for span in (850,2200,3000):
            r=fetch_iex_bars("AAPL",feed="sip",as_of=as_of,
                             key_id="PAPER_X",secret_key="PAPER_Y",
                             lookback_days=span,urlopen=opener)
            self.assertEqual(r.ticker,"AAPL")
            params=parse_qs(urlsplit(calls[-1].full_url).query)
            self.assertEqual(params["start"],
                             [(as_of-timedelta(days=span)).isoformat()])
            self.assertEqual(params["feed"],["sip"])
            self.assertEqual(params["adjustment"],["split"])
            self.assertEqual(calls[-1].get_method(),"GET")

    def test_invalid_history_window_fails_without_requests(self):
        called=[]
        def opener(*args,**kwargs):
            called.append(1)
            raise AssertionError("must not call")
        for span in (849,3001,-1,0,"2200",True):
            with self.subTest(span=span):
                with self.assertRaises(AlpacaUnavailable):
                    fetch_iex_bars("AAPL",key_id="X",secret_key="Y",
                                   lookback_days=span,urlopen=opener)
        self.assertEqual(called,[])


if __name__=="__main__":
    unittest.main()
