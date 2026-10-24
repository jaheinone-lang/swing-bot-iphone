"""Audit BTC/ETH five-year actual historical entry outcomes and early moves.

NO CHANGE TO STRATEGY. Match the existing read-only replay BUY/EXIT stream.
Future candles are used ONLY for retrospective diagnostics. Snapshot 15,30,
60,120-minute movements if the position was still held at that instant;
otherwise mark censored, never quietly use post-exit prices. MFE/MAE
through actual holding period from 5m OHLC are descriptive, not causal.
Pre-entry 15min return, 4h momentum, relative volume are strictly frozen
at the signal candle i-1, before trade's next-bar open.
"""
from __future__ import annotations
from statistics import mean,median
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts

HORIZONS=(15,30,60,120)
EXITS={"FULL_TP","STOP","ENTRY_BAR_STOP","DAY_FLAT",
       "END_OF_OBSERVED_SEGMENT","EARLY_EXIT"}


def features_before_entry(bars, i):
    j=i-1
    if j<160:raise ValueError("Not enough signal history")
    close=bars[j]["close"]
    vavg=mean(x["volume"] for x in bars[j-20:j])
    recent=mean(x["close"] for x in bars[j-47:j+1])
    older=mean(x["close"] for x in bars[j-143:j-95])
    return {
        "pre_entry_15m_change_pct":round(100*(close/bars[j-3]["close"]-1),3),
        "trend_recent_vs_older_pct":round(100*(recent/older-1),3),
        "relative_volume_20":round(bars[j]["volume"]/vavg,3) if vavg>0 else None,
    }


def describe(rows,field):
    values=[r[field] for r in rows if r.get(field) is not None]
    return {
        "n":len(values),
        "avg":round(mean(values),3) if values else None,
        "median":round(median(values),3) if values else None
    }


def diagnose(prepared, *, costs=ExecutionCosts()):
    cash=5000.
    dates=set()
    entries=[]
    for feed,caches in prepared:
        if len(feed[PAIRS[0]])<162:continue
        signal=lambda bars,i: i in caches[
            "BTC-EUR" if bars is feed["BTC-EUR"] else "ETH-EUR"]["morning_strict"]
        result=replay_one_per_day(
            feed,capital=cash,costs=costs,signal=signal,
            first_entry_index=160,previously_traded_days=dates)
        cash=result["end_eur"]
        dates.update(result["daily_trade_dates"])
        pending=None
        for event in result["events"]:
            if event["type"]=="BUY":
                if pending is not None:raise AssertionError("Overlapping positions")
                pending=event
                continue
            if event["type"] not in EXITS or pending is None:
                raise AssertionError("Unpaired BUY/EXIT")
            if pending["symbol"]!=event["symbol"]:
                raise AssertionError("Mismatched symbol")
            asset=event["symbol"]
            bars=feed[asset]
            start=pending["bar"]
            end=event["bar"]
            entry=pending["raw_entry"]
            item={"day":event["day_local"],"symbol":asset,
                  "exit":event["type"],
                  "duration_minutes":event["holding_minutes"],
                  "net_eur":event["net_eur_before_tax"],
                  "net_pct":event["net_return_pct_on_position"],
                  **features_before_entry(bars,start)}
            # Only bar close at exact horizon if trade has survived
            # through the end of that horizon candle.
            for minutes in HORIZONS:
                offset=minutes//5
                j=start+offset-1
                field=f"held_{minutes}m_change_pct"
                item[field]=round(100*(bars[j]["close"]/entry-1),3) \
                    if j<end and j<len(bars) else None
            # Realized trade's observed price path; on the exit candle
            # unknown ordering prohibits inferring attainable favorable MFE.
            # Exclude the exit candle; entry bar can contain post-fill extrema
            # but is also unknown if immediate stop/TP closed in same bar.
            earlier=bars[start:end]
            if earlier:
                item["observed_preexit_mfe_pct"]=round(
                    100*(max(x["high"] for x in earlier)/entry-1),3)
                item["observed_preexit_mae_pct"]=round(
                    100*(min(x["low"] for x in earlier)/entry-1),3)
            else:
                item["observed_preexit_mfe_pct"]=None
                item["observed_preexit_mae_pct"]=None
            entries.append(item)
            pending=None
        if pending is not None:raise AssertionError("Unclosed trade")
    tp=[x for x in entries if x["exit"]=="FULL_TP"]
    stopped=[x for x in entries if x["exit"] in ("STOP","ENTRY_BAR_STOP")]
    other=[x for x in entries if x not in tp and x not in stopped]
    def group_stats(rows):
        keys=[
            "pre_entry_15m_change_pct","trend_recent_vs_older_pct",
            "relative_volume_20",
            "observed_preexit_mfe_pct","observed_preexit_mae_pct"
        ]+[f"held_{x}m_change_pct" for x in HORIZONS]
        return {"count":len(rows),"metrics":{k:describe(rows,k) for k in keys}}
    return {"mode":"READ_ONLY_FIVE_YEAR_ENTRY_PATH_DIAGNOSTICS",
            "total_trades":len(entries),
            "winning_target_count":len(tp),
            "stop_count":len(stopped),
            "other_exit_count":len(other),
            "full_tp":group_stats(tp),
            "stop_loss":group_stats(stopped),
            "other_exits":group_stats(other),
            "records":entries,
            "reconciled_final_eur":round(cash,2),
            "live_trades":0,
            "warning":"RETROSPECTIVE descriptors, not executable signal. "
                "Snapshot missing if exited sooner (survivorship censoring). "
                "5m high/low path and limit fills unknown. Prior price "
                "history studied, features NOT independent test and never "
                "interpreted as predictive proof. Taxes excluded."}
