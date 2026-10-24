"""150-day BTC/ETH historical buy timing diagnostics with 90d/60d split.

Uses *only completed earlier candles* for entry features. Reports actual
historical model entries that hit +1% net vs stops / compulsory day close.
Studies seven pre-declared entry rules with pooled €5k cash, one trade per
Helsinki day, one full-position TP, stop and 21:55 hard-flat.

Train-only qualification is never based on the later-period results.
Past historical data has been inspected in earlier work, so holdout is
chronological but not independent of the overall research project.
READ-ONLY. No market orders, no broker API calls, no account mutation.
"""
from __future__ import annotations

import json
from datetime import datetime
from statistics import mean

from .bitvavo_intraday_history import historical_five_minute
from .btc_eth_quality_gate import quality_buy_signal
from .daytrade_one_per_day import (
    PAIRS, confirmed_upward_move, local_time, replay_one_per_day,
    ENTRY_START, ENTRY_CUTOFF,
)
from .five_month_exit_research import _period_windows
from .intraday_net_target import ExecutionCosts

DOUBLE=ExecutionCosts(50,50,30,30)
POLICIES=(
    "confirmed_reference",
    "confirmed_09_to_14",
    "confirmed_14_to_20",
    "confirmed_high_volume",
    "confirmed_moderate_impulse",
    "confirmed_steep_trend",
    "quality_high_volume",
)


def candle_features(bars, i):
    """Features observable at decision timestamp, never after it."""
    if i < 160:
        raise ValueError("160 completed bars of lookback required")
    close=bars[i]["close"]
    volumes=[b["volume"] for b in bars[i-20:i]]
    baseline=mean(volumes)
    recent=mean(x["close"] for x in bars[i-48:i])
    earlier=mean(x["close"] for x in bars[i-144:i-96])
    rise=(close/bars[i-3]["close"]-1)*100
    bar=bars[i]
    return {
        "rise_15m_pct":round(rise,4),
        "trend_4h_vs_older_pct":round((recent/earlier-1)*100,4),
        "relative_volume":round(bar["volume"]/baseline,4) if baseline>0 else 0.,
        "bar_body_pct":round((bar["close"]/bar["open"]-1)*100,4),
        "signal_local_hour":local_time(bar["timestamp_ms"]).hour,
        "signal_local":local_time(bar["timestamp_ms"]).isoformat(),
    }


def accepts(policy, features, *, quality, confirmed, next_entry_hour):
    """Decide from cached past-only signal data; never future OHLC."""
    if policy not in POLICIES:
        raise ValueError("Unknown predeclared entry policy")
    if not (9 <= next_entry_hour < 20):
        return False
    if policy == "quality_high_volume":
        return quality and features["relative_volume"]>=1.6
    if not confirmed:
        return False
    if policy == "confirmed_reference":
        return True
    if policy == "confirmed_09_to_14":
        return 9<=next_entry_hour<14
    if policy == "confirmed_14_to_20":
        return 14<=next_entry_hour<20
    if policy == "confirmed_high_volume":
        return features["relative_volume"]>=1.6
    if policy == "confirmed_moderate_impulse":
        return .12<=features["rise_15m_pct"]<=.45
    if policy == "confirmed_steep_trend":
        return features["trend_4h_vs_older_pct"]>=1.
    raise AssertionError("Unhandled policy")


def make_caches(windows):
    """Cache truth for all policies once per observed segment and asset."""
    caches={}
    for section,_first,_eligible in windows:
        for symbol in PAIRS:
            bars=section[symbol]
            cached={}
            for i in range(160,len(bars)-1):
                nxt=local_time(bars[i+1]["timestamp_ms"])
                hour=nxt.hour
                if not 9<=hour<20:
                    continue
                if not quality_buy_signal(bars,i):
                    continue
                feats=candle_features(bars,i)
                confirmed=confirmed_upward_move(bars,i)
                for policy in POLICIES:
                    if accepts(policy,feats,quality=True,
                               confirmed=confirmed,next_entry_hour=hour):
                        # Inner dict holds features, accessible only after a
                        # signal is found. Future price isn't inspected.
                        cached.setdefault(policy,{})[i]=feats
            caches[id(bars)]=cached
    return caches


