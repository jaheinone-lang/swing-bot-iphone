"""Explicit check of user-requested full-EUR sizing and compound reinvestment."""
import unittest
from datetime import date, timedelta
from dataclasses import replace

from swingbot.crypto_allocation_research import (
    E, SCENARIOS, analyse_allocation,
)
from swingbot.crypto_alpha_research import SYMBOLS
from swingbot.portfolio import Bar
from swingbot.strategy_lab import _safe_size


def rising_market(days=420):
    data = {}
    for sym_i, sym in enumerate(SYMBOLS):
        series = []
        for i in range(days):
            day = date(2025, 1, 1) + timedelta(days=i)
            price = (100 + (sym_i+1)*18) * (1.0035**i)
            # No unrealistic future peeking, only valid independent bars.
            series.append(Bar(day, price, price*1.015, price*.985, price))
        data[sym] = series
    return data


class CapitalAllocationTests(unittest.TestCase):
    def test_e100_differs_only_by_sizing_not_indicators(self):
        self.assertEqual(len(SCENARIOS), 3)
        base = SCENARIOS[0][1]
        for _, spec, risk_cap in SCENARIOS[1:]:
            self.assertEqual(spec.breakout, base.breakout)
            self.assertEqual(spec.trend, base.trend)
            self.assertEqual(spec.stop_atr, base.stop_atr)
            self.assertEqual(spec.sma200_filter, base.sma200_filter)
            self.assertEqual(spec.max_position, 1.0)
        self.assertEqual(SCENARIOS[0][2], .03)
        self.assertEqual(SCENARIOS[1][2], .03)
        self.assertIsNone(SCENARIOS[2][2])

    def test_size_compounds_wins_and_losses(self):
        # With 2%-risk cap binding, position quantity increases for 6k
        # relative to 5k and decreases for 4k relative to 5k.
        cfg = replace(E, max_position=1.0)
        quantities = [_safe_size(e,e,100,10,25,"crypto",cfg)
                      for e in (4000,5000,6000)]
        self.assertLess(quantities[0], quantities[1])
        self.assertLess(quantities[1], quantities[2])
        # All-in max 100% uses practically the entire net cash balance.
        allin = SCENARIOS[2][1]
        qty = _safe_size(5000,5000,100,10,25,"crypto",allin)
        self.assertGreater(qty*100, 4980)
        self.assertLessEqual(qty*100*(1+25/10000), 5000.001)

    def test_thirty_day_account_reset_and_full_reinvestment(self):
        data = rising_market()
        result = analyse_allocation(data)
        self.assertEqual(result["starting_eur"],5000)
        self.assertEqual(result["recent_days"],30)
        self.assertEqual(result["external_contributions"],0)
        self.assertTrue(result["profits_reinvested"])
        self.assertEqual(len(result["scenarios"]),3)
        for scenario in result["scenarios"]:
            month = scenario["most_recent_30d_from_fresh_5000"]
            whole = scenario["full_history_compounding"]
            self.assertEqual(month["days"],30)
            self.assertEqual(month["starting_eur"],5000)
            self.assertGreater(month["ending_eur"],0)
            self.assertGreater(whole["final_equity_eur"],0)
            self.assertEqual(
                round(5000+month["profit_eur"],2),month["ending_eur"]
            )
            self.assertLessEqual(month["days_95pct_or_more_invested"],30)
            self.assertGreaterEqual(month["days_not_invested"],0)

    def test_in_rising_market_all_in_approaches_full_allocation(self):
        data = rising_market()
        result = analyse_allocation(data)
        base, capped, allin = result["scenarios"]
        self.assertGreater(
            allin["most_recent_30d_from_fresh_5000"]["days_95pct_or_more_invested"],0
        )
        self.assertGreater(
            allin["most_recent_30d_from_fresh_5000"]["mean_invested_share_pct"],
            capped["most_recent_30d_from_fresh_5000"]["mean_invested_share_pct"]
        )
        self.assertGreater(
            capped["most_recent_30d_from_fresh_5000"]["mean_invested_share_pct"],
            base["most_recent_30d_from_fresh_5000"]["mean_invested_share_pct"]
        )

    def test_invalid_data_and_balances_fail(self):
        data = rising_market()
        for bad in (float("nan"),0,-100):
            with self.assertRaises(ValueError):
                analyse_allocation(data,starting_eur=bad)
        with self.assertRaises(ValueError):
            analyse_allocation(data,recent_days=3)
        data["SOL-EUR"].pop(110)
        with self.assertRaises(ValueError):
            analyse_allocation(data)


if __name__ == "__main__":
    unittest.main()
