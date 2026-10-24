"""Regression tests for one-trade-per-day BTC+ETH cash-only rules."""
import unittest
from datetime import datetime, timezone
from swingbot.daytrade_one_per_day import replay_one_per_day, local_time


def prices(days=2):
    utc = datetime(2026, 9, 30, 21, 0, tzinfo=timezone.utc)
    start = int(utc.timestamp()*1000)
    return [
        {"timestamp_ms":start+i*300000, "open":100.0,
         "high":100.2, "low":99.9, "close":100.0, "volume":100.0}
        for i in range(days*288)
    ]


class DayTradeTests(unittest.TestCase):
    def test_one_buy_per_day_and_whole_position_exit(self):
        btc=prices()
        eth=prices()
        btc[171]["high"]=103.
        btc[459]["high"]=103.
        btc[459]["low"]=98.
        output=replay_one_per_day(
            {"BTC-EUR":btc, "ETH-EUR":eth},
            signal=lambda bars, i: bars is btc and i in (
                170,171,172,458,459))
        self.assertEqual(output["buys"],2)
        self.assertEqual(output["full_take_profits"],1)
        self.assertEqual(output["stop_exits"],1)
        self.assertEqual(output["open_positions"],0)
        buys=[x for x in output["events"] if x["type"]=="BUY"]
        self.assertEqual(len(set(x["day_local"] for x in buys)),2)
        sells=[x for x in output["events"] if x["type"]=="FULL_TP"]
        self.assertGreaterEqual(sells[0]["net_return_pct_on_position"],1.0)

    def test_21_55_forces_cash_and_avoids_overnight(self):
        btc=prices()
        eth=prices()
        output=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            signal=lambda bars,i: bars is btc and i==170)
        self.assertEqual(output["buys"],1)
        self.assertEqual(output["session_end_exits"],1)
        self.assertEqual(output["open_positions"],0)
        end=[x for x in output["events"] if x["type"]=="DAY_FLAT"][0]
        self.assertEqual(local_time(btc[end["bar"]]["timestamp_ms"]).hour,21)
        self.assertEqual(local_time(btc[end["bar"]]["timestamp_ms"]).minute,55)

    def test_night_signal_rejected(self):
        btc=prices()
        eth=prices()
        result=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            signal=lambda bars,i: bars is btc and i==270)
        self.assertEqual(result["buys"],0)

    def test_shared_capital_no_sol_and_aligned_time(self):
        btc=prices()
        eth=prices()
        with self.assertRaises(ValueError):
            replay_one_per_day({"BTC-EUR":btc,"SOL-EUR":eth})
        eth[100]["timestamp_ms"]+=300000
        with self.assertRaises(ValueError):
            replay_one_per_day({"BTC-EUR":btc,"ETH-EUR":eth})

    def test_previous_day_registry_blocks_second_segment_trade(self):
        btc=prices()
        eth=prices()
        trade_day=local_time(btc[171]["timestamp_ms"]).date().isoformat()
        out=replay_one_per_day(
            {"BTC-EUR":btc,"ETH-EUR":eth},
            previously_traded_days=(trade_day,),
            signal=lambda bars,i: bars is btc and i==170)
        self.assertEqual(out["buys"],0)


if __name__=="__main__":
    unittest.main()
