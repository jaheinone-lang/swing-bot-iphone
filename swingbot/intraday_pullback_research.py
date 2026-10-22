"""Fixed pullback vs breakout intraday 5-minute research, no live orders.

Simple proof-of-concept; all entries filled on next bar only. 7-day
historical dataset remains small and not evidence of future profitability.
"""
from __future__ import annotations
import json
from statistics import mean
from .bitvavo_intraday_history import historical_five_minute
from .intraday_entry_filters import filtered_buy_signal
from .intraday_research import replay
from .intraday_net_target import ExecutionCosts

def pullback_signal(bars, i):
    """Confirmed recent breakout, then recovery from a shallow 20-bar pullback."""
    if i<80:
        return False
    now=bars[i]
    look=bars[i-80:i]
    fast=mean(x["close"] for x in bars[i-20:i])
    slow=mean(x["close"] for x in bars[i-50:i])
    if not (fast>slow and now["close"]>fast and
            now["close"]>now["open"]):
        return False
    # Earlier confirmed breakout: the prior 2..6 bars must have
    # closed above their then-prev 20-bar highs (never future).
    confirmed=False
    for k in range(i-6,i-1):
        if bars[k]["close"]>max(x["high"] for x in bars[k-20:k]):
            confirmed=True
            break
    if not confirmed or now["low"]>fast:
        return False
    prior_vol=mean(x["volume"] for x in bars[i-20:i])
    return prior_vol>0 and now["volume"]>=prior_vol*.80


def seven_day_comparison():
    report={"mode":"NO_ORDERS_7D_FIXED_PULLBACK_COMPARISON","markets":{}}
    for pair in ("BTC-EUR","ETH-EUR","SOL-EUR"):
        prices=historical_five_minute(pair,days=7)
        # Allow 80 completed bars for indicators and freeze comparison on
        # first 60% chronological train period vs later 40% untouched.
        cut=int(len(prices)*.60)
        evaluation={}
        for label,segment,eligible in (
            ("train",prices[:cut],80),
            ("later",prices[cut-80:],80),
        ):
            models={}
            for strategy_name,signal in (
                ("original",None),
                ("volume_confirmed",filtered_buy_signal),
                ("pullback",pullback_signal),
            ):
                normal=replay(segment,signal=signal,first_entry_index=eligible)
                stress=replay(segment,signal=signal,first_entry_index=eligible,
                              costs=ExecutionCosts(50,50,30,30))
                models[strategy_name]={
                    "eur":normal["estimated_pnl_eur"],
                    "double_cost_eur":stress["estimated_pnl_eur"],
                    "buys":normal["buys"],
                    "half_take_profit":normal["half_take_profits"],
                    "max_drawdown_pct":normal["max_mark_to_market_drawdown_pct"],
                }
            evaluation[label]=models
        report["markets"][pair]=evaluation
    report["important"]="Short 7-day study designed after earlier history; not true independent validation. Holdout is descriptive and must not be used to retroactively tune and claim future profit. No income taxes or actual fill checks. No broker orders."
    return report

def main():
    print(json.dumps(seven_day_comparison(),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
