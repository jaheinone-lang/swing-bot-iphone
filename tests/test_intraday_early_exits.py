"""Fail-closed tests for same-day 5-minute causal weakness exits."""
import unittest
from datetime import datetime,timezone

from swingbot.daytrade_one_per_day import replay_one_per_day
from swingbot.intraday_early_exits import (
    fading_rise_30m,no_progress_120m,choose_exit_guard,POLICY_NAMES)


def market(days=2):
    start=int(datetime(2026,9,30,21,tzinfo=timezone.utc).timestamp()*1000)
    return [{"timestamp_ms":start+i*300000, "open":100., "high":100.2,
             "low":99.6, "close":100., "volume":100}
            for i in range(days*288)]


class EarlyExitTests(unittest.TestCase):
    def test_guards_only_use_completed_bars(self):
        b=market()
        p={"entry_bar":171,"entry_raw":100.}
        for k,v in [(173,100.),(174,99.95),(175,99.9),(176,99.85)]:
            b[k]["close"]=v
        self.assertTrue(fading_rise_30m(b,177,p))
        old=fading_rise_30m(b,177,p)
        b[177]["close"]=200.
        b[177]["low"]=2.
        b[177]["high"]=200.
        self.assertEqual(fading_rise_30m(b,177,p),old)
        self.assertFalse(fading_rise_30m(b,176,p))
        self.assertTrue(no_progress_120m(b,195,p))
        self.assertFalse(no_progress_120m(b,194,p))

    def test_guard_preempts_intrabar_stop_at_current_open(self):
        btc=market()
        eth=market()
        for k,v in [(173,100.),(174,99.95),(175,99.9),(176,99.85)]:
            btc[k]["close"]=v
        btc[177]["low"]=98.
        result=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            signal=lambda rows,i: rows is btc and i==170,
            exit_guard=choose_exit_guard("fade_30m"))
        self.assertEqual(result["buys"],1)
        self.assertEqual(result["early_exits"],1)
        self.assertEqual(result["stop_exits"],0)
        exit_event=[e for e in result["events"] if e["type"]=="EARLY_EXIT"][0]
        self.assertEqual(exit_event["exit_raw"],100)
        self.assertEqual(exit_event["holding_minutes"],30)

    def test_default_no_guard_preserves_original_stop(self):
        btc=market()
        eth=market()
        for k,v in [(173,100.),(174,99.95),(175,99.9),(176,99.85)]:
            btc[k]["close"]=v
        btc[177]["low"]=98.
        result=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            signal=lambda rows,i: rows is btc and i==170)
        self.assertEqual(result["early_exits"],0)
        self.assertEqual(result["stop_exits"],1)

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            choose_exit_guard("optimized_to_history")
        self.assertEqual(len(POLICY_NAMES),4)

if __name__=="__main__":unittest.main()
