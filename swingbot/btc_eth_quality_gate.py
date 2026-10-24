"""Predeclared higher-timeframe quality gate for BTC/ETH spot buy signals.

No tuning based on holdout outcomes. Completed 5m candles only; the
100-candle regime + breakout signal is a prerequisite. Uses past ~4h
and ~12h slopes plus adequate current 5m ATR. No predictions.
"""
from __future__ import annotations
from statistics import mean
from .intraday_risk_regime import regime_buy_signal

def quality_buy_signal(bars, i):
    if i < 150 or not regime_buy_signal(bars,i):
        return False
    closes=[x["close"] for x in bars[i-150:i+1]]
    # Require a clear longer-term trend: avoid weak sideways up-cycles.
    recent=mean(closes[-48:])
    older=mean(closes[-144:-96])
    slope=(recent/older-1)*100
    if not .35 <= slope <= 6.0:
        return False
    bar=bars[i]
    ranges=[]
    for k in range(i-13,i+1):
        x=bars[k]; prev=bars[k-1]["close"]
        ranges.append(max(x["high"]-x["low"],
                          abs(x["high"]-prev),abs(x["low"]-prev)))
    atr_pct=mean(ranges)/bar["close"]*100
    if not .18<=atr_pct<=1.5:return False
    # Avoid a single already overstretched entry candle.
    if (bar["close"]/bars[i-5]["close"]-1)*100>1.5:return False
    # Strong candle, not a thin wick on breakout.
    span=bar["high"]-bar["low"]
    return span>0 and (bar["close"]-bar["low"])/span>=.65
