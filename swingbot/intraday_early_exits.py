"""Causal, predeclared early-exit hypotheses for BTC/ETH day trading.

The simulator invokes these at bar i OPEN. Guards inspect ONLY historical
bars 0 through i-1 and the position's entry index/price. Never use
bar i high/low/close or data from i+1. Exits are speculative research.
"""
from __future__ import annotations
from statistics import mean
from .intraday_net_target import ExecutionCosts, net_profit_pct

POLICY_NAMES = ("unchanged", "fade_30m", "timeout_120m", "fade_or_timeout")


def fading_rise_30m(bars, i, position):
    """Exit a low-progress trade once a short run of candles weakens."""
    if i < 14 or i-position["entry_bar"] < 6:
        return False
    c0,c1,c2,c3=(bars[i-4]["close"],bars[i-3]["close"],
                 bars[i-2]["close"],bars[i-1]["close"])
    falling=c0>c1>c2>c3
    sma12=mean(b["close"] for b in bars[i-12:i])
    # Only consider a negative or barely positive roundtrip after model fees.
    weak_after_costs=net_profit_pct(
        position["entry_raw"],c3,ExecutionCosts())<=.0
    return falling and c3 < sma12 and weak_after_costs


def no_progress_120m(bars,i,position):
    """Exit 120min after entry if theoretical net PnL is not positive."""
    if i < 1 or i-position["entry_bar"] < 24:
        return False
    last=bars[i-1]["close"]
    return net_profit_pct(position["entry_raw"],last,ExecutionCosts())<0.


def choose_exit_guard(name):
    if name=="unchanged":return None
    if name=="fade_30m":return fading_rise_30m
    if name=="timeout_120m":return no_progress_120m
    if name=="fade_or_timeout":
        return lambda bars,i,pos: (
            fading_rise_30m(bars,i,pos) or no_progress_120m(bars,i,pos))
    raise ValueError("Unrecognized predeclared exit candidate")
