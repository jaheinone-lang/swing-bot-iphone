"""Regression of no-future entry features, clock gates and 90/60 data split."""
import unittest
from datetime import datetime, timezone
from swingbot.entry_timing_150d_audit import (
    POLICIES, accepts, candle_features, _period_windows, make_caches,
    _run_period,
)
from swingbot.intraday_net_target import ExecutionCosts


def bars(count=520):
    start = int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
    return [
        {"timestamp_ms":start+i*300000, "open":100+i*.01,
         "high":100.1+i*.01, "low":99.9+i*.01,
         "close":100.02+i*.01, "volume":100+(i%7)*10}
        for i in range(count)
    ]


class TimingAuditTests(unittest.TestCase):
    def test_predeclared_rule_gates_use_only_known_features(self):
        self.assertEqual(len(POLICIES),7)
        f={"relative_volume":1.8,"rise_15m_pct":.3,
           "trend_4h_vs_older_pct":1.5}
        self.assertTrue(accepts("confirmed_high_volume",f,
                                quality=True,confirmed=True,
                                next_entry_hour=12))
        self.assertFalse(accepts("confirmed_high_volume",f,
                                 quality=True,confirmed=False,
                                 next_entry_hour=12))
        self.assertTrue(accepts("confirmed_09_to_14",f,
                                quality=True,confirmed=True,
                                next_entry_hour=11))
        self.assertFalse(accepts("confirmed_09_to_14",f,
                                 quality=True,confirmed=True,
                                 next_entry_hour=17))
        self.assertTrue(accepts("confirmed_14_to_20",f,
                                quality=True,confirmed=True,
                                next_entry_hour=17))
        self.assertFalse(accepts("confirmed_reference",f,
                                 quality=True,confirmed=True,
                                 next_entry_hour=8))
        with self.assertRaises(ValueError):
            accepts("made_up_model",f,quality=True,confirmed=True,
                    next_entry_hour=12)

    def test_features_do_not_read_future(self):
        d=bars()
        f=candle_features(d,250)
        # Force invalid future data; features for 250 must stay unchanged.
        for b in d[251:]:
            b["close"]=.01
            b["volume"]=900000
        self.assertEqual(candle_features(d,250),f)

    def test_windows_do_not_overlap_tradeable_timestamps(self):
        d=bars(800)
        m={sym:{row["timestamp_ms"]:row for row in d}
           for sym in ("BTC-EUR","ETH-EUR")}
        split=d[450]["timestamp_ms"]
        parts,common,_runs=_period_windows(m,split_ms=split)
        self.assertEqual(common,800)
        train={b["timestamp_ms"]
               for feed,first,_ in parts["train"]
               for b in feed["BTC-EUR"][first:]}
        later={b["timestamp_ms"]
               for feed,first,_ in parts["later"]
               for b in feed["BTC-EUR"][first:]}
        self.assertTrue(train and later)
        self.assertTrue(train.isdisjoint(later))

    def test_no_signals_give_zero_buys_and_no_profit_claim(self):
        d=bars(600)
        feed={"BTC-EUR":d,"ETH-EUR":d}
        windows=[(feed,160,len(d)-160)]
        cache=make_caches(windows)
        result=_run_period(windows,cache,"confirmed_reference",
                           ExecutionCosts(),collect=True)
        self.assertEqual(result["buys"],0)
        self.assertEqual(result["pnl_eur"],0)
        self.assertEqual(result["sample_trades"],[])


if __name__=="__main__":
    unittest.main()
