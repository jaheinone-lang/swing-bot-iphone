"""5-year backtest of predeclared early exits vs frozen morning entries.

One pooled €5,000 spot BTC/ETH account; at most one Finnish day trade;
full +1% after-cost TP, 1.5% raw stop, 21:55 Finland hard flat.
Identical morning_strict ENTRY times per dataset / scenario, but subsequent
capital changes may alter nominal trade sizes.
Exits are evaluated at next 5m OPEN on data through previous close only.
Period years 2021-23 old exploration / 2024-26 descriptive later results.
All time periods were historically available before this research and
prior research saw 2024-26, so no true prospective holdout is asserted.
"""
from __future__ import annotations
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_early_exits import POLICY_NAMES,choose_exit_guard
from .intraday_net_target import ExecutionCosts

STRESS=ExecutionCosts(50,50,30,30)


def evaluate(prepared, policy, costs):
    if policy not in POLICY_NAMES:
        raise ValueError("Unknown exit research policy")
    guard=choose_exit_guard(policy)
    capital=5000.
    days=set()
    yearly={str(y):{
        "buys":0,"complete_profit_sales":0,"stop_sales":0,
        "early_exits":0,"session_end_sales":0,
        "net_realized_eur":0.
    } for y in range(2021,2027)}
    counts={"buys":0,"full_tp":0,"stops":0,
            "early_exits":0,"day_flat":0,"gap_exits":0}
    for feed,caches in prepared:
        if len(feed[PAIRS[0]])<162:
            continue
        # Our previously frozen strict morning ENTRY selection.
        signal=lambda bars,i: i in caches[
            "BTC-EUR" if bars is feed["BTC-EUR"] else "ETH-EUR"]["morning_strict"]
        res=replay_one_per_day(
            feed,capital=capital,costs=costs,signal=signal,
            first_entry_index=160,previously_traded_days=days,
            exit_guard=guard)
        capital=res["end_eur"]
        days.update(res["daily_trade_dates"])
        counts["buys"]+=res["buys"]
        counts["full_tp"]+=res["full_take_profits"]
        counts["stops"]+=res["stop_exits"]
        counts["early_exits"]+=res["early_exits"]
        counts["day_flat"]+=res["session_end_exits"]
        counts["gap_exits"]+=res["end_segment_forced_exits"]
        for e in res["events"]:
            key=e["day_local"][:4]
            if e["type"]=="BUY":
                yearly[key]["buys"]+=1
            else:
                yearly[key]["net_realized_eur"]+=e["net_eur_before_tax"]
                field={
                    "FULL_TP":"complete_profit_sales",
                    "STOP":"stop_sales",
                    "ENTRY_BAR_STOP":"stop_sales",
                    "EARLY_EXIT":"early_exits",
                    "DAY_FLAT":"session_end_sales"
                }.get(e["type"])
                if field:
                    yearly[key][field]+=1
    for row in yearly.values():
        row["net_realized_eur"]=round(row["net_realized_eur"],2)
    return {
        "initial_eur":5000.,
        "ending_eur":round(capital,2),
        "profit_eur":round(capital-5000,2),
        "return_pct":round((capital/5000-1)*100,3),
        "trade_outcomes":counts,
        "yearly":yearly,
        "one_entry_per_finnish_calendar_day":True,
        "live_order_count":0,
    }


def study(prepared):
    result={}
    for policy in POLICY_NAMES:
        result[policy]={
            "normal_costs":evaluate(prepared,policy,ExecutionCosts()),
            "double_costs":evaluate(prepared,policy,STRESS),
        }
    # There is no automated picking of a "winner" from already explored data.
    return {
        "mode":"EARLY_EXIT_FIVE_YEAR_READ_ONLY",
        "entry_rule":"morning_strict",
        "prespecified_exit_policies":POLICY_NAMES,
        "results":result,
        "automatically_approved":False,
        "disclaimer":"All results are retrospective with estimated 5m candle "
            "fills; earlier years and later years have been seen already. "
            "Partial history gaps reset inventory using last observed close. "
            "Early exit can worsen net returns due to costs. No tax, orders, "
            "or live deployment.",
    }
