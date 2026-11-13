"""Fast no-lookahead BTC/ETH 5m buying indicator snapshots for 5y replay.

Numerically the same indicator inequalities as:
 quality_buy_signal -> confirmed_upward_move, except explicit 1e-9
 float tolerance for near-boundary historical candles. Signals calculated
 ONLY from data through bar i and executed at i+1 OPEN in replay engine.
"""
from __future__ import annotations

from collections import deque
from statistics import mean
from .daytrade_one_per_day import local_time


def _rolling_prefix(values):
    prefix=[0.]
    for v in values:
        prefix.append(prefix[-1]+v)
    return prefix


def generate_frozen_signals(bars):
    """Compute 3 predeclared signal sets over contiguous completed candles.

    No future OHLC, no all-day all-in. The 'morning_strict' candidate was
    hypothesized AFTER prior 150d trade review; do not declare 5y test
    independent. Identical price and fee handling for all candidates.
    """
    n=len(bars)
    if n<180:
        return {"confirmed_reference":set(),"confirmed_morning":set(),
                "morning_strict":set()}
    cp=_rolling_prefix([x["close"] for x in bars])
    vp=_rolling_prefix([x["volume"] for x in bars])
    true=[0.]
    for i in range(1,n):
        b=bars[i];prev=bars[i-1]["close"]
        true.append(max(b["high"]-b["low"],abs(b["high"]-prev),
                        abs(b["low"]-prev)))
    tp=_rolling_prefix(true)
    sets={"confirmed_reference":set(),"confirmed_morning":set(),
          "morning_strict":set()}
    # Previous-20 high rolling maximum, monotonic queue: no O(20) rescans.
    recent_high=deque()
    for i in range(n):
        # Queue covers strictly BEFORE i when making decision on bar i.
        if i>=20:
            j=i-1
            while recent_high and bars[recent_high[-1]]["high"]<=bars[j]["high"]:
                recent_high.pop()
            recent_high.append(j)
        while recent_high and recent_high[0]<i-20:
            recent_high.popleft()

        if not 160<=i<n-1:
            continue
        next_clock=local_time(bars[i+1]["timestamp_ms"])
        if not 9<=next_clock.hour<20:
            continue
        bar=bars[i]
        close=bar["close"]
        if (close<=bar["open"] or
            bar["close"]-bar["open"]<.35*(bar["high"]-bar["low"])
            or not recent_high or close<=bars[recent_high[0]]["high"]):
            continue
        p20=(cp[i]-cp[i-20])/20
        p50=(cp[i]-cp[i-50])/50
        if not(close>p20 and p20>p50):
            continue
        s20=(cp[i+1]-cp[i-19])/20
        s50=(cp[i+1]-cp[i-49])/50
        s100=(cp[i+1]-cp[i-99])/100
        if not (s20>s50>s100 and close>s20):
            continue
        avol=(vp[i]-vp[i-20])/20
        if avol<=0 or bar["volume"]<avol*1.2:
            continue
        atr=(tp[i+1]-tp[i-13])/14/close*100
        if not .18<=atr<=1.5:
            continue
        earlier=(cp[i-95]-cp[i-143])/48
        recent=(cp[i+1]-cp[i-47])/48
        slope=(recent/earlier-1)*100
        if not .35<=slope<=6.0:
            continue
        if (close/bars[i-5]["close"]-1)*100>1.5:
            continue
        span=bar["high"]-bar["low"]
        if span<=0 or (close-bar["low"])/span<.65:
            continue
        if not (bars[i-3]["close"]<bars[i-2]["close"]
                <bars[i-1]["close"]<close):
            continue
        gain15=(close/bars[i-3]["close"]-1)*100
        if not .12<=gain15<=.90:
            continue
        sets["confirmed_reference"].add(i)
        if next_clock.hour<14:
            sets["confirmed_morning"].add(i)
            if slope>=1.0 and bar["volume"]>=avol*1.9:
                sets["morning_strict"].add(i)
    return sets
