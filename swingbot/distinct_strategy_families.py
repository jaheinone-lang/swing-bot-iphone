"""Compare genuinely distinct 5m strategies against cash and legacy setup.

Two predefined alternative entry families versus morning_strict breakout.
Fixed stop 1.5%, 100% full net 1% TP, one Finnish day trade, common EUR5000
cash per scenario, no leverage. Uses same fee/slippage normal and 2x.
Separate 2021-23 and 2024-26 portfolio resets at test boundary.
2024-26 was previously explored; descriptive, NOT independent holdout.
"""
from __future__ import annotations
from .alternative_entry_families import compute
from .five_year_fast_signals import generate_frozen_signals
from .positive_rules_5year import split_feeds
from .intraday_net_target import ExecutionCosts
from .daytrade_one_per_day import PAIRS,replay_one_per_day

RULES=("cash_only","morning_strict","trend_continuation","mean_revert_uptrend")
STRESS=ExecutionCosts(50,50,30,30)

def run_period(windows,policy,costs=ExecutionCosts()):
    if policy not in RULES:raise ValueError("Unknown research rule")
    if policy=="cash_only":
        return {"trades":0,"take_profits":0,"stops":0,
                "ending_eur":5000.,"pnl_eur":0.}
    funds=5000.
    dates=set()
    buy_count=take_count=stop_count=0
    for feed,_ in windows:
        candidates={}
        for symbol in PAIRS:
            candidates[symbol]=(generate_frozen_signals(feed[symbol])["morning_strict"]
               if policy=="morning_strict" else compute(feed[symbol])[policy])
        signal=lambda bars,i: i in candidates[
            "BTC-EUR" if bars is feed["BTC-EUR"] else "ETH-EUR"]
        r=replay_one_per_day(feed,capital=funds,costs=costs,signal=signal,
                            first_entry_index=160,previously_traded_days=dates)
        funds=r["end_eur"]
        dates.update(r["daily_trade_dates"])
        buy_count+=r["buys"]
        take_count+=r["full_take_profits"]
        stop_count+=r["stop_exits"]
    return {"trades":buy_count,"take_profits":take_count,"stops":stop_count,
            "ending_eur":round(funds,2),"pnl_eur":round(funds-5000,2)}

def study(prepared):
    divided=split_feeds(prepared)
    rows=[]
    for name in RULES:
        old=run_period(divided["train"],name)
        old2=run_period(divided["train"],name,STRESS)
        later=run_period(divided["later"],name)
        later2=run_period(divided["later"],name,STRESS)
        qualifies=(old["trades"]>=15 and old["pnl_eur"]>0 and
                   old2["pnl_eur"]>0 and later["trades"]>=15 and
                   later["pnl_eur"]>0 and later2["pnl_eur"]>0)
        rows.append({"rule":name,"train":old,"train_2x":old2,
                     "later":later,"later_2x":later2,
                     "meets_all_historical_thresholds":qualifies})
    return {"mode":"READ_ONLY_DISTINCT_STRATEGY_FAMILIES",
            "rules":rows,
            "positively_qualified_history":[r["rule"] for r in rows
                                           if r["meets_all_historical_thresholds"]],
            "cash_benchmark_return_eur":0,
            "live_approved":False,
            "warning":"Already-explored history, not independent validation. "
                      "No actual exchange fills or income taxes. "
                      "Cash benchmark zero excludes inflation and yield."}
