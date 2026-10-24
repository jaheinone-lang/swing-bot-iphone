"""Frozen read-only 5m BTC-EUR buy-entry comparisons with no future peeking.

Signals only from fully completed candles. Compare same historical data
with the untouched baseline replay. Do not auto-deploy selected variant.
"""
from __future__ import annotations
import json
from statistics import mean
from .bitvavo_intraday import intraday_candles
from .intraday_research import replay


def filtered_buy_signal(bars: list[dict], i: int) -> bool:
    """Prior 60-bar trend, 20-bar breakout, volume and ATR-range gate."""
    if i < 60:
        return False
    candle=bars[i]
    prior=bars[i-60:i]
    recent=prior[-20:]
    older=prior[-40:]
    close=candle["close"]
    # Current bar is *complete*. Entry happens at NEXT open via replay.
    if not (close>max(x["high"] for x in recent)
            and close>mean(x["close"] for x in prior[-20:])
            and mean(x["close"] for x in prior[-20:]) >
                mean(x["close"] for x in prior[-50:])):
        return False
    if not (candle["close"]>candle["open"] and
            candle["close"]-candle["open"] >=
                .35*(candle["high"]-candle["low"])):
        return False
    # Use volume only when supplied from the exchange; reject incomplete
    # volumes rather than silently calling this a volume filter.
    if not all("volume" in x and x["volume"]>=0 for x in recent+[candle]):
        return False
    baseline=mean(x["volume"] for x in recent)
    if baseline <= 0 or candle["volume"] < baseline*1.20:
        return False
    true_ranges=[]
    for j in range(i-13,i+1):
        b=bars[j]; previous=bars[j-1]["close"]
        true_ranges.append(max(b["high"]-b["low"],
                                abs(b["high"]-previous),
                                abs(b["low"]-previous)))
    atr_pct=mean(true_ranges)/close*100
    return .12 <= atr_pct <= 1.8


def compare(data: list[dict]) -> dict:
    control=replay(data)
    candidate=replay(data, signal=filtered_buy_signal)
    return {"mode":"READ_ONLY_HISTORICAL_COMPARISON",
            "bars":len(data),"baseline":control,"filtered":candidate,
            "caveat":"Short retrospective test; avoid selecting a model from "
                     "same observed data. Actual order fills unverified."}


def main():
    data=intraday_candles("BTC-EUR",limit=1000)
    print(json.dumps(compare(data),indent=2))


if __name__=="__main__":
    main()
