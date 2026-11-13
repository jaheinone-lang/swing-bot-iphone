"""Compare two CAUSAL early exits on 5y BTC/ETH morning-strict trading.

All entry criteria remain FROZEN from prior study. One pooled €5,000
spot account; <=1 entry/Finland day; full +1% AFTER fee target stays intact.
Only new dimension: waiting for a hard stop/21:55 vs exiting at NEXT OPEN
after confirmed weak momentum, or after 90m weak holding.

All policy ideas were designed after seeing some historical data, so any
result is exploratory/hypothesis-generating, NOT validation for live funds.
"""
from __future__ import annotations
from datetime import datetime,timezone
import json

from .bitvavo_five_year import five_year_history
from .five_year_daytrade import START,END,align_segments,cached_segments,simulate,DOUBLE_COSTS
from .daytrade_exit_guards import GUARDS
from .intraday_net_target import ExecutionCosts


def evaluate(*,dataset=None,coverage=None):
    if dataset is None:
        dataset,coverage=five_year_history(start=START,end=END)
    sections,common=align_segments(dataset)
    prepared=cached_segments(sections)
    rule="morning_strict"
    outcomes={}
    for label,guard in GUARDS.items():
        baseline=simulate(prepared,rule,costs=ExecutionCosts(),exit_guard=guard)
        stress=simulate(prepared,rule,costs=DOUBLE_COSTS,exit_guard=guard)
        outcomes[label]={"normal":baseline,"double_costs":stress}
    prior=outcomes["baseline"]["normal"]["net_profit_eur"]
    for name,result in outcomes.items():
        result["improvement_vs_no_early_exit_eur"]=round(
            result["normal"]["net_profit_eur"]-prior,2)
        result["normal_2021_2025_pnl"]=round(
            sum(result["normal"]["annual"][str(yr)]["net_profit_eur"]
                for yr in range(2021,2026)),2)
        result["normal_2026_pnl"]=result["normal"]["annual"]["2026"][
            "net_profit_eur"]
    return {
        "mode":"READ_ONLY_CAUSAL_EARLY_EXIT_RESEARCH",
        "start_utc":START.isoformat(),
        "end_utc_exclusive":END.isoformat(),
        "data_coverage":coverage,
        "common_bars":common,
        "eligible_bars":sum(len(x["BTC-EUR"]) for x in sections),
        "contiguous_sections":len(sections),
        "frozen_entry":"morning_strict",
        "exits":{
            "baseline":"1.5% stop, full +1% net TP, 21:55 flat",
            "fade_3_descending":"After 20m, 3 declining completed 5m closes, below entry and 20SMA -> sell NEXT bar open",
            "losing_after_90min":"After 90m with last completed price below entry, below 20SMA, below 15m-ago -> sell NEXT bar open",
        },
        "results":outcomes,
        "live_approval":False,
        "notes":[
            "No real fills, orders, new wallet or brokerage connections.",
            "One exit order per simulated position, same one/day entry rule.",
            "Early exits may realize loss even when the hard stop was not reached; "
            "all round-trip modeled costs still apply.",
            "2026 data previously inspected; no independent forward validation.",
            "Candle OHLC cannot establish intrabar order sequence or actual limit fill.",
            "Gaps force liquidation and indicator warmups; taxes omitted.",
            "Profitability and stress resilience must be assessed, not just number of stops.",
        ]
    }


if __name__=="__main__":
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
