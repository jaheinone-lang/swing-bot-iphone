"""Offline reproducible tests. Prices are SYNTHETIC, not Massive quotes."""
import unittest
from dataclasses import replace
from unittest.mock import patch
from datetime import date, timedelta
from swingbot.equity_screen import DailyBar
from swingbot.massive_free import FreeMarketHistory
from swingbot.us_watchlist import US_WATCHLIST_50, rank_us_research
from swingbot.us_synthetic_lab import compare_abc_offline, _simulation, SPECS, WARMUP


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

    def test_all_50_names_supported_with_synthetic_data(self):
        # Repeated synthetic trajectories are a software load test, never a
        # representation of real market breadth or historical index membership.
        all_data={ticker: synthetic(ticker,count=275)
                  for ticker in US_WATCHLIST_50}
        as_of=next(iter(all_data.values())).bars[-1].day+timedelta(days=1)
        ranked=rank_us_research(all_data,as_of=as_of)
        self.assertEqual(ranked["received"],50)
        self.assertEqual(ranked["eligible"],50)
        self.assertEqual(len(ranked["ranking"]),20)
        self.assertFalse(ranked["real_order_authorized"])
        lab=compare_abc_offline(all_data,as_of=as_of)
        self.assertEqual(lab["symbol_count"],50)
        self.assertEqual(len(lab["variants"]),3)
        self.assertFalse(lab["eur_paper_modified"])

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

    def test_overnight_gap_triggers_halt_before_new_buy(self):
        # Synthetic 3-position portfolio falls >25% at the morning open.
        # Old logic evaluated circuit only at the close, so a forced new
        # buy at that open would have violated the circuit breaker.
        dates=[date(2025,1,1)+timedelta(days=i) for i in range(WARMUP+3)]
        aligned={}
        for symbol in ("AAPL","MSFT","JPM"):
            rows=[]
            for idx,d in enumerate(dates):
                open_px=1.0 if idx==WARMUP+1 else 100.0
                close_px=open_px
                rows.append(DailyBar(d,open_px,open_px+1.0,
                                     max(.01,open_px-1.0),
                                     close_px,1_500_000))
            aligned[symbol]=tuple(rows)
        def forced_signal(history, cfg):
            # Signal 3 buys before gap, then try repeatedly after gap.
            return (.2,1.0) if len(history)>=WARMUP else None
        with patch("swingbot.us_synthetic_lab._signal",side_effect=forced_signal):
            report=_simulation(aligned,dates,SPECS[0],WARMUP,WARMUP+3)
        self.assertTrue(report["halted_new_entries"])
        self.assertEqual(report["buy_events"],3)
        self.assertEqual(report["overnight_gap_stop_exits"],3)
        self.assertGreater(report["max_drawdown_pct"],25.0)
        self.assertEqual(report["completed_round_trips"],3)
        self.assertEqual(report["order_event_count"],
                         report["buy_events"]+report["sell_events"])

    def test_theoretical_reference_is_not_sp500_and_no_fake_winner(self):
        a,b=synthetic("AAPL"),synthetic("MSFT")
        report=compare_abc_offline(
            {"AAPL":a,"MSFT":b},as_of=a.bars[-1].day+timedelta(days=1)
        )
        self.assertEqual(report["benchmark_training"]["reference"],
                         "THEORETICAL_EQUAL_WEIGHT_WATCHLIST_NOT_INVESTABLE")
        self.assertTrue(report["benchmark_holdout"]["survivorship_bias"])
        self.assertTrue(report["benchmark_training"]["fractional_shares_assumed"])
        self.assertEqual(report["minimum_training_completed_trades"],15)
        self.assertIsNone(report["qualified_strategy"])
        self.assertFalse(report["qualified_comparison_available"])
        self.assertFalse(report["real_order_authorized"])

    def test_trade_accounting_has_explicit_closed_trade_metrics(self):
        a=synthetic("AAPL")
        result=compare_abc_offline(
            {"AAPL":a},as_of=a.bars[-1].day+timedelta(days=1))
        for variant in result["variants"]:
            for phase in ("training","holdout"):
                stats=variant[phase]
                self.assertEqual(stats["order_event_count"],
                                 stats["buy_events"]+stats["sell_events"])
                self.assertEqual(stats["completed_round_trips"],
                                 stats["sell_events"])
                self.assertLessEqual(stats["max_planned_stop_risk_pct_of_equity"],1.001)
                self.assertIn("net_realized_closed_pnl_usd",stats)
                self.assertIn("worst_day_pct",stats)
                self.assertIn("closed_trade_profit_factor",stats)

    def test_25pct_halt_applies_to_new_entries(self):
        a=synthetic("AAPL",shock=True)
        as_of=a.bars[-1].day+timedelta(days=1)
        lab=compare_abc_offline({"AAPL":a},as_of=as_of)
        self.assertTrue(all("halted_new_entries" in v["holdout"]
                            for v in lab["variants"]))


if __name__=="__main__":
    unittest.main()
