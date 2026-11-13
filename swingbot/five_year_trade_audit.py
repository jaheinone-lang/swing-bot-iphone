"""Read-only trade-level audit for frozen BTC/ETH 5-year daytrade rule.

No strategy changes. Use existing simulator event stream; every BUY
must have exactly one EXIT, including data-gap forced exits. Compare
actual realized trade PnL, rather than equating a raw 1.5% price stop
with net percentage loss.
"""
from __future__ import annotations
from collections import Counter
from statistics import mean,median
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts

RULE="morning_strict"
EXIT_TYPES=("FULL_TP","STOP","ENTRY_BAR_STOP","DAY_FLAT",
            "END_OF_OBSERVED_SEGMENT","EARLY_EXIT")


def audit(prepared,costs=ExecutionCosts()):
    cash=5000.
    days=set()
    ledger=[]
    for feed,caches in prepared:
        if len(feed[PAIRS[0]])<162:
            continue
        signal=lambda bars,i: i in caches[
            "BTC-EUR" if bars is feed["BTC-EUR"] else "ETH-EUR"][RULE]
        res=replay_one_per_day(
            feed,capital=cash,costs=costs,signal=signal,
            first_entry_index=160,previously_traded_days=days)
        cash=res["end_eur"]
        days.update(res["daily_trade_dates"])
        active=None
        for event in res["events"]:
            if event["type"]=="BUY":
                if active is not None:
                    raise AssertionError("Second BUY before previous EXIT")
                active=event
            else:
                if active is None or event["type"] not in EXIT_TYPES:
                    raise AssertionError("EXIT without matching BUY")
                if active["symbol"]!=event["symbol"]:
                    raise AssertionError("BUY/EXIT asset mismatch")
                ledger.append({
                    "day":event["day_local"],
                    "symbol":event["symbol"],
                    "exit":event["type"],
                    "net_eur":event["net_eur_before_tax"],
                    "net_pct":event["net_return_pct_on_position"],
                    "position_cost_eur":event["position_cost_eur"],
                    "holding_minutes":event["holding_minutes"],
                })
                active=None
        if active is not None:
            raise AssertionError("Unclosed position in segment")
    by_exit={}
    for exit_name in EXIT_TYPES:
        rows=[e for e in ledger if e["exit"]==exit_name]
        by_exit[exit_name]={
            "count":len(rows),
            "sum_net_eur":round(sum(x["net_eur"] for x in rows),2),
            "avg_net_pct":round(mean(x["net_pct"] for x in rows),3) if rows else None,
            "median_net_pct":round(median(x["net_pct"] for x in rows),3) if rows else None,
            "avg_net_eur":round(mean(x["net_eur"] for x in rows),2) if rows else None,
            "avg_holding_minutes":round(mean(x["holding_minutes"] for x in rows),1) if rows else None
        }
    wins=[x for x in ledger if x["net_eur"]>0]
    losses=[x for x in ledger if x["net_eur"]<0]
    total=sum(x["net_eur"] for x in ledger)
    if abs(total-(cash-5000))>.05:
        raise AssertionError("Trade PnL must reconcile with cash")
    return {
        "mode":"READ_ONLY_TRADE_LEVEL_AUDIT",
        "starting_eur":5000.,
        "ending_eur":round(cash,2),
        "net_pnl_eur":round(total,2),
        "trades":len(ledger),
        "positive_trades":len(wins),
        "negative_trades":len(losses),
        "flat_trades":len(ledger)-len(wins)-len(losses),
        "realized_win_rate_pct":round(100*len(wins)/len(ledger),2) if ledger else None,
        "average_net_eur_per_trade":round(total/len(ledger),3) if ledger else None,
        "profit_factor":round(sum(x["net_eur"] for x in wins)/-sum(x["net_eur"] for x in losses),3) if losses else None,
        "average_positive_trade_eur":round(mean(x["net_eur"] for x in wins),2) if wins else None,
        "average_negative_trade_eur":round(mean(x["net_eur"] for x in losses),2) if losses else None,
        "exit_breakdown":by_exit,
        "per_trade":ledger,
        "live_orders":0,
        "warning":"Historical 5m OHLC fill model, not actual exchange fills; costs estimated, taxes excluded."
    }
