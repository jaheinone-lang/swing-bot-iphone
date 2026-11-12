"""Hourly candlestick-pattern entries sampled from complete 5m OHLC BTC/ETH.

These are hypotheses, NOT demonstrated profitable strategies. Completed
UTC clock-hours only; signal is on last available bar of the hour, and the
simulator may buy only at NEXT 5m open, if Finnish 09:00-13:59.
The signal uses price bars through i ONLY. Do not use incomplete hour.
"""
from __future__ import annotations
from .daytrade_one_per_day import local_time

PATTERNS=("bullish_harami","hammer_confirm","bullish_hikkake")

def completed_hours(bars):
    hours=[]
    for i in range(11,len(bars),12):
        slice_=bars[i-11:i+1]
        if slice_[0]["timestamp_ms"]%3600000!=0:continue
        if any(slice_[j]["timestamp_ms"]-slice_[j-1]["timestamp_ms"]!=300000
               for j in range(1,12)):continue
        hours.append({"idx":i,"open":slice_[0]["open"],"high":max(x["high"] for x in slice_),
             "low":min(x["low"] for x in slice_),"close":slice_[-1]["close"],
             "volume":sum(x["volume"] for x in slice_)})
    return hours

def signals(bars):
    result={k:set() for k in PATTERNS}
    h=completed_hours(bars)
    for j in range(30,len(h)):
        cur=h[j];prev=h[j-1];before=h[j-2];older=h[j-3]
        i=cur["idx"]
        if i+1>=len(bars) or i<160:continue
        next_clock=local_time(bars[i+1]["timestamp_ms"])
        if not 9<=next_clock.hour<14:continue
        # Lower or sideways prior hourly context; in a powerful
        # persistent downtrend these patterns can be false positives.
        trend=h[j-24]["close"]<=cur["close"] # defensive rising-day gate
        if not trend:continue
        op,cl=cur["open"],cur["close"]
        body=abs(cl-op);spread=cur["high"]-cur["low"]
        if (prev["close"]<prev["open"] and cl>op
            and op>prev["close"] and cl<prev["open"]
            and prev["open"]-prev["close"]>2*body):
            result["bullish_harami"].add(i)
        # Hammer completed on previous hour, confirmation on current close.
        pbody=abs(prev["close"]-prev["open"]);prange=prev["high"]-prev["low"]
        if(prange>0 and pbody/prange<=.32 and
           min(prev["open"],prev["close"])-prev["low"]>=2*pbody and
           prev["high"]-max(prev["open"],prev["close"])<=pbody and
           cl>prev["high"] and cl>op):
            result["hammer_confirm"].add(i)
        # Conservative simplified upward Hikkake:
        # older outside, before inside (entire high/low), prev breaks
        # below inside, current recovers to above inside high.
        if (before["high"]<older["high"] and before["low"]>older["low"]
            and prev["low"]<before["low"]
            and cl>before["high"] and cl>op):
            result["bullish_hikkake"].add(i)
    return result
