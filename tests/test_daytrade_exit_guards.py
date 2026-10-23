"""Safety regression for optional stop-capped crypto early exits."""
import unittest
from datetime import datetime,timezone
from swingbot.daytrade_exit_guards import (
    momentum_fade, losing_after_ninety_minutes,GUARDS)
from swingbot.daytrade_one_per_day import replay_one_per_day


def prices():
    start=int(datetime(2026,9,30,21,tzinfo=timezone.utc).timestamp()*1000)
    return [{
        "timestamp_ms":start+i*300000,
        "open":100., "high":100.2, "low":99.9,
        "close":100., "volume":100.
    } for i in range(500)]


class CausalEarlyExitTests(unittest.TestCase):
    def test_fade_exits_at_next_open_after_only_completed_bars(self):
        btc=prices();eth=prices()
        for index,close in ((161,99.95),(162,99.9),(163,99.85),(164,99.8)):
            btc[index]["close"]=close
            btc[index]["low"]=close-.03
        btc[165]["open"]=99.8
        btc[165]["low"]=99.75
        btc[165]["high"]=100.2
        original=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            first_entry_index=160,
            signal=lambda b,i:b is btc and i==160)
        early=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            first_entry_index=160,exit_guard=momentum_fade,
            signal=lambda b,i:b is btc and i==160)
        self.assertEqual(early["buys"],1)
        self.assertEqual(early["early_exits"],1)
        x=[e for e in early["events"] if e["type"]=="EARLY_EXIT"][0]
        self.assertEqual(x["bar"],165)
        self.assertEqual(x["exit_raw"],99.8)
        self.assertEqual(early["full_take_profits"],0)
        self.assertEqual(original["early_exits"],0)

    def test_future_candle_cannot_impact_guard(self):
        btc=prices()
        for index,close in ((161,99.95),(162,99.90),(163,99.85),(164,99.8)):
            btc[index]["close"]=close
        pos={"entry_bar":161,"entry_raw":100.}
        decided=momentum_fade(btc,165,pos)
        btc[165]["close"]=1.0
        btc[165]["low"]=.9
        btc[165]["high"]=1000.
        self.assertEqual(momentum_fade(btc,165,pos),decided)
        self.assertTrue(decided)

    def test_ninety_min_guard_no_premature_exit(self):
        btc=prices()
        pos={"entry_bar":161,"entry_raw":100.}
        for i in range(161,185):
            btc[i]["close"]=99.8-i*.0001
        self.assertFalse(losing_after_ninety_minutes(btc,178,pos))
        self.assertTrue(losing_after_ninety_minutes(btc,185,pos))

    def test_stop_at_open_overrides_early_guard(self):
        btc=prices();eth=prices()
        btc[165]["open"]=98.0
        btc[165]["low"]=97.5
        btc[165]["high"]=100.0
        res=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},first_entry_index=160,
            exit_guard=lambda b,i,p: i>=165,
            signal=lambda b,i: b is btc and i==160)
        self.assertEqual(res["stop_exits"],1)
        self.assertEqual(res["early_exits"],0)

    def test_baseline_guard_is_optional(self):
        self.assertIsNone(GUARDS["baseline"])
        self.assertEqual(set(GUARDS),
                         {"baseline","fade_3_descending","losing_after_90min"})


if __name__=="__main__":
    unittest.main()
