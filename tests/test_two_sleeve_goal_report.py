import unittest
from swingbot.two_sleeve_goal_report import report

class DualSleeveTests(unittest.TestCase):
    def test_deposits_not_profit(self):
        r=report(as_of="2026-12-10",trading_equity_eur=5100,
                 holding_liquidation_eur=390,
                 holding_contributions=[
                   {"month":"2026-11","eur":200},
                   {"month":"2026-12","eur":200}],trade_peak_eur=5500)
        self.assertEqual(r["trading"]["profit_eur"],100)
        self.assertEqual(r["holding"]["profit_eur"],-10)
        self.assertEqual(r["combined"]["profit_eur"],90)
        self.assertEqual(r["combined"]["equity_eur"],5490)
        self.assertEqual(r["combined"]["external_capital_eur"],5400)
        self.assertEqual(r["trading"]["one_year_100pct_goal_eur_if_no_external_flows"],10000)
        self.assertFalse(r["trading"]["annual_goal_is_not_forecast"] is False)
    def test_future_deposit_rejected(self):
        with self.assertRaises(ValueError):
            report(as_of="2026-11-12",trading_equity_eur=5000,
                holding_liquidation_eur=200,
                holding_contributions=[{"month":"2026-12","eur":200}])
    def test_duplicate_deposit_rejected(self):
        with self.assertRaises(ValueError):
            report(as_of="2026-11-12",trading_equity_eur=5000,
                holding_liquidation_eur=390,
                holding_contributions=[
                   {"month":"2026-11","eur":200},
                   {"month":"2026-11","eur":200}])
    def test_drawdown_guard_and_no_fictional_performance(self):
        v=report(as_of="2026-11-12",trading_equity_eur=3750,
          holding_liquidation_eur=0,holding_contributions=[],trade_peak_eur=5000)
        self.assertTrue(v["trading"]["drawdown_threshold_breached"])
        self.assertEqual(v["trading"]["peak_drawdown_pct"],25)
        with self.assertRaises(ValueError):
            report(as_of="2026-11-12",trading_equity_eur=6000,
                   holding_liquidation_eur=0,holding_contributions=[],
                   trade_peak_eur=5000)
    def test_missing_peak_is_unknown_not_safe(self):
        v=report(as_of="2026-11-12",trading_equity_eur=5000,
            holding_liquidation_eur=0,holding_contributions=[])
        self.assertIsNone(v["trading"]["drawdown_threshold_breached"])
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            report(as_of="2026-11-12",trading_equity_eur=float("nan"),
                   holding_liquidation_eur=0,holding_contributions=[])
    def test_external_trading_deposit_not_profit(self):
        v=report(as_of="2026-11-12",trading_equity_eur=6000,
          holding_liquidation_eur=0,holding_contributions=[],
          trading_external_flows_eur=1000)
        self.assertEqual(v["trading"]["profit_eur"],0)
        self.assertEqual(v["combined"]["profit_eur"],0)
if __name__=="__main__":unittest.main()
