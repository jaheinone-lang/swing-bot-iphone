import unittest
from swingbot.intraday_pullback_research import pullback_signal

class PullbackTests(unittest.TestCase):
    def test_incomplete_history_never_trades(self):
        bars=[{"open":100,"high":101,"low":99,"close":100,"volume":100}
              for _ in range(90)]
        self.assertFalse(pullback_signal(bars,10))
        self.assertFalse(pullback_signal(bars,89))
    def test_requires_volume(self):
        bars=[{"open":100+i*.01,"high":101+i*.01,
               "low":99+i*.01,"close":100+i*.01,"volume":0}
              for i in range(100)]
        self.assertFalse(pullback_signal(bars,95))
if __name__=="__main__":unittest.main()
