"""Research-only causal trend-regime variants of fixed morning_strict.

Pre-entry features are computed only from the completed signal bar.
Replays are genuine pooled EUR 5000 portfolio simulations, not summing
the original subset PnL. Chronological eras reset cash independently.
Thresholds were explored using existing 50 trades; no OOS claim.
"""
from __future__ import annotations
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts
from .positive_rules_5year import split_feeds

POLICIES=("original","trend_ge_2pct","pre_rise_le_055","trend2_rise_le_065")
STRESS=ExecutionCosts(50,50,30,30)

def allowed(bars,i,name):
    if name=="original":return True
    close=bars[i]["close"]
    old=sum(x["close"] for x in bars[i-143:i-95])/48
    newer=sum(x["close"] for x in bars[i-47:i+1])/48
    trend=(newer/old-1)*100
    rise=(close/bars[i-3]["close"]-1)*100
    return (
        trend>=2 if name=="trend_ge_2pct" else
        rise<=.55 if name=="pre_rise_le_055" else
        trend>=2 and rise<=.65
    )

def replay(windows,name,costs=ExecutionCosts()):
    if name not in POLICIES:raise ValueError("Unknown regime")
    funds=5000.; dates=set();buys=tp=stops=0
    for feed,caches in windows:
        def signal(rows,i):
            symbol="BTC-EUR" if rows is feed["BTC-EUR"] else "ETH-EUR"
            return i in caches[symbol]["morning_strict"] and allowed(rows,i,name)
        trial=replay_one_per_day(feed,capital=funds,costs=costs,signal=signal,
            first_entry_index=160,previously_traded_days=dates)
        funds=trial["end_eur"];dates.update(trial["daily_trade_dates"])
        buys+=trial["buys"];tp+=trial["full_take_profits"]
        stops+=trial["stop_exits"]
    return {"trades":buys,"targets":tp,"stops":stops,
            "pnl_eur":round(funds-5000,2),"ending_eur":round(funds,2)}

def study(prepared):
    eras=split_feeds(prepared)
    rows=[]
    for name in POLICIES:
        a=replay(eras["train"],name);b=replay(eras["later"],name)
        c=replay(eras["train"],name,STRESS);d=replay(eras["later"],name,STRESS)
        rows.append({"rule":name,"early":a,"later":b,
                     "early_double":c,"later_double":d,
                     "all_eras_positive":all(x["pnl_eur"]>0 for x in (a,b,c,d)),
                     "minimum_15_trades_both":a["trades"]>=15 and b["trades"]>=15})
    return {"mode":"CAUSAL_REPLAY_OF_POSTHOC_SCREENED_FILTERS",
            "rows":rows,"approved_live":False,
            "warning":"Thresholds chosen after looking at same 5-year data. "
                      "Portfolio replays account for different positions/cash "
                      "but cannot validate forward predictive performance."}
