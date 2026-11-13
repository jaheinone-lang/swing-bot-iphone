import unittest
from swingbot.shared_btc_eth_portfolio import shared_replay
from swingbot.five_month_exit_research import (
    PREDECLARED, _period_windows, _evaluate, ExitPolicy)
from swingbot.intraday_net_target import ExecutionCosts


def bars(count=210, start=1700000100000):
    out=[]
    for i in range(count):
        price=100.
        high=104. if i==162 else 100.3
        low=99.5
        out.append({"timestamp_ms":start+i*300000,
                    "open":price,"high":high,"low":low,
                    "close":price,"volume":100.})
    return out


class ExitResearchTests(unittest.TestCase):
    def test_policy_grid_preserves_net_target_one_percent_minimum(self):
        self.assertEqual(len(PREDECLARED),6)
        self.assertTrue(all(p.take_profit_pct>=1 for p in PREDECLARED))
        self.assertEqual(PREDECLARED[0].stop_pct,1.5)
        self.assertEqual(PREDECLARED[0].sell_fraction,.5)

    def test_full_take_profit_closes_position_and_records_gain(self):
        a=bars()
        b=bars()
        outcome=shared_replay(
            {"BTC-EUR":a, "ETH-EUR":b},
            signal=lambda rows,i: i==160 and rows is a,
            first_entry_index=160,
            take_fraction=1.)
        self.assertEqual(outcome["buys"],1)
        self.assertEqual(outcome["full_take_profits"],1)
        self.assertEqual(outcome["half_take_profits"],0)
        self.assertFalse(outcome["open_positions"])
        self.assertGreaterEqual(outcome["profit_eur_before_tax"],5.)

    def test_partial_sell_keeps_remainder_at_target(self):
        a=bars()
        b=bars()
        outcome=shared_replay(
            {"BTC-EUR":a,"ETH-EUR":b},
            signal=lambda rows,i: i==160 and rows is a,
            first_entry_index=160,
            take_fraction=.5)
        self.assertEqual(outcome["half_take_profits"],1)
        self.assertEqual(outcome["full_take_profits"],0)

    def test_invalid_target_and_size_rejected(self):
        a=bars()
        b=bars()
        for kwargs in (
            {"take_fraction":0},
            {"take_fraction":1.2},
            {"take_profit_pct":.5},
            {"stop_pct":0},
        ):
            with self.assertRaises(ValueError):
                shared_replay({"BTC-EUR":a,"ETH-EUR":b},**kwargs)

    def test_train_later_split_not_sharing_executed_candles(self):
        a=bars(count=800)
        b=bars(count=800)
        mapping={"BTC-EUR":{x["timestamp_ms"]:x for x in a},
                 "ETH-EUR":{x["timestamp_ms"]:x for x in b}}
        split=a[450]["timestamp_ms"]
        periods,common,runs=_period_windows(mapping,split_ms=split)
        self.assertEqual(common,800)
        self.assertTrue(periods["train"] and periods["later"])
        train_trade_times={
            t["timestamp_ms"]
            for feed,index,_ in periods["train"]
            for t in feed["BTC-EUR"][index:]
        }
        later_trade_times={
            t["timestamp_ms"]
            for feed,index,_ in periods["later"]
            for t in feed["BTC-EUR"][index:]
        }
        self.assertTrue(train_trade_times.isdisjoint(later_trade_times))


if __name__=="__main__":
    unittest.main()
