"""Causal next-open protective early-exit hypotheses, no future lookahead.

None of these replaces the +1% net full-position TP, 1.5% stop, or
21:55 Helsinki close. Early exit triggers only from completed 5m bars
BEFORE next candle's open. They are unproven trial alternatives.
"""
from __future__ import annotations
from statistics import mean
from .intraday_net_target import ExecutionCosts, net_profit_pct


def momentum_fade(bars,i,position):
    """After >=20m, leave a losing momentum reversal at next open.

    All values through index i-1 only; no intrabar future observations.
    """
    entry=position["entry_bar"]
    if i-entry<4:return False
    if i<23:return False
    closes=[bars[j]["close"] for j in range(i-4,i)]
    return (closes[0]>closes[1]>closes[2]>closes[3]
            and closes[-1]<position["entry_raw"]
            and closes[-1]<mean(b["close"] for b in bars[i-20:i]))


def losing_after_ninety_minutes(bars,i,position):
    """If 90 minutes elapsed and momentum lost, avoid holding weak trade."""
    if i-position["entry_bar"]<18 or i<23:return False
    closes=[x["close"] for x in bars[i-20:i]]
    return (closes[-1]<position["entry_raw"]
            and closes[-1]<mean(closes)
            and closes[-1]<closes[-4])


def none(_bars,_i,_position):
    return False


GUARDS={
    "baseline":None,
    "fade_3_descending":momentum_fade,
    "losing_after_90min":losing_after_ninety_minutes,
}
