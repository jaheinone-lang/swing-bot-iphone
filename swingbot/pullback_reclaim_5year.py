"""No-lookahead 5-minute BTC/ETH continuation vs pullback-reclaim signals.

ENTRY is always next 5m bar OPEN, strictly after the finished signal bar.
Prespecified comparison (not optimized to later realized outcomes):
- 'morning_strict' original breakout+impulse,
- 'breakout_pullback_reclaim' confirmed breakout 3-12 bars ago, EMA20
  retest then strong bullish reclaim in uptrend,
- 'trend_pullback_reclaim' two weak completed closes then a bullish
  20SMA reclaim in clean 20>50>100 uptrend, no breakout prerequisite.

Only Helsinki 09:00-13:59 potential NEXT BAR open. Never look ahead.
Both new hypotheses may LOSE money; tests do not enable trading.
"""
from __future__ import annotations

from collections import deque
from math import isfinite

from .daytrade_one_per_day import local_time
from .five_year_fast_signals import _rolling_prefix

NEW_POLICIES=("breakout_pullback_reclaim","trend_pullback_reclaim")
ALL_POLICIES=("morning_strict",)+NEW_POLICIES


def causal_pullback_signals(bars):
    n=len(bars)
    signals={p:set() for p in NEW_POLICIES}
    if n<180:return signals
    close=[b["close"] for b in bars]
    volume=[b["volume"] for b in bars]
    cp=_rolling_prefix(close)
    vp=_rolling_prefix(volume)
    true=[0.]
    for i in range(1,n):
        b=bars[i];previous=close[i-1]
        true.append(max(b["high"]-b["low"],
                        abs(b["high"]-previous),abs(b["low"]-previous)))
    tp=_rolling_prefix(true)
    highs=deque()
    breakout_recent=deque()

    def sma(end,length):
        return (cp[end+1]-cp[end+1-length])/length

    for i in range(n):
        # Maintain completed higher-high breakout markers. Breakout at j
        # is allowed only when j >= 30; its own previous 20 highs are
        # known from j-20..j-1. This never uses future candles.
        if i>=20:
            prev=i-1
            while highs and bars[highs[-1]]["high"]<=bars[prev]["high"]:
                highs.pop()
            highs.append(prev)
        while highs and highs[0]<i-20:
            highs.popleft()
        if i>=30 and highs:
            before_avg=(vp[i]-vp[i-20])/20
            if (before_avg>0 and close[i]>bars[highs[0]]["high"] and
                    bars[i]["volume"]>=before_avg*1.2):
                breakout_recent.append(i)
        while breakout_recent and breakout_recent[0]<i-12:
            breakout_recent.popleft()
        if not 160<=i<n-1:continue
        next_local=local_time(bars[i+1]["timestamp_ms"])
        if not 9<=next_local.hour<14:continue
        current=bars[i]
        price=close[i]
        fast=sma(i,20);middle=sma(i,50);slow=sma(i,100)
        if not (fast>middle>slow and price>fast and
                current["close"]>current["open"]):
            continue
        if not (price>bars[i-1]["high"] and
                price<=fast*1.009):continue
        bar_range=current["high"]-current["low"]
        if bar_range<=0 or (price-current["low"])/bar_range<.65:
            continue
        atr_pct=(tp[i+1]-tp[i-13])/14/price*100
        if not .18<=atr_pct<=1.5:
            continue
        # Previous one or two finished candles must have been a real
        # retracement, not five minutes of monotonically chasing price.
        dipped = any(
            bars[k]["low"] <= sma(k,20)*1.002
            for k in range(i-4,i))
        if not dipped:continue
        prior_average_volume=(vp[i]-vp[i-20])/20
        if (prior_average_volume<=0 or
                current["volume"]<prior_average_volume*.80):continue
        # Avoid buying a clear overextended spike.
        impulse=(price/close[i-3]-1)*100
        if impulse>1.0:continue

        # Require actual weakness in completed CLOSES, not just an
        # incidental wick inside a still-rising breakout sequence.
        declining=(close[i-3]>close[i-2]>close[i-1])
        rebounded=(declining and price>close[i-2])
        if rebounded:
            signals["trend_pullback_reclaim"].add(i)

        # Breakout 3-12 finished candles ago AND a subsequent descending
        # two-candle pullback that retested the 20-bar mean before reclaim.
        if rebounded and any((3<=i-breakout_i<=12 and any(
            bars[k]["low"]<=sma(k,20)*1.002
            for k in range(breakout_i+1,i)))
               for breakout_i in breakout_recent):
            signals["breakout_pullback_reclaim"].add(i)
    return signals
