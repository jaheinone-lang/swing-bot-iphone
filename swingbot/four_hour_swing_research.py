"""Research-only 4h trend-following BTC/ETH spot swing replay (5y 5m OHLC).

Not a live bot. Entries from COMPLETED UTC 4h bars only, at NEXT 5m
open; exits from 5m stop or fixed holding horizon (24h/72h).
No leverage, one shared EUR 5000 cash account, max one open position,
at most one opening per Finland-local calendar day, max 20% position
and estimated 0.25% nominal account-at-stop risk. Each market-data gap
forces observed-last-close liquidation. The regime split is implemented
without executing before start of test era. No forward candles for entry.

This is exploratory IN-SAMPLE research, not profit validation.
"""
from __future__ import annotations

from datetime import datetime,timezone
from .daytrade_one_per_day import PAIRS,local_time
from .intraday_net_target import ExecutionCosts,buy_total_cost,sell_net_proceeds
from .intraday_risk_regime import max_affordable_units

STEP=300000
FOUR_HOURS=48
WARMUP=48*34
SPLIT_MS=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
FEES=ExecutionCosts()
STRESS=ExecutionCosts(50,50,30,30)
RULES=(
    ("4h_breakout_24h","breakout",24),
    ("4h_breakout_72h","breakout",72),
    ("4h_reclaim_24h","reclaim",24),
    ("4h_reclaim_72h","reclaim",72),
)

def four_hour_signals(bars,style):
    if style not in ("breakout","reclaim"):
        raise ValueError("Unknown 4h strategy")
    result=set()
    # Signal candle i is last 5m bar of a COMPLETE UTC 4h block.
    ix=[]
    for i in range(FOUR_HOURS-1,len(bars)-1):
        if (bars[i]["timestamp_ms"]+STEP)%(4*3600000)==0:
            if bars[i-FOUR_HOURS+1]["timestamp_ms"]%(4*3600000)!=0:
                continue
            ix.append(i)
    for j in range(33,len(ix)):
        i=ix[j]
        def hbar(end):
            rows=bars[end-47:end+1]
            return (rows[0]["open"],max(x["high"] for x in rows),
                    min(x["low"] for x in rows),rows[-1]["close"])
        # Previous 30 finished 4h bars and this completed bar.
        frames=[hbar(ix[k]) for k in range(j-30,j+1)]
        closes=[x[3] for x in frames]
        ma12=sum(closes[-12:])/12
        ma30=sum(closes[-30:])/30
        c=closes[-1]
        if not(c>ma30 and ma12>ma30):
            continue
        if style=="breakout":
            # New 48h high with body strength, not massive overextension.
            previous_hi=max(x[1] for x in frames[-13:-1])
            if (c>previous_hi and c>frames[-1][0] and
                0.001<=(c/frames[-1][0]-1)<=0.025):
                result.add(i)
        else:
            # Trend recovery from temporary prior 4h close under 12-bar SMA.
            previous_mean=sum(closes[-13:-1])/12
            if (closes[-2]<previous_mean and c>ma12 and
                c>frames[-1][0] and
                (c/closes[-2]-1)<=0.025):
                result.add(i)
    return result

def era_segments(prepared):
    output={"early":[],"later":[]}
    for feed,_ in prepared:
        ts=[x["timestamp_ms"] for x in feed[PAIRS[0]]]
        idx=next((i for i,t in enumerate(ts) if t>=SPLIT_MS),len(ts))
        if idx>=WARMUP+2:
            output["early"].append(({s:feed[s][:idx] for s in PAIRS},0))
        if len(ts)-idx>=3:
            begin=max(0,idx-WARMUP-FOUR_HOURS)
            sub={s:feed[s][begin:] for s in PAIRS}
            output["later"].append((sub,SPLIT_MS))
    return output

