"""Conservative risk/regime overlay, separate from unchanged E paper trading.

Uses *completed* prior 5m bars to classify momentum before next-open entry.
Risk filter is not a source of alpha on its own. No broker credentials.
"""
from __future__ import annotations
from math import isfinite
from statistics import mean
from .intraday_entry_filters import filtered_buy_signal
from .intraday_net_target import ExecutionCosts, buy_total_cost

def regime(bars, i):
    if i < 100:
        return "INSUFFICIENT"
    closes=[b["close"] for b in bars[i-100:i+1]]
    fast=mean(closes[-20:])
    medium=mean(closes[-50:])
    slow=mean(closes[-100:])
    if fast>medium>slow and closes[-1]>fast:
        return "UPTREND"
    if fast<medium<slow and closes[-1]<fast:
        return "DOWNTREND"
    return "SIDEWAYS"

def regime_buy_signal(bars,i):
    return regime(bars,i)=="UPTREND" and filtered_buy_signal(bars,i)

def max_affordable_units(cash, equity, entry_raw_price, *,
                         risk_budget_pct=.25, max_position_pct=20.,
                         stop_raw_price=None,
                         costs=ExecutionCosts()):
    """Position fraction capped by cash, size ceiling, and nominal stop-risk.

    Uses NET entry cost and NET expected stop sale; never borrow.
    Default 0.25% account-at-risk and 20% single position maximum.
    """
    if not all(isfinite(x) for x in (cash,equity,entry_raw_price,risk_budget_pct,
                                    max_position_pct)):
        raise ValueError("Nonfinite inputs")
    if not (cash>0 and equity>0 and entry_raw_price>0 and
            0<risk_budget_pct<=2 and 0<max_position_pct<=100):
        raise ValueError("Invalid balance or risk budget")
    if stop_raw_price is None or not (isfinite(stop_raw_price) and
                                      0<stop_raw_price<entry_raw_price):
        raise ValueError("Expected stop below entry required")
    per_unit=buy_total_cost(entry_raw_price,1,costs)
    from .intraday_net_target import sell_net_proceeds
    downside=max(0,per_unit-sell_net_proceeds(stop_raw_price,1,costs))
    if downside<=0: raise ValueError("Risk must be positive")
    return min(cash/per_unit,
               equity*(max_position_pct/100)/per_unit,
               equity*(risk_budget_pct/100)/downside)
