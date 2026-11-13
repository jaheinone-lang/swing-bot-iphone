"""Search for globally positive BTC/ETH research rules with explicit rejection.

Fixed six hypotheses; 2021-2023 training, 2024-2026 chronological check.
One shared 5000EUR spot account per phase, max 1 Finland-local entry/day.
No use of future candles for a signal; no optimistic compounding across
a train/test boundary. Chronological test already seen in other studies:
this is descriptive cross-regime stress, NOT a pristine unseen holdout.
"""
from __future__ import annotations
from datetime import datetime,timezone
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts
from .five_year_fast_signals import generate_frozen_signals
from .five_year_daytrade import DOUBLE_COSTS

SPLIT_MS=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
# Name, asset restriction, frozen signal, raw stop, full net TP
POLICIES=(
    ("reference_both",None,"morning_strict",1.5,1.),
    ("eth_only", "ETH-EUR","morning_strict",1.5,1.),
    ("btc_only", "BTC-EUR","morning_strict",1.5,1.),
    ("tight_stop",None,"morning_strict",.8,1.),
    ("wide_stop",None,"morning_strict",2.5,1.),
    ("higher_net_target",None,"morning_strict",1.5,2.),
)


def split_feeds(prepared):
    halves={"train":[],"later":[]}
    # Never transfer position or future OHLC across 2024. Indicators
    # may use up to 160 preceding completed bars when contiguous.
    for feed,caches in prepared:
        timestamps=[x["timestamp_ms"] for x in feed[PAIRS[0]]]
        idx=next((i for i,t in enumerate(timestamps) if t>=SPLIT_MS),len(timestamps))
        parts=[
            ("train",feed[PAIRS[0]][:idx],feed[PAIRS[1]][:idx],0),
            ("later",feed[PAIRS[0]][max(0,idx-160):],
             feed[PAIRS[1]][max(0,idx-160):],max(0,160-idx)),
        ] if 0<idx<len(timestamps) else [
            ("train" if idx==len(timestamps) else "later",
             feed[PAIRS[0]],feed[PAIRS[1]],0)
        ]
        for period,btc,eth,_ in parts:
            if len(btc)<180:continue
            sub={"BTC-EUR":btc,"ETH-EUR":eth}
            # Reset cached signals at the boundary; no future use, with
            # 160 past bars allowed for warmup on boundary-spanning segment.
            fresh={s:generate_frozen_signals(sub[s]) for s in PAIRS}
            halves[period].append((sub,fresh))
    return halves


def simulate(windows,rule,fees):
    label,asset,signal_key,stop,target=rule
    cash=5000.
    used=set()
    count=tp=stops=evening=0
    for feed,caches in windows:
        def eligible(bars,i):
            symbol="BTC-EUR" if bars is feed["BTC-EUR"] else "ETH-EUR"
            return (asset is None or symbol==asset) and i in caches[symbol][signal_key]
        out=replay_one_per_day(
            feed,capital=cash,costs=fees,signal=eligible,
            first_entry_index=160,previously_traded_days=used,
            stop_pct=stop,net_target_pct=target)
        cash=out["end_eur"]
        used.update(out["daily_trade_dates"])
        count+=out["buys"]
        tp+=out["full_take_profits"]
        stops+=out["stop_exits"]
        evening+=out["session_end_exits"]
    return {"trades":count,"take_profits":tp,"stops":stops,
            "day_flat":evening,"end_eur":round(cash,2),
            "pnl_eur":round(cash-5000,2)}


def search(prepared):
    halves=split_feeds(prepared)
    if not halves["train"] or not halves["later"]:
        raise ValueError("Historical training/later data not independently available")
    result=[]
    for policy in POLICIES:
        a=simulate(halves["train"],policy,ExecutionCosts())
        b=simulate(halves["train"],policy,DOUBLE_COSTS)
        accepted=a["trades"]>=15 and a["pnl_eur"]>0 and b["pnl_eur"]>0
        result.append({"policy":policy[0],"train":a,"train_double":b,
                       "train_qualifies":accepted})
    eligible=[r for r in result if r["train_qualifies"]]
    chosen=max(eligible,key=lambda r:r["train_double"]["pnl_eur"])["policy"] if eligible else None
    # Later outcomes are reported for transparency, NEVER used for selection.
    for row,policy in zip(result,POLICIES):
        row["later"]=simulate(halves["later"],policy,ExecutionCosts())
        row["later_double"]=simulate(halves["later"],policy,DOUBLE_COSTS)
        row["passes_all_periods"]=row["train_qualifies"] and (
            row["later"]["pnl_eur"]>0 and
            row["later_double"]["pnl_eur"]>0 and
            row["later"]["trades"]>=15)
    return {"mode":"RETROSPECTIVE_POSITIVE_WHOLE_ACCOUNT_RULE_SEARCH",
            "train":"2021-10-23 to 2023-12-31",
            "later":"2024-01-01 to 2026-10-22",
            "one_shared_eur_account_each_period":5000.,
            "selected_from_training_only":chosen,
            "qualified_across_both_periods":[r["policy"] for r in result
                                             if r["passes_all_periods"]],
            "rows":result,
            "deployment_approved":False,
            "limitations":"Older data evaluated for selection; newer years "
             "were previously used in research, so not independent OOS. "
             "Full 1pct or 2pct net TP targets before tax. Simulated fills, "
             "realized gaps may exceed stop, costs estimated. No real orders."}
