"""Alternative fixed-hypothesis BTC/ETH 5m entry families, read-only.

These are NOT incremental changes to the previous breakout filter:
  1) trend_continuation: 20/50/100 averages align, 1h rising closes,
     intraday pullback near SMA20, positive finishing 5m bar;
  2) mean_revert_uptrend: 20/50/100 uptrend but current close 0.2-0.8%
     below 20-bar mean; bullish reversal and adequate volatility;
  3) avoid_all: cash-only benchmark, no trades.
No completed candle after signal i informs that signal.
"""
from __future__ import annotations
from .five_year_fast_signals import _rolling_prefix
from .daytrade_one_per_day import local_time

POLICIES=("trend_continuation","mean_revert_uptrend","cash_only")

def compute(bars):
    found={k:set() for k in POLICIES}
    if len(bars)<200:return found
    closes=[b["close"] for b in bars]
    cp=_rolling_prefix(closes)
    for i in range(160,len(bars)-1):
        t=local_time(bars[i+1]["timestamp_ms"])
        if not 9<=t.hour<14:continue
        b=bars[i];c=b["close"]
        def avg(n):
            return (cp[i+1]-cp[i+1-n])/n
        ma20,ma50,ma100=avg(20),avg(50),avg(100)
        if not(ma20>ma50>ma100 and c>ma100):
            continue
        vol=sum(x["volume"] for x in bars[i-20:i])/20
        if vol<=0 or b["volume"]<vol*.85:continue
        if b["close"]<=b["open"]:continue
        if c>ma20 and c/closes[i-12]>1.002 and c/closes[i-3]<1.008:
            if bars[i-1]["low"]<=ma20*1.004:
                found["trend_continuation"].add(i)
        if .002<=1-c/ma20<=.008:
            if closes[i-1]<closes[i-2] and c>closes[i-1]:
                found["mean_revert_uptrend"].add(i)
    return found