def replay(segments,rule,fees=FEES):
    _,style,hours=rule
    cash=5000.
    trade_days=set()
    records=[]
    for feed,min_entry_ts in segments:
        a=feed[PAIRS[0]]
        if len(a)<WARMUP+2:continue
        available={s:four_hour_signals(feed[s],style) for s in PAIRS}
        position=None
        for i,bar in enumerate(a):
            ts=bar["timestamp_ms"]
            if position:
                symbol=position["symbol"]
                current=feed[symbol][i]
                elapsed=(ts-position["entry_ms"])/3600000
                reason=None
                if current["open"]<=position["stop"]:
                    sell=current["open"];reason="STOP_GAP_OR_OPEN"
                elif current["low"]<=position["stop"]:
                    sell=position["stop"];reason="STOP"
                elif elapsed>=hours:
                    sell=current["open"];reason="TIME_EXIT"
                if reason:
                    proceeds=sell_net_proceeds(sell,position["qty"],fees)
                    cash+=proceeds
                    records.append({"symbol":symbol,"entry_ms":position["entry_ms"],
                        "exit_ms":ts,"reason":reason,
                        "net_eur":round(proceeds-position["basis"],4),
                        "position_cost":round(position["basis"],4)})
                    position=None
            if position or i< WARMUP+1 or ts<min_entry_ts:continue
            day=local_time(ts).date().isoformat()
            if day in trade_days:continue
            possible=[]
            for symbol in PAIRS:
                if i-1 in available[symbol] and feed[symbol][i]["open"]>0:
                    possible.append(symbol)
            if not possible:continue
            # Choose symbol by PRIOR completed 4h close return, no future.
            symbol=max(possible,key=lambda s:(
                feed[s][i-1]["close"]/feed[s][i-49]["close"],s))
            entry=feed[symbol][i]["open"]
            stop=entry*.98
            qty=max_affordable_units(cash,cash,entry,
                risk_budget_pct=.25,max_position_pct=20.,
                stop_raw_price=stop,costs=fees)
            if qty<=0:continue
            basis=buy_total_cost(entry,qty,fees)
            if basis>cash+1e-6:raise AssertionError("No negative cash")
            cash-=basis
            position={"entry_ms":ts,"stop":stop,"qty":qty,
                "symbol":symbol,"basis":basis}
            trade_days.add(day)
            # The entry 5m candle high/low is unknown inside that bar;
            # stop-first is conservative, no exit until next bar.
        if position is not None:
            close=feed[position["symbol"]][-1]["close"]
            proceeds=sell_net_proceeds(close,position["qty"],fees)
            cash+=proceeds
            records.append({"symbol":position["symbol"],
                "entry_ms":position["entry_ms"],
                "exit_ms":a[-1]["timestamp_ms"],
                "reason":"GAP_OR_STUDY_END",
                "net_eur":round(proceeds-position["basis"],4),
                "position_cost":round(position["basis"],4)})
    return {
        "trades":len(records),"stops":sum(r["reason"].startswith("STOP") for r in records),
        "time_exits":sum(r["reason"]=="TIME_EXIT" for r in records),
        "gap_end_exits":sum(r["reason"]=="GAP_OR_STUDY_END" for r in records),
        "wins":sum(r["net_eur"]>0 for r in records),
        "end_eur":round(cash,2),"pnl_eur":round(cash-5000,2),
        "max_one_concurrent_position":True,
        "taxes_included":False,
    }

def study(prepared):
    eras=era_segments(prepared)
    rows=[]
    for rule in RULES:
        a=replay(eras["early"],rule)
        b=replay(eras["later"],rule)
        stress_a=replay(eras["early"],rule,STRESS)
        stress_b=replay(eras["later"],rule,STRESS)
        rows.append({"name":rule[0],
             "early":a,"later":b,"early_double":stress_a,"later_double":stress_b,
             "historically_positive_both_eras_all_costs":
                all(x["pnl_eur"]>0 and x["trades"]>=15
                    for x in (a,b,stress_a,stress_b))})
    return {
        "mode":"FOUR_HOUR_MULTI_DAY_SPOT_SWING_EXPLORATION",
        "periods":"2021-2023 and 2024-2026 each starts at 5000 EUR",
        "rows":rows,
        "historical_candidates":[x["name"] for x in rows
            if x["historically_positive_both_eras_all_costs"]],
        "live_approved":False,
        "caveats":[
            "Both periods have been used in prior research: NO independent OOS.",
            "24h/72h time exits allow overnight gaps; stop fill may be worse.",
            "Five minute candle ordering and exchange fills unverified.",
            "Only long spot risk-managed positions, no leverage.",
            "Gap sections force liquidation; long 4h warmup discards many bars.",
            "Costs estimated, double-cost stress included, tax excluded.",
        ],
    }
