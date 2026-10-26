"""Cross-era research for different BTC/ETH entry families.

2021-23 and 2024-26 each start a separate shared 5000 EUR cash account.
No optimizations or live trading; tests are retrospective and previous
history has been examined.
"""
from __future__ import annotations
from .alternative_entry_families import POLICIES,compute
from .positive_rules_5year import split_feeds
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts

def evaluate(parts,policy,costs):
    if policy not in POLICIES:raise ValueError("Unknown policy")
    cash=5000.; days=set(); buys=tp=stop=flat=0
    for feed,_ in parts:
        cache={s:compute(feed[s]) for s in PAIRS}
        def signal(rows,i):
            s="BTC-EUR" if rows is feed["BTC-EUR"] else "ETH-EUR"
            return i in cache[s][policy]
        out=replay_one_per_day(feed,capital=cash,costs=costs,
            signal=signal,first_entry_index=160,
            previously_traded_days=days)
        cash=out["end_eur"]
        days.update(out["daily_trade_dates"])
        buys+=out["buys"];tp+=out["full_take_profits"]
        stop+=out["stop_exits"];flat+=out["session_end_exits"]
    return {"buys":buys,"full_tp":tp,"stops":stop,"day_flat":flat,
            "final_eur":round(cash,2),"pnl_eur":round(cash-5000,2)}

def study(prepared):
    windows=split_feeds(prepared)
    rows=[]
    double=ExecutionCosts(50,50,30,30)
    for name in POLICIES:
        train=evaluate(windows["train"],name,ExecutionCosts())
        train_stress=evaluate(windows["train"],name,double)
        qualifies=(train["buys"]>=15 and train["pnl_eur"]>0 and
                   train_stress["pnl_eur"]>0)
        rows.append({"name":name,"train":train,
            "train_double":train_stress,"train_qualifies":qualifies})
    for row in rows:
        name=row["name"]
        row["later"]=evaluate(windows["later"],name,ExecutionCosts())
        row["later_double"]=evaluate(windows["later"],name,double)
        row["both_periods_positive"]=(row["train_qualifies"] and
            row["later"]["buys"]>=15 and row["later"]["pnl_eur"]>0
            and row["later_double"]["pnl_eur"]>0)
    return {
        "mode":"READ_ONLY_NEW_ENTRY_FAMILIES",
        "train":"2021-2023","later":"2024-2026",
        "starting_eur_per_period":5000,
        "candidates":rows,
        "approved":[r["name"] for r in rows if r["both_periods_positive"]],
        "live_trading":False,
        "warning":"This is previously inspected historical data, NOT an "
            "independent out-of-sample prediction. Flat cash-only baseline "
            "is 0 return, not positive performance. Estimated fills/fees, "
            "missing candles and tax exclusion affect results."
    }
