"""Causal BTC/ETH five-year pullback-reclaim entry tests.

Synthetic prices deliberately include one completed-breakout, shallow
two-candle retest and bullish reclaim at a Finland-morning timestamp.
"""
import unittest
from datetime import datetime,timezone
from swingbot.pullback_reclaim_5year import (
    ALL_POLICIES,causal_pullback_signals)
from swingbot.five_year_pullback_research import (
    evaluate,inject_reclaim_signals)
from swingbot.five_year_fast_signals import generate_frozen_signals

START=int(datetime(2026,9,1,15,tzinfo=timezone.utc).timestamp()*1000)


def candles(n=410):
    rows=[]
    for i in range(n):
        close=100+i*.015
        if i==204:close-=.08
        if i==205:close-=.15
        if i==206:close-=.20
        rows.append({
            "timestamp_ms":START+i*300000,
            "open":close-.04,
            "high":close+.005,
            "low":close-.25,
            "close":close,
            "volume":500 if i==203 else (200 if i==207 else 100)
        })
    return rows


class PullbackFiveYearTests(unittest.TestCase):
    def test_declining_pullback_followed_by_reclaim_is_recognized(self):
        data=candles()
        found=causal_pullback_signals(data)
        self.assertIn(207,found["trend_pullback_reclaim"])
        self.assertIn(207,found["breakout_pullback_reclaim"])
        self.assertIn(len(ALL_POLICIES),[3])
        self.assertTrue(found["breakout_pullback_reclaim"].issubset(
            found["trend_pullback_reclaim"]))

    def test_future_prices_cannot_change_past_buy_signal(self):
        data=candles()
        before=causal_pullback_signals(data)
        # i+1 is the next OPEN bar, not allowed in the prior signal.
        data[208].update({
            "open":900000,"close":900000,"high":900000,"low":1,
            "volume":999999})
        for key in before:
            after=causal_pullback_signals(data)[key]
            self.assertEqual(207 in before[key],207 in after)

    def test_warmup_and_trade_date_in_one_pooled_account(self):
        btc=candles()
        eth=[dict(x,open=x["open"]*1.2,high=x["high"]*1.2,
                  low=x["low"]*1.2,close=x["close"]*1.2)
             for x in btc]
        feeds={"BTC-EUR":btc,"ETH-EUR":eth}
        frozen={s:generate_frozen_signals(feeds[s])
                for s in feeds}
        prepared=inject_reclaim_signals([(feeds,frozen)])
        result=evaluate(prepared,"breakout_pullback_reclaim")
        self.assertLessEqual(result["events"]["buys"],2)
        self.assertEqual(result["starting_eur"],5000)
        self.assertTrue(result["no_real_orders"])
        self.assertLessEqual(result["events"]["buys"],1)

    def test_unknown_policy_not_accepted(self):
        btc=candles()
        eth=[dict(x) for x in btc]
        feeds={"BTC-EUR":btc,"ETH-EUR":eth}
        prep=inject_reclaim_signals([(feeds,{
            s:generate_frozen_signals(feeds[s]) for s in feeds})])
        with self.assertRaises(ValueError):
            evaluate(prep,"future_peeking")


if __name__=="__main__":
    unittest.main()
