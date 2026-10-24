import unittest
from swingbot.intraday_net_target import (
    ExecutionCosts, minimum_target_price, net_profit_pct,
    partial_profit_cashflow, complete_bar_exit_decision,
)


class NetTargetTests(unittest.TestCase):
    def test_default_one_percent_after_all_four_costs(self):
        t = minimum_target_price(100)
        self.assertGreater(t, 101.8)
        self.assertGreaterEqual(net_profit_pct(100, t), 1.0)
        self.assertLess(net_profit_pct(100, t - .01), 1.0)

    def test_one_percent_is_not_just_gross_one_percent(self):
        self.assertLess(net_profit_pct(100, 101), 1.0)
        no_fees = ExecutionCosts(0, 0, 0, 0)
        self.assertAlmostEqual(minimum_target_price(100, costs=no_fees), 101)

    def test_custom_fee_and_slippage_sensitivity(self):
        normal = minimum_target_price(100)
        stressed = minimum_target_price(
            100, costs=ExecutionCosts(50,50,30,30))
        self.assertGreater(stressed, normal)
        self.assertGreaterEqual(
            net_profit_pct(100, stressed,
                           ExecutionCosts(50,50,30,30)), 1
        )

    def test_partial_realizes_half_percent_of_portfolio(self):
        t=minimum_target_price(100)
        half=partial_profit_cashflow(100,t,sold_fraction=.5)
        self.assertGreaterEqual(half["realized_profit_on_sold_slice_pct"],1)
        self.assertGreaterEqual(half["net_realized_gain_eur_before_tax"],25)
        self.assertLess(half["net_realized_gain_eur_before_tax"],26)
        self.assertGreater(half["remaining_position_quantity"],0)
        all_in=partial_profit_cashflow(100,t,sold_fraction=1)
        self.assertGreaterEqual(all_in["net_realized_gain_eur_before_tax"],50)
        self.assertEqual(all_in["remaining_position_quantity"],0)

    def test_stop_priority_if_both_targets_hit_same_candle(self):
        decision=complete_bar_exit_decision(
            entry_price=100,bar_open=100,bar_high=105,bar_low=94,
            bar_close=101,target_price=102,stop_price=96)
        self.assertEqual(decision["reason"],"STOP_FIRST_CONSERVATIVE")
        t=complete_bar_exit_decision(
            entry_price=100,bar_open=100,bar_high=103,bar_low=99,
            bar_close=102,target_price=102,stop_price=96)
        self.assertEqual(t["reason"],"TAKE_PROFIT")
        self.assertEqual(t["raw_exit_price"],102)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            minimum_target_price(100,net_target_pct=-1)
        with self.assertRaises(ValueError):
            minimum_target_price(100,tick_size=0)
        with self.assertRaises(ValueError):
            partial_profit_cashflow(100,102,sold_fraction=0)
        with self.assertRaises(ValueError):
            ExecutionCosts(entry_fee_bps=-1)


if __name__ == "__main__":
    unittest.main()
