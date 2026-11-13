"""Separate predictive value from executable portfolio profitability.

BTC-EUR and ETH-EUR hourly candlestick signal diagnostics over the same
gap-free observed 5m segments. For each completed UTC hourly signal,
hypothetical entry is NEXT 5m candle OPEN. Measure 1h,4h,12h returns at
future observed CLOSE; never cross a missing candle or segment boundary.

For every symbol/horizon use a contemporaneous matched-time control:
all other eligible UTC-hour-close events within the same symbol, year,
Finnish hour and 24h market regime. This is descriptive, NOT randomization
or causal identification. Pattern occurrences overlap, and labels/time
windows overlap. All examined history already used for strategy research.

Round-trip net forward estimates assume single open-to-close hold, normal
and doubled fees+slippage; they are NOT the real strategy (which also
exits at stop, take profit, 21:55, or gap). No auto trades or credentials.
"""
from __future__ import annotations
from collections import defaultdict
from statistics import mean, median
from .daytrade_one_per_day import PAIRS, local_time
from .hourly_candle_hypotheses import PATTERNS, signals, completed_hours
from .intraday_net_target import ExecutionCosts, net_profit_pct

HORIZONS=(1,4,12)
DOUBLE=ExecutionCosts(50,50,30,30)
NORMAL=ExecutionCosts()

def summarize(values):
    if not values:return {"n":0,"mean":None,"median":None,"positive_share_pct":None}
    return {"n":len(values),"mean":round(mean(values),4),
            "median":round(median(values),4),
            "positive_share_pct":round(100*sum(x>0 for x in values)/len(values),2)}

def observations(prepared):
    events={p:[] for p in PATTERNS}
    baseline=[]
    for feed,_ in prepared:
        for symbol in PAIRS:
            bars=feed[symbol]
            sig=signals(bars)
            hour=completed_hours(bars)
            # Match only events for which the previous 24 hours are known,
            # and the next-open entry is permissible by the frozen 9-14 rule.
            for j in range(30,len(hour)):
                row=hour[j]
                i=row["idx"]
                if i+1>=len(bars):continue
                local=local_time(bars[i+1]["timestamp_ms"])
                if not 9<=local.hour<14:continue
                trend=hour[j-24]["close"]<=row["close"]
                if not trend:continue
                entry=bars[i+1]["open"]
                horizons={}
                for h in HORIZONS:
                    # Need a complete 5m bar ending h hours after
                    # the NEXT open entry, not the signal close.
                    last=i+12*h
                    if last>=len(bars):continue
                    exitprice=bars[last]["close"]
                    horizons[h]={
                        "raw_pct":100*(exitprice/entry-1),
                        "normal_net_pct":net_profit_pct(entry,exitprice,NORMAL),
                        "double_net_pct":net_profit_pct(entry,exitprice,DOUBLE)}
                if not horizons:continue
                key=(symbol,local.year,local.hour)
                record={"key":key,"horizons":horizons}
                baseline.append(record)
                for name,stamps in sig.items():
                    if i in stamps:events[name].append(record)
    return baseline,events

def research(prepared):
    controls,by_pattern=observations(prepared)
    # Control excludes signal occurrence of the SAME pattern, in matched
    # asset/year/hour and the same 24h rising regime. No synthetic data.
    answer=[]
    for name in PATTERNS:
        marked=by_pattern[name]
        included_ids={id(x) for x in marked}
        pool=defaultdict(list)
        for b in controls:
            if id(b) not in included_ids:pool[b["key"]].append(b)
        buckets={}
        for h in HORIZONS:
            occurrences=[r for r in marked if h in r["horizons"]]
            matched=[]
            for event in occurrences:
                # Control weighting: each event's matched peers contribute
                # one equal-weight mean, reducing huge regime-size imbalance.
                peer=[x["horizons"][h] for x in pool[event["key"]]
                      if h in x["horizons"]]
                if peer:matched.append((event["horizons"][h],{
                    k:mean(p[k] for p in peer) for k in
                    ("raw_pct","normal_net_pct","double_net_pct")}))
            q={}
            for metric in ("raw_pct","normal_net_pct","double_net_pct"):
                sigvals=[x["horizons"][h][metric] for x in occurrences]
                q[metric]={"signal":summarize(sigvals),
                           "matched_baseline":summarize([x[1][metric] for x in matched]),
                           "matched_signal":summarize([x[0][metric] for x in matched]),
                           "mean_excess_pct":round(mean(x[0][metric]-x[1][metric]
                                for x in matched),4) if matched else None}
            q["n_signal_events_with_matched_controls"]=len(matched)
            buckets[str(h)+"h"]=q
        answer.append({"pattern":name,"events":len(marked),"horizons":buckets})
    return {"mode":"READ_ONLY_PREDICTIVE_VS_PROFIT_DIAGNOSTIC",
        "horizons_hours":HORIZONS,
        "eligible_baseline_events":len(controls),
        "patterns":answer,
        "normal_roundtrip_fee_slippage_bps":80,
        "doubled_roundtrip_fee_slippage_bps":160,
        "already_completed_portfolio_test":"hourly_candles",
        "approved_live":False,
        "warnings":[
            "Matched historical controls are observational, not causal.",
            "Net fixed-horizon forward calculations are NOT a strategy "
            "or pooled-account backtest: they omit stop, force-flat, actual fills.",
            "Signals and controls can have overlapping 12h horizons.",
            "Only truly complete observed 5m price runs; horizons after gaps omitted.",
            "Pattern history and the matching rules have already been explored.",
            "No out-of-sample performance guarantee, no taxes or live orders."]}