def _run_period(windows,caches,policy,fees,*,collect=False):
    cash=5000.
    buys=full_tp=stops=flat=0
    dates=set()
    examples=[]
    for section,first,_eligible in windows:
        # All decisions refer to cached past-only entries, never to a
        # price bar past the decision timestamp.
        signal=lambda bars,i: i in caches[id(bars)].get(policy,{})
        trial=replay_one_per_day(
            section,capital=cash,costs=fees,signal=signal,
            first_entry_index=first,previously_traded_days=dates)
        cash=trial["end_eur"]
        buys+=trial["buys"]
        full_tp+=trial["full_take_profits"]
        stops+=trial["stop_exits"]
        flat+=trial["session_end_exits"]
        dates.update(trial["daily_trade_dates"])
        if collect:
            # Exactly one buy per Finland day; each BUY is followed by
            # precisely one exit from that position in the event sequence.
            events=trial["events"]
            for j,event in enumerate(events):
                if event["type"]!="BUY":
                    continue
                matches=[
                    e for e in events[j+1:]
                    if e.get("type") in (
                        "FULL_TP","STOP","ENTRY_BAR_STOP",
                        "DAY_FLAT","END_OF_OBSERVED_SEGMENT")
                    and e.get("symbol")==event["symbol"]
                    and e.get("day_local")==event["day_local"]
                ]
                if len(matches)!=1:
                    raise AssertionError("Every entry must have one exit")
                closed=matches[0]
                feats=caches[id(section[event["symbol"]])][policy].get(
                    event["bar"]-1)
                if feats is None:
                    raise AssertionError("Unknown cached entry")
                examples.append({
                    "day":event["day_local"],
                    "buy_time_fi":local_time(
                        section[event["symbol"]][event["bar"]]
                        ["timestamp_ms"]).strftime("%Y-%m-%d %H:%M"),
                    "asset":event["symbol"],
                    "exit":closed["type"],
                    "net_eur":closed["net_eur_before_tax"],
                    "net_pct_on_position":closed[
                        "net_return_pct_on_position"],
                    "holding_minutes":closed["holding_minutes"],
                    "entry_raw":event["raw_entry"],
                    "target_raw":event["raw_target"],
                    "features":feats,
                })
    return {
        "final_eur":round(cash,2),
        "pnl_eur":round(cash-5000,2),
        "pnl_pct":round((cash/5000-1)*100,2),
        "buys":buys,
        "full_target_sales":full_tp,
        "stops":stops,
        "evening_exits":flat,
        "distinct_days":len(dates),
        "sample_trades":examples if collect else None,
    }


def audit(days=150):
    raw={sym:historical_five_minute(
        sym,days=days,require_complete=False) for sym in PAIRS}
    by_ms={sym:{b["timestamp_ms"]:b for b in raw[sym]} for sym in PAIRS}
    end=min(max(by_ms[s]) for s in PAIRS)
    split_ms=end-60*288*300000
    windows,common,segments=_period_windows(by_ms,split_ms=split_ms)
    if not windows["train"] or not windows["later"]:
        raise ValueError("Not enough observed contiguous training and later bars")
    caches={period:make_caches(windows[period])
            for period in ("train","later")}
    candidates=[]
    for policy in POLICIES:
        train=_run_period(windows["train"],caches["train"],
                          policy,ExecutionCosts())
        train_stress=_run_period(windows["train"],caches["train"],
                                 policy,DOUBLE)
        qualifies=(
            train["buys"]>=12 and train["pnl_eur"]>0 and
            train_stress["pnl_eur"]>0)
        candidates.append({
            "policy":policy,"train":{k:v for k,v in train.items()
                                   if k!="sample_trades"},
            "train_2x_costs":{
                k:v for k,v in train_stress.items() if k!="sample_trades"},
            "qualifies_on_train":qualifies,
        })
    qualified=[x for x in candidates if x["qualifies_on_train"]]
    selected=(
        max(qualified,key=lambda x:x["train_2x_costs"]["pnl_eur"])["policy"]
        if qualified else None
    )
    for entry in candidates:
        policy=entry["policy"]
        later=_run_period(windows["later"],caches["later"],
                          policy,ExecutionCosts(),collect=True)
        entry["later"]={k:v for k,v in later.items()
                        if k!="sample_trades"}
        stress=_run_period(windows["later"],caches["later"],
                           policy,DOUBLE)
        entry["later_2x_costs"]={k:v for k,v in stress.items()
                                  if k!="sample_trades"}
        if policy=="confirmed_reference":
            examples=later["sample_trades"]
    outcome_counts={}
    for record in examples:
        key=record["exit"]
        outcome_counts[key]=outcome_counts.get(key,0)+1
    gains=[x for x in examples if x["exit"]=="FULL_TP"]
    failures=[x for x in examples if x["exit"] in (
        "STOP","ENTRY_BAR_STOP","DAY_FLAT")]
    gains.sort(key=lambda x:x["buy_time_fi"],reverse=True)
    failures.sort(key=lambda x:x["buy_time_fi"],reverse=True)
    # Historical successes are NOT provided as knowable predictions;
    # every example describes a trade that was identifiable only by
    # an earlier signal, with its *future* outcome evaluated afterwards.
    return {
        "mode":"READ_ONLY_150D_TRAIN_THEN_LATER_BUY_TIMING_AUDIT",
        "training_days":days-60,"later_days":60,
        "common_observed_bars":common,
        "original_gap_segments":segments,
        "train_windows":len(windows["train"]),
        "later_windows":len(windows["later"]),
        "train_selected_entry_policy":selected,
        "candidates":candidates,
        "later_reference_outcomes":outcome_counts,
        "recent_later_success_examples":gains[:6],
        "recent_later_failure_examples":failures[:6],
        "approved_for_live":False,
        "warning":"Predeclared policies train-selected only, but previously "
                  "explored 150d data so NOT a truly independent holdout. "
                  "TP fills assumed when 5m candle high touches price. "
                  "Day-close liquidations, gaps, exchange charges/slippage "
                  "are modeled. Finnish taxes excluded. Not future advice.",
    }


if __name__=="__main__":
    print(json.dumps(audit(),ensure_ascii=False,indent=2))
