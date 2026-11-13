"""Tikkala-inspired US stock *research* setups; no copied proprietary rules.

Three independently defined candidate families from completed USD daily bars:
(1) liquid small-cap momentum, (2) failed gap-up breakout (research only,
    NO short sales or borrow assumption), (3) liquid large-cap 20d breakout.

Requires true split-adjusted full-market-volume OHLCV with point-in-time
market cap, actual spread, and per-instrument metadata to issue WATCH signals.
Alpaca IEX-only volume never qualifies as whole-US liquidity. No signal
grants paper or live trade authorization. Historical OHLC is observation,
NOT executable fills; no PnL or magical win probabilities generated.
"""
from __future__ import annotations
from datetime import date
from math import isfinite
from statistics import median,mean

FAMILIES=("small_cap_momentum","failed_gap_up","large_cap_breakout")
WATCH_ONLY="WATCH_ONLY_NO_ORDERS"

def scan(symbol,bars,*,as_of,market_cap_usd=None,
         consolidated_volume=False,split_adjusted=False,
         verified_spread_bps=None,borrow_locate_verified=False):
    """Return point-in-time candidate gates, never an executable order.

    bars: ordered DailyBar, 61+ full completed sessions, USD quotes.
    market_cap_usd: verified as of decision time, not today's cap in old test.
    """
    base={"symbol":symbol,"mode":"US_STOCK_RESEARCH_ONLY",
          "status":"REJECTED","family_signals":{k:False for k in FAMILIES},
          "paper_order_authorized":False,"live_order_authorized":False,
          "short_order_authorized":False,"borrow_locate_verified":
              bool(borrow_locate_verified),
          "reason":"Insufficient validated market data"}
    if not isinstance(symbol,str) or not symbol or not symbol.isascii():
        return base
    if not isinstance(as_of,date) or len(bars)<201:
        return base
    if not split_adjusted or not consolidated_volume:
        base["reason"]="Split-adjusted, consolidated US volume required"
        return base
    if (market_cap_usd is None or not isfinite(market_cap_usd)
        or market_cap_usd<=0):
        base["reason"]="Historical point-in-time market cap unverified"
        return base
    if (verified_spread_bps is None or not isfinite(verified_spread_bps)
        or verified_spread_bps<0 or verified_spread_bps>30):
        base["reason"]="Verified liquid spread <=30 bps required"
        return base
    if (bars[-1].day>=as_of or (as_of-bars[-1].day).days>7 or
        any(a.day>=b.day for a,b in zip(bars,bars[1:]))):
        base["reason"]="Stale, future, missing or disordered last completed session"
        return base
    try:
        if any(not all(isfinite(v) and v>0 for v in
                      (b.open,b.high,b.low,b.close,b.volume)) or
               not (b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high)
               for b in bars):
            return base
        last,prev=bars[-1],bars[-2]
        dollar_turnover=median(b.close*b.volume for b in bars[-20:])
        volume_ratio=last.volume/median(b.volume for b in bars[-21:-1])
        gap=last.open/prev.close-1
        intraday=last.close/last.open-1
        hi20=max(b.high for b in bars[-21:-1])
        sma50=mean(b.close for b in bars[-50:])
        sma200=mean(b.close for b in bars[-200:])
    except (ZeroDivisionError,ValueError,TypeError):
        return base
    # Conservative market-cap segmentation; labels not ticker stereotypes.
    small=300_000_000<=market_cap_usd<=2_000_000_000
    large=market_cap_usd>=10_000_000_000
    liquid=dollar_turnover>=10_000_000
    small_breakout=(small and liquid and last.close>hi20
        and .03<=gap<=.15 and .04<=intraday<=.18
        and volume_ratio>=2 and last.close>2)
    # Classic failed gap, downside WATCH only. Shortability cannot be
    # inferred from borrow_locate_verified; locate, fees, circuit breakers,
    # restricted instruments and intraday timestamps still necessary.
    failed_gap=(small and liquid and .05<=gap<=.30
        and last.close<last.open and last.close<prev.close
        and volume_ratio>=2 and last.close>2)
    big_trend=(large and liquid and last.close>hi20
        and last.close>sma50>sma200 and
        .03<=last.close/bars[-61].close-1<=.50)
    flags={"small_cap_momentum":small_breakout,
           "failed_gap_up":failed_gap,
           "large_cap_breakout":big_trend}
    base.update({
        "status":WATCH_ONLY,"reason":"Read-only candidate classification",
        "family_signals":flags,
        "observation_day":last.day.isoformat(),
        "average_dollar_turnover_usd":round(dollar_turnover,2),
        "volume_ratio":round(volume_ratio,3),
        "gap_pct":round(gap*100,2),
        "return_open_to_close_pct":round(intraday*100,2),
        "market_cap_bucket":"SMALL" if small else "LARGE" if large else "OTHER",
        "data_quality":"CONSOLIDATED_SPLIT_ADJUSTED_VERIFIED",
        "requires_independent_backtest":True,
        "requires_real_spreads_borrow_fx_and_fills":True,
    })
    return base
