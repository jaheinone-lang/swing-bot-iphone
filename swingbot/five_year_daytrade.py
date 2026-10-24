"""Five calendar years BTC/ETH one-shared-account 5-minute spot backtest.

Explicit research window 2021-10-23T00:00Z to 2026-10-23T00:00Z.
One Finland-local trade/day, buys on next candle OPEN, full 1% net
take-profit, protective stop, compulsory 21:55 close, no leverage.
Three previously-specified entry rules, default and 2x cost conditions.

Market data is ONLY exact Bitvavo BTC-EUR/ETH-EUR observed 5-minute
candles; missing intervals are excluded, never generated or interpolated.
No live orders or existing paper account modifications.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

from .bitvavo_five_year import five_year_history
from .bitvavo_intraday_history import contiguous_observed_segments
from .daytrade_one_per_day import PAIRS, local_time, replay_one_per_day
from .five_year_fast_signals import generate_frozen_signals
from .intraday_net_target import ExecutionCosts

UTC=timezone.utc
START=datetime(2021,10,23,tzinfo=UTC)
END=datetime(2026,10,23,tzinfo=UTC)
DOUBLE_COSTS=ExecutionCosts(50,50,30,30)
RULES=("confirmed_reference","confirmed_morning","morning_strict")
YEAR_KEYS=("2021","2022","2023","2024","2025","2026")


def align_segments(dataset, *, min_bars=180):
    lookup={s:{x["timestamp_ms"]:x for x in dataset[s]} for s in PAIRS}
    common=sorted(set(lookup[PAIRS[0]]) & set(lookup[PAIRS[1]]))
    common_bars=[lookup[PAIRS[0]][t] for t in common]
    sections=contiguous_observed_segments(common_bars,min_bars=min_bars)
    combined=[]
    for section in sections:
        ts=[x["timestamp_ms"] for x in section]
        rows={s:[lookup[s][t] for t in ts] for s in PAIRS}
        combined.append(rows)
    return combined, len(common)


def cached_segments(segments):
    prepared=[]
    for feed in segments:
        caches={s:generate_frozen_signals(feed[s]) for s in PAIRS}
        prepared.append((feed,caches))
    return prepared


def simulate(prepared, rule, *, costs=ExecutionCosts(), start_eur=5000, exit_guard=None):
    if rule not in RULES:
        raise ValueError("Unknown frozen research rule")
    cash=float(start_eur)
    days_used=set()
    outcomes={"FULL_TP":0,"STOP":0,"ENTRY_BAR_STOP":0,
              "DAY_FLAT":0,"EARLY_EXIT":0,"END_OF_OBSERVED_SEGMENT":0}
    pnl_by_year={y:0. for y in YEAR_KEYS}
    buys_by_year={y:0 for y in YEAR_KEYS}
    tp_by_year={y:0 for y in YEAR_KEYS}
    trading_days_by_year={y:set() for y in YEAR_KEYS}
    years_with_gaps={y:0 for y in YEAR_KEYS}
    n_traded_bars=0
    segments_traded=0
    gain_amounts=[]
    win_durations=[]
    stop_durations=[]
    for feed,caches in prepared:
        first=160
        if len(feed[PAIRS[0]])<first+2:
            continue
        signal=lambda rows,i: i in caches["BTC-EUR" if rows is feed["BTC-EUR"] else "ETH-EUR"][rule]
        trial=replay_one_per_day(
            feed,capital=cash,costs=costs,signal=signal,
            first_entry_index=first,previously_traded_days=days_used,
            exit_guard=exit_guard)
        cash=trial["end_eur"]
        segments_traded+=1
        n_traded_bars+=len(feed[PAIRS[0]])
        days_used.update(trial["daily_trade_dates"])
        for e in trial["events"]:
            yr=e["day_local"][:4]
            if yr not in pnl_by_year:
                raise ValueError("Trade outside study years")
            if e["type"]=="BUY":
                buys_by_year[yr]+=1
                trading_days_by_year[yr].add(e["day_local"])
            else:
                outcomes[e["type"]]+=1
                pnl_by_year[yr]+=e["net_eur_before_tax"]
                if e["type"]=="FULL_TP":
                    gain_amounts.append(e["net_eur_before_tax"])
                    win_durations.append(e["holding_minutes"])
                    tp_by_year[yr]+=1
                elif e["type"] in ("STOP","ENTRY_BAR_STOP"):
                    stop_durations.append(e["holding_minutes"])
    cumulative=round(cash,2)
    return {
        "initial_eur":round(start_eur,2),
        "final_eur":cumulative,
        "net_profit_eur":round(cumulative-start_eur,2),
        "return_pct":round((cumulative/start_eur-1)*100,3),
        "buys":sum(buys_by_year.values()),
        "distinct_traded_fi_dates":len(days_used),
        "full_position_1pct_net_takeprofits":outcomes["FULL_TP"],
        "stop_exits":outcomes["STOP"]+outcomes["ENTRY_BAR_STOP"],
        "21_55_exits":outcomes["DAY_FLAT"],
        "early_exits":outcomes["EARLY_EXIT"],
        "data_gap_forced_exits":outcomes["END_OF_OBSERVED_SEGMENT"],
        "win_rate_pct_of_all_buys":round(
            outcomes["FULL_TP"]/max(1,sum(buys_by_year.values()))*100,2),
        "average_net_gain_on_full_tp_eur":round(
            sum(gain_amounts)/len(gain_amounts),2) if gain_amounts else None,
        "average_tp_holding_minutes":round(
            sum(win_durations)/len(win_durations),1) if win_durations else None,
        "average_stop_holding_minutes":round(
            sum(stop_durations)/len(stop_durations),1) if stop_durations else None,
        "annual":{y:{
            "trades":buys_by_year[y],
            "successful_full_tp":tp_by_year[y],
            "net_profit_eur":round(pnl_by_year[y],2),
            "trading_days":len(trading_days_by_year[y])
        } for y in YEAR_KEYS},
        "bars_processed_in_contiguous_sections":n_traded_bars,
        "segments":segments_traded,
    }


def five_year_study(*,dataset=None,coverage=None):
    if dataset is None:
        dataset,coverage=five_year_history(start=START,end=END)
    pieces,count=align_segments(dataset)
    if not pieces:
        raise ValueError("Not enough observed 5m candles for five-year simulation")
    prepared=cached_segments(pieces)
    result={}
    for rule in RULES:
        result[rule]={
            "base":simulate(prepared,rule),
            "double_trading_costs":simulate(
                prepared,rule,costs=DOUBLE_COSTS)}
    return {
        "mode":"FIVE_YEAR_5M_BTC_ETH_SHARED_EUR5000_READ_ONLY",
        "from_utc":START.isoformat(),
        "to_utc_exclusive":END.isoformat(),
        "history_metadata":coverage,
        "bars_common_both":count,
        "eligible_segments":len(pieces),
        "eligible_common_bars":sum(len(x[PAIRS[0]]) for x in pieces),
        "frozen_compared_rules":RULES,
        "results":result,
        "exit_management_research":__import__("swingbot.five_year_early_exit_research",fromlist=["study"]).study(prepared),
        "entry_pullback_research":__import__("swingbot.five_year_pullback_research",fromlist=["study"]).study(prepared),
        "fill_sensitivity_research":__import__("swingbot.five_year_fill_sensitivity",fromlist=["study"]).study(prepared),
        "trade_level_audit":__import__("swingbot.five_year_trade_audit",fromlist=["audit"]).audit(prepared),
        "selection":{
            "qualified_profitable_both_cost_assumptions":[
                k for k,v in result.items() if
                v["base"]["net_profit_eur"]>0 and
                v["double_trading_costs"]["net_profit_eur"]>0 and
                v["base"]["buys"]>=75
            ],
            "approved_for_real_money":False
        },
        "critical_caveats":[
            "The 2026 recent 150d part was ALREADY used to develop signal gates.",
            "Gapped exchange history is segmented, with assumed last-close "
            "liquidation and fresh technical-indicator warmup after data holes.",
            "100% of position TP modeled on 5m candle high, not verified fill.",
            "Only expected fees and slippage (and 2x stress), no income tax.",
            "One +1% net winning trade is NOT +1% of the entire EUR5000 equity.",
            "No broker authentication, live orders or changes to E shadow ledger."
        ],
    }


if __name__=="__main__":
    print(json.dumps(five_year_study(),ensure_ascii=False,indent=2))
