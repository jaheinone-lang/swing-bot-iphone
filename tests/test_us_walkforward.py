"""Unit tests for expanding training-only selection across time."""
from dataclasses import replace
from datetime import date, timedelta
from math import sin
from unittest import TestCase
from unittest.mock import patch

from swingbot.equity_screen import DailyBar
from swingbot.massive_free import FreeMarketHistory
from swingbot.us_synthetic_lab import WARMUP
from swingbot.us_walkforward import walkforward_abc_offline, SIP_SOURCE


def fixture(symbol="AAPL", size=550):
    base=date(2025, 1, 1)
    bars=[]
    for i in range(size):
        p=105 + .14*i + 3*sin(i/13)
        openp=p*(1-.001*sin(i/2))
        bars.append(DailyBar(base+timedelta(days=i),openp,
                             max(p,openp)*1.018,
                             min(p,openp)*.982,p,2_000_000))
    return FreeMarketHistory(
        ticker=symbol,currency="USD",source="SYNTHETIC_TEST_FIXTURE",
        adjustment="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",bars=tuple(bars))


class WalkForwardTests(TestCase):
    def test_three_nonoverlapping_chronological_holdouts(self):
        h=fixture()
        r=walkforward_abc_offline({"AAPL":h},
                                  as_of=h.bars[-1].day+timedelta(days=1))
        self.assertEqual(len(r["folds"]),3)
        self.assertTrue(r["synthetic_only"])
        self.assertFalse(r["qualified_historical_comparison"])
        self.assertFalse(r["strategy_profitability_proven"])
        self.assertFalse(r["automatic_order_execution"])
        self.assertFalse(r["paper_order_execution"])
        self.assertFalse(r["eur_portfolio_modified"])
        first,second,third=r["folds"]
        self.assertLess(first["training_end"],first["holdout_start"])
        self.assertLess(first["holdout_end"],second["holdout_start"])
        self.assertLess(second["holdout_end"],third["holdout_start"])
        self.assertEqual(second["training_end"],first["holdout_end"])
        self.assertEqual(third["training_end"],second["holdout_end"])
        for fold in r["folds"]:
            self.assertEqual(set(fold["variants"]),{"A","B","C"})
            self.assertEqual(fold["holdout_sessions"],max(40,(550-WARMUP)//5))
            self.assertFalse(fold["qualified_historical_fold"])
            self.assertFalse(fold["reference_is_investable"])
            self.assertTrue(fold["cash_reset_between_folds"])

    def test_recent_future_bar_is_ignored(self):
        h=fixture()
        cutoff=h.bars[-1].day+timedelta(days=1)
        original=walkforward_abc_offline({"AAPL":h},as_of=cutoff)
        future=DailyBar(cutoff,500,550,450,525,10_000_000)
        result=walkforward_abc_offline(
            {"AAPL":replace(h,bars=h.bars+(future,))},as_of=cutoff)
        self.assertEqual(original,result)

    def test_unlicensed_real_feed_is_rejected(self):
        h=fixture()
        reals=replace(h,source=SIP_SOURCE)
        with self.assertRaises(PermissionError):
            walkforward_abc_offline(
                {"AAPL":reals},as_of=h.bars[-1].day+timedelta(days=1))

    def test_not_enough_periods_rejected(self):
        h=fixture(size=370)
        with self.assertRaisesRegex(ValueError,"200 tradable sessions"):
            walkforward_abc_offline(
                {"AAPL":h},as_of=h.bars[-1].day+timedelta(days=1))

    def test_mixed_sources_rejected_even_with_license_flag(self):
        a=fixture("AAPL")
        b=replace(fixture("MSFT"),source=SIP_SOURCE)
        with self.assertRaisesRegex(ValueError,"Mixed historical"):
            walkforward_abc_offline(
                {"AAPL":a,"MSFT":b},
                as_of=a.bars[-1].day+timedelta(days=1),
                licensed_non_display_use=True)

    def test_training_leader_is_not_reselected_from_holdout(self):
        h=fixture()
        def mocked(aligned,dates,cfg,start,end):
            # Deliberately make C an enormous HOLDOUT winner, while A wins
            # every training phase. The chosen symbol MUST remain A.
            names={"A – perus":0,"B – trendi":1,"C – aggressiivinen":2}
            idx=names[cfg.name]
            is_train=start==WARMUP
            return {
                "return_pct": ([12.0,6.0,1.0] if is_train
                               else [-4.0,-2.0,200.0])[idx],
                "max_drawdown_pct": 1.0,
                "completed_round_trips":20,
            }
        with patch("swingbot.us_walkforward._simulation",side_effect=mocked):
            result=walkforward_abc_offline(
                {"AAPL":h},as_of=h.bars[-1].day+timedelta(days=1))
        for fold in result["folds"]:
            self.assertEqual(fold["selected_from_training"],"A")
            self.assertEqual(fold["selected_holdout_return_pct"],-4.0)
            self.assertEqual(fold["variants"]["C"]["holdout"]["return_pct"],200.0)


if __name__=="__main__":
    import unittest
    unittest.main()
