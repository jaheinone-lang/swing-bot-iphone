"""Offline reproducible tests. Prices are SYNTHETIC, not Massive quotes."""
import unittest
from dataclasses import replace
from datetime import date, timedelta
from swingbot.equity_screen import DailyBar
from swingbot.massive_free import FreeMarketHistory
from swingbot.us_watchlist import US_WATCHLIST_50, rank_us_research
from swingbot.us_synthetic_lab import compare_abc_offline


def synthetic(symbol="AAPL", count=310, shock=False):
    bars=[]
    start=date(2025,10,20)
    for k in range(count):
        px=50+k*.26
        if shock and k>count-28:
            px*=.48
        vol=1500000
        bars.append(DailyBar(start+timedelta(days=k), px-.2,
                             px+1.2, px-1.3, px, vol))
    return FreeMarketHistory(symbol,"USD","SYNTHETIC_TEST_FIXTURE",
                            "SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",
                            tuple(bars))


class USResearchTests(unittest.TestCase):
    def test_curated_exactly_50_unique(self):
        self.assertEqual(len(US_WATCHLIST_50),50)
        self.assertEqual(len(set(US_WATCHLIST_50)),50)

    def test_rank_top20_is_synthetic_watch_only(self):
        a,b=synthetic("AAPL"),synthetic("MSFT")
        as_of=a.bars[-1].day+timedelta(days=1)
        x=rank_us_research({"AAPL":a,"MSFT":b},as_of=as_of,limit=20)
        self.assertEqual(x["eligible"],2)
        self.assertFalse(x["eur_account_compatible"])
        self.assertFalse(x["real_order_authorized"])
        self.assertFalse(x["paper_trade_authorized"])
        self.assertTrue(all(z["source_adjustment"]=="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED" for z in x["ranking"]))

    def test_massive_non_display_block_by_default(self):
        a=synthetic()
        as_of=a.bars[-1].day+timedelta(days=1)
        prohibited=replace(a,source="Massive US Stocks Basic EOD")
        with self.assertRaises(PermissionError):
            rank_us_research({"AAPL":prohibited},as_of=as_of)
        with self.assertRaises(PermissionError):
            compare_abc_offline({"AAPL":prohibited},as_of=as_of)

    def test_reject_unknown_and_unverified_history(self):
        a=synthetic()
        d=a.bars[-1].day+timedelta(days=1)
        with self.assertRaises(ValueError):
            rank_us_research({"NOT_T212":a},as_of=d)
        with self.assertRaises(ValueError):
            compare_abc_offline({"NOT_T212":a},as_of=d)
        x=rank_us_research({"AAPL":replace(a,fx_verified=True)},as_of=d)
        self.assertEqual(x["eligible"],0)

    def test_abc_split_and_usd_risk(self):
        a,b=synthetic("AAPL"),synthetic("MSFT")
        as_of=a.bars[-1].day+timedelta(days=1)
        lab=compare_abc_offline({"AAPL":a,"MSFT":b},as_of=as_of)
        self.assertEqual(lab["data_use_rights"],"SYNTHETIC_TEST_FIXTURES_ONLY")
        self.assertEqual(len(lab["variants"]),3)
        self.assertTrue(lab["holdout_start"]>lab["training_end"])
        self.assertIn(lab["training_selected_strategy"],[v["strategy"] for v in lab["variants"]])
        self.assertFalse(lab["real_order_authorized"])
        self.assertFalse(lab["eur_paper_modified"])
        for variant in lab["variants"]:
            for period in ("training","holdout"):
                r=variant[period]
                self.assertEqual(r["starting_usd"],5000.0)
                self.assertEqual(r["real_order_authorized"],False)
                self.assertGreaterEqual(r["estimated_fees_usd"],0)
                self.assertLessEqual(r["max_drawdown_pct"],100)

    def test_never_look_into_future_bars(self):
        a=synthetic("AAPL")
        as_of=a.bars[-1].day+timedelta(days=1)
        before=compare_abc_offline({"AAPL":a},as_of=as_of)
        extra=DailyBar(as_of,900,910,880,905,10000000)
        after=compare_abc_offline(
            {"AAPL":replace(a,bars=a.bars+(extra,))},as_of=as_of
        )
        self.assertEqual(before,after)

    def test_25pct_halt_applies_to_new_entries(self):
        a=synthetic("AAPL",shock=True)
        as_of=a.bars[-1].day+timedelta(days=1)
        lab=compare_abc_offline({"AAPL":a},as_of=as_of)
        self.assertTrue(all("halted_new_entries" in v["holdout"]
                            for v in lab["variants"]))


if __name__=="__main__":
    unittest.main()
