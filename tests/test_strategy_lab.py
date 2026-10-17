"""Strategy laboratory is strictly historical; real paper state is untouched."""
import unittest
from datetime import date, timedelta

from swingbot.portfolio import Bar
from swingbot.fi_tax_estimate import annual_tax_schedule
from swingbot.strategy_lab import (
    Spec, VARIANTS, _safe_size, research_backtest, walkforward_research
)


def sample_data(length=430):
    start=date(2024,1,1)
    stock=[]
    btc=[]
    for index in range(length):
        day=start+timedelta(days=index)
        # Trending then declining, with occasional breakout pulses.
        c1=(80+.18*index+4*(index%50>=43)) if index<300 else (
            134-.09*(index-300)+4*(index%50>=43))
        c2=(100+.22*index+5*(index%31>=26)) if index<300 else (
            166-.14*(index-300)+5*(index%31>=26))
        if day.weekday()<5:
            stock.append(Bar(day,c1-0.5,c1+2.5,c1-2.5,c1))
        btc.append(Bar(day,c2-.5,c2+3,c2-3,c2))
    return {"TEST.DE":stock,"BTC-EUR":btc},{"TEST.DE":"stock","BTC-EUR":"crypto"}


class TaxEstimatorTests(unittest.TestCase):
    def test_one_gain_and_loss_offset_same_year(self):
        tax=annual_tax_schedule([
            {"year":2026,"gain_eur":1000},
            {"year":2026,"gain_eur":-500}
        ])
        self.assertEqual(tax["total_estimated_tax_eur"],150.0)

    def test_brackets_and_other_capital_income(self):
        self.assertEqual(annual_tax_schedule([
            {"year":2026,"gain_eur":40000}
        ])["total_estimated_tax_eur"],12400.0)
        self.assertEqual(annual_tax_schedule([
            {"year":2026,"gain_eur":1000}
        ],other_capital_income_eur=30000)["total_estimated_tax_eur"],340.0)

    def test_losses_carried_five_years_not_six(self):
        r=annual_tax_schedule([
            {"year":2020,"gain_eur":-1000},
            {"year":2025,"gain_eur":800},
            {"year":2026,"gain_eur":500},
        ])
        self.assertEqual(r["total_estimated_tax_eur"],150.0)

    def test_negative_other_capital_income_invalid(self):
        with self.assertRaises(ValueError):
            annual_tax_schedule([],other_capital_income_eur=-10)


class StrategyResearchTests(unittest.TestCase):
    def test_compounding_position_size_uses_after_tax_equity(self):
        variant=VARIANTS[2]
        full=_safe_size(5000,5000,100,10,0,"stock",variant)
        reserved=_safe_size(4000,4000,100,10,0,"stock",variant)
        self.assertGreater(full,reserved)

    def test_all_variants_and_frozen_walkforward(self):
        data,markets=sample_data()
        report=walkforward_research(data,markets)
        self.assertEqual(len(report["variants"]),3)
        self.assertFalse(report["auto_trading_changes"])
        self.assertIn(report["training_selected_variant"],
                      [v["name"] for v in report["variants"]])
        self.assertLess(report["split_date"],report["validation_end"])
        for row in report["variants"]:
            self.assertIn("holdout",row)
            self.assertIn("development",row)
            self.assertGreaterEqual(row["estimated_tax_reserve_eur"],0)

    def test_does_not_fabricate_historical_disposals_tax(self):
        data,markets=sample_data()
        for variant in VARIANTS:
            r=research_backtest(data,markets,variant)
            self.assertEqual(len(r["daily_curve"]),
                             len({b.day for bars in data.values() for b in bars}))
            self.assertLessEqual(r["after_tax_equity_eur"],
                                 r["gross_final_equity_eur"]+.00001)
            self.assertEqual(r["starting_eur"],5000)
            self.assertGreaterEqual(r["estimated_fees_eur"],0)
            self.assertTrue(all(t["side"] in ("BUY","SELL")
                                for t in r["trade_events"]))

    def test_later_market_data_cannot_change_earlier_paper_fills(self):
        data,markets=sample_data(430)
        cut=date(2024,10,10)
        early={sym:[bar for bar in bars if bar.day<=cut] for sym,bars in data.items()}
        first=research_backtest(early,markets,VARIANTS[1])
        extended=research_backtest(data,markets,VARIANTS[1])
        earlier_curve=[v for v in extended["daily_curve"] if v["day"]<=cut.isoformat()]
        self.assertEqual(first["daily_curve"],earlier_curve)
        prior_events=[t for t in extended["trade_events"] if t["day"]<=cut.isoformat()]
        self.assertEqual(first["trade_events"],prior_events)

    def test_insufficient_history_refuses_training(self):
        data,markets=sample_data(250)
        with self.assertRaises(ValueError):
            walkforward_research(data,markets)


if __name__=="__main__":
    unittest.main()
