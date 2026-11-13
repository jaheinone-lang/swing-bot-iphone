"""Offline-only tests for literature-driven price-pattern EVENT STUDY.

Synthetic source means no real return or strategy efficacy can be inferred.
No API key, order requests, provider data, or third-party quote distribution.
"""
import json
import unittest
from dataclasses import replace
from datetime import date,timedelta

from swingbot.equity_screen import DailyBar
from swingbot.massive_free import FreeMarketHistory
from swingbot.literature_event_study import (
    PATTERNS,LOOKBACK,MIN_EVENT_SAMPLE,
    pattern_flags,net_open_to_open_return,study_pattern_events
)


def bars_with_one_earnings_style_gap():
    start=date(2023,1,1)
    out=[]
    for k in range(500):
        base=100.0
        if k<300:
            o,h,l,c,v=100.,101.,99.,100.,1_000_000.
        elif k==300:
            o,h,l,c,v=112.,121.,111.,120.,5_000_000.
        else:
            o,h,l,c,v=121.,123.,119.,121.,1_000_000.
            if k==301:
                o,h,l,c=130.,133.,129.,131.
            if k==306:
                o,h,l,c=136.,139.,135.,137.
        out.append(DailyBar(start+timedelta(days=k),o,h,l,c,v))
    return tuple(out)


def as_feed(ticker="AAPL",bars=None,source="SYNTHETIC_TEST_FIXTURE"):
    return FreeMarketHistory(
        ticker,"USD",source,"SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",
        bars or bars_with_one_earnings_style_gap()
    )


class PatternSourceTests(unittest.TestCase):
    def test_predeclared_four_patterns(self):
        self.assertEqual(PATTERNS,(
            "52W_HIGH","LEADER_BASE_BREAK","GAP_VOLUME_PROXY",
            "90D_SMOOTH_TREND"
        ))

    def test_gap_proxy_requires_both_gap_and_volume(self):
        b=bars_with_one_earnings_style_gap()
        self.assertTrue(pattern_flags(b,300)["GAP_VOLUME_PROXY"])
        lowered=list(b)
        old=lowered[300]
        lowered[300]=replace(old,volume=1_000_000.)
        self.assertFalse(pattern_flags(tuple(lowered),300)["GAP_VOLUME_PROXY"])
        low_gap=list(b)
        low_gap[300]=DailyBar(old.day,105,121,104,120,5_000_000.)
        self.assertFalse(pattern_flags(tuple(low_gap),300)["GAP_VOLUME_PROXY"])

    def test_future_quotes_cannot_change_historical_signal(self):
        b=bars_with_one_earnings_style_gap()
        flags=pattern_flags(b,300)
        changed=list(b)
        for k in range(301,500):
            old=changed[k]
            changed[k]=DailyBar(old.day,199,201,195,200,2_000_000.)
        self.assertEqual(flags,pattern_flags(tuple(changed),300))

    def test_no_market_data_rights_blocks_real_and_mixed_feed(self):
        b=bars_with_one_earnings_style_gap()
        as_of=b[-1].day+timedelta(days=1)
        real=as_feed(source="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL")
        with self.assertRaises(PermissionError):
            study_pattern_events({"AAPL":real},as_of=as_of)
        synthetic=as_feed()
        with self.assertRaises(PermissionError):
            study_pattern_events({"AAPL":synthetic,"MSFT":replace(real,ticker="MSFT")},
                                 as_of=as_of,licensed_non_display_use=True)
        with self.assertRaises(PermissionError):
            study_pattern_events({"AAPL":synthetic},as_of=as_of,
                                 licensed_non_display_use=True)

    def test_gap_event_entry_next_open_and_next_open_exit(self):
        b=bars_with_one_earnings_style_gap()
        as_of=b[-1].day+timedelta(days=1)
        report=study_pattern_events({"AAPL":as_feed(bars=b)},as_of=as_of)
        gap=next(x for x in report["patterns"] if x["pattern"]=="GAP_VOLUME_PROXY")
        self.assertEqual(gap["signal_events"],1)
        five=next(x for x in gap["horizons"] if x["holding_sessions"]==5)
        self.assertEqual(five["events"],1)
        expect=round(net_open_to_open_return(b[301].open,b[306].open),3)
        self.assertEqual(five["mean_net_event_return_pct"],expect)
        self.assertFalse(report["annual_100pct_cagr_goal_proven"])
        self.assertFalse(report["real_orders_enabled"])
        self.assertTrue(report["event_returns_not_compounded_portfolio"])
        self.assertNotIn("AAPL",json.dumps(report))
        self.assertNotIn("120.0",json.dumps(gap))

    def test_spy_reference_requires_exact_entry_exit_dates(self):
        b=bars_with_one_earnings_style_gap()
        as_of=b[-1].day+timedelta(days=1)
        spy=[DailyBar(x.day,200.,201.,199.,200.,1_000_000.) for x in b]
        result=study_pattern_events(
            {"AAPL":as_feed(bars=b)},as_of=as_of,
            benchmark=as_feed(ticker="SPY",bars=tuple(spy)))
        gap=next(x for x in result["patterns"] if x["pattern"]=="GAP_VOLUME_PROXY")
        five=next(x for x in gap["horizons"] if x["holding_sessions"]==5)
        self.assertEqual(five["matched_spy_event_count"],1)
        self.assertEqual(five["unmatched_spy_events"],0)
        expected_ref=round(net_open_to_open_return(200.,200.),3)
        self.assertEqual(five["mean_spy_matched_return_pct"],expected_ref)
        self.assertEqual(
            five["mean_stock_excess_over_spy_pct_points"],
            round(five["mean_net_event_return_pct"]-expected_ref,3))
        with self.assertRaises(ValueError):
            study_pattern_events(
                {"AAPL":as_feed(bars=b)},as_of=as_of,
                benchmark=as_feed(ticker="AAPL",bars=tuple(spy)))

    def test_invalid_expensive_or_nonfinite_returns_rejected(self):
        for a,b,fee,slip in (
            (0,100,10,10), (100,float("nan"),10,10),
            (100,100,-1,10),(100,100,10,501),
        ):
            with self.subTest(a=a,b=b,fee=fee,slip=slip):
                with self.assertRaises(ValueError):
                    net_open_to_open_return(a,b,fees_bps=fee,slippage_bps=slip)
        self.assertLess(net_open_to_open_return(100,100),0)

    def test_not_enough_lookback_or_future_sessions_fails(self):
        b=bars_with_one_earnings_style_gap()[:LOOKBACK+20]
        with self.assertRaises(ValueError):
            study_pattern_events(
                {"AAPL":as_feed(bars=b)},as_of=b[-1].day+timedelta(days=1))

    def test_current_day_bar_is_always_ignored(self):
        b=bars_with_one_earnings_style_gap()
        as_of=b[-1].day+timedelta(days=1)
        normal=study_pattern_events({"AAPL":as_feed(bars=b)},as_of=as_of)
        new=DailyBar(as_of,1000,1001,999,1000,2_000_000)
        ignored=study_pattern_events(
            {"AAPL":as_feed(bars=b+(new,))},as_of=as_of)
        self.assertEqual(normal,ignored)


if __name__=="__main__":
    unittest.main()
