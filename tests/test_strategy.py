import unittest
from swingbot.strategy import evaluate_signal


def prices(last=120.0):
    close = [100.0] * 60 + [last]
    high = [v + 2.0 for v in close]
    low = [v - 2.0 for v in close]
    return close, high, low


class StrategyTests(unittest.TestCase):
    def test_breakout_generates_hypothetical_buy(self):
        result = evaluate_signal(*prices())
        self.assertEqual(result["action"], "BUY")
        self.assertGreater(result["quantity"], 0)
        self.assertLessEqual(result["notional"], 1000.01)
        self.assertLess(result["stop_price"], result["price"])

    def test_no_breakout_means_hold(self):
        result = evaluate_signal(*prices(last=100.0))
        self.assertEqual(result["action"], "HOLD")

    def test_drawdown_guard(self):
        result = evaluate_signal(*prices(), equity=3750, peak_equity=5000)
        self.assertEqual(result["action"], "HALT")
        self.assertEqual(result["quantity"], 0)

    def test_short_history_means_hold(self):
        result = evaluate_signal(*([100.0] * 10, [102.0] * 10, [98.0] * 10))
        self.assertEqual(result["reason"], "not_enough_history")

    def test_invalid_candle_raises(self):
        with self.assertRaises(ValueError):
            evaluate_signal([100], [90], [80])


if __name__ == "__main__":
    unittest.main()
