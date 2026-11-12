"""Read-only long-horizon BTC/ETH EUR DAILY candle research, spot only.

Uses actual Bitvavo 1d OHLCV, NOT resampled gap-heavy 5min sections.
Only completed daily signals: buy at NEXT day's OPEN. Stop first on
same-day low, gaps at worse open; pre-declared 20d/55d breakouts and
20d trend-reclaim. One shared EUR 5000 cash account per calendar era,
max 20% position, nominal <=0.25% risk per trade, no leverage.
Separate 2021-2023 vs 2024-2026, with >=200 day indicator warmup.
Study is retrospective and NOT a guarantee of future returns.
"""
from __future__ import annotations
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import urlencode
import json

from .market_data import MarketDataError, _request_text
from .intraday_net_target import ExecutionCosts,buy_total_cost,sell_net_proceeds
from .intraday_risk_regime import max_affordable_units

DAY=86400000
START=datetime(2021,10,23,tzinfo=timezone.utc)
END=datetime(2026,10,23,tzinfo=timezone.utc)
SPLIT=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
PAIRS=("BTC-EUR","ETH-EUR")
FEE=ExecutionCosts()
STRESS=ExecutionCosts(50,50,30,30)
RULES=("breakout20","breakout55","trend_reclaim")
WARMUP=205

def history(fetch=_request_text):
    start=int(START.timestamp()*1000);end=int(END.timestamp()*1000)
    merged={}
    stats={}
    for symbol in PAIRS:
        values=[]
        for lo in range(start,end,1000*DAY):
            hi=min(end,lo+1000*DAY)
            url="https://api.bitvavo.com/v2/"+symbol+"/candles?"+urlencode({
                "interval":"1d","start":lo,"end":hi,"limit":1000})
            payload=json.loads(fetch(url))
            if not isinstance(payload,list):raise MarketDataError("Not a candle array")
            for row in payload:
                if not isinstance(row,(list,tuple)) or len(row)<6:
                    raise MarketDataError("Malformed daily market candle")
                t=int(row[0]);op,h,l,c,v=map(float,row[1:6])
                if not(lo<=t<hi and t%DAY==0 and
                       all(isfinite(z) for z in (op,h,l,c,v)) and
                       0<l<=min(op,c)<=max(op,c)<=h and v>=0):
                    raise MarketDataError("Invalid candle price / timestamp")
                values.append({"timestamp_ms":t,"open":op,"high":h,
                               "low":l,"close":c,"volume":v})
        values.sort(key=lambda x:x["timestamp_ms"])
        if len({x["timestamp_ms"] for x in values})!=len(values):
            raise MarketDataError("Duplicate daily UTC market candle")
        merged[symbol]=values
        stats[symbol]={"days":len(values),"first":values[0]["timestamp_ms"],
                       "last":values[-1]["timestamp_ms"]}
    common=set(x["timestamp_ms"] for x in merged[PAIRS[0]])
    common&=set(x["timestamp_ms"] for x in merged[PAIRS[1]])
    stamps=sorted(common)
    lookups={s:{x["timestamp_ms"]:x for x in merged[s]} for s in PAIRS}
    sections=[];run=[]
    for t in stamps:
        if run and t-run[-1]!=DAY:
            if len(run)>WARMUP+1:
                sections.append({s:[lookups[s][u] for u in run] for s in PAIRS})
            run=[]
        run.append(t)
    if len(run)>WARMUP+1:
        sections.append({s:[lookups[s][u] for u in run] for s in PAIRS})
    return sections,{"per_pair":stats,"both_common_days":len(stamps),
                     "consecutive_sections_ge_207d":len(sections),
                     "no_fill_of_missing_days":True,"provider":"Bitvavo public EUR 1d"}

def split_eras(sections):
    eras={"early":[],"later":[]}
    for feed in sections:
        arr=feed[PAIRS[0]]
        ix=next((i for i,b in enumerate(arr) if b["timestamp_ms"]>=SPLIT),len(arr))
        if ix>WARMUP+1:
            eras["early"].append(({s:feed[s][:ix] for s in PAIRS},0))
        if len(arr)-ix>=2:
            begin=max(0,ix-WARMUP-5)
            eras["later"].append(({s:feed[s][begin:] for s in PAIRS},SPLIT))
    return eras

def _avg(bars,i,n):
    return sum(x["close"] for x in bars[i-n+1:i+1])/n

def signal(bars,completed_i,rule):
    i=completed_i
    if i<200:return False
    c=bars[i]["close"]
    sma20=_avg(bars,i,20);sma50=_avg(bars,i,50)
    sma100=_avg(bars,i,100);sma200=_avg(bars,i,200)
    if rule in ("breakout20","breakout55"):
        n=20 if rule=="breakout20" else 55
        previous_high=max(b["high"] for b in bars[i-n:i])
        return (c>previous_high and sma50>sma100 and c>sma50
                and .01<c/bars[i-30]["close"]-1<.35)
    if rule=="trend_reclaim":
        p20=_avg(bars,i-1,20)
        return (sma50>sma100 and sma100>sma200 and
                bars[i-1]["close"]<=p20 and c>sma20
                and c>bars[i]["open"] and
                c/bars[i-30]["close"]>1.015)
    raise ValueError("Unknown daily swing rule")

def replay(eras,rule,costs=FEE):
    if rule not in RULES:raise ValueError("Unknown policy")
    cash=5000.
    events=[]
    cooldown_until=0
    for feed,min_ts in eras:
        length=len(feed[PAIRS[0]])
        if length<=WARMUP+1:continue
        position=None
        for i in range(WARMUP,length):
            t=feed[PAIRS[0]][i]["timestamp_ms"]
            if position:
                asset=position["asset"];bar=feed[asset][i]
                endreason=None;price=None
                old=feed[asset]
                if (i>0 and old[i-1]["close"]<_avg(old,i-1,20)):
                    endreason="TREND_EXIT";price=bar["open"]
                elif bar["open"]<=position["stop"]:
                    endreason="STOP_GAP";price=bar["open"]
                elif bar["low"]<=position["stop"]:
                    endreason="STOP";price=position["stop"]
                elif t-position["entry_ms"]>=60*DAY:
                    endreason="TIME_LIMIT";price=bar["open"]
                if endreason:
                    receipt=sell_net_proceeds(price,position["qty"],costs)
                    cash+=receipt
                    events.append({"asset":asset,"reason":endreason,
                        "exit_year":datetime.fromtimestamp(t/1000,timezone.utc).year,
                        "net_eur":round(receipt-position["basis"],4)})
                    position=None
                    cooldown_until=t+3*DAY
            if position or t<min_ts or t<cooldown_until:continue
            possibilities=[s for s in PAIRS if signal(feed[s],i-1,rule)]
            if not possibilities:continue
            asset=max(possibilities,key=lambda s:
                feed[s][i-1]["close"]/feed[s][i-31]["close"])
            price=feed[asset][i]["open"];stop=price*.96
            qty=max_affordable_units(cash,cash,price,
                risk_budget_pct=.25,max_position_pct=20.,
                stop_raw_price=stop,costs=costs)
            if qty<=0:continue
            basis=buy_total_cost(price,qty,costs)
            if basis>cash+1e-6:raise AssertionError("Overdraft")
            cash-=basis
            position={"asset":asset,"qty":qty,"basis":basis,
                      "stop":stop,"entry_ms":t}
            # Stop-first on entry bar; a 1d OHLC cannot recover intra-day
            # order of high/low, so this favors conservative loss estimation.
            if feed[asset][i]["low"]<=stop:
                receipt=sell_net_proceeds(stop,qty,costs)
                cash+=receipt
                events.append({"asset":asset,"reason":"ENTRY_STOP",
                    "exit_year":datetime.fromtimestamp(t/1000,timezone.utc).year,
                    "net_eur":round(receipt-basis,4)})
                cooldown_until=t+3*DAY;position=None
        if position:
            asset=position["asset"]
            receipt=sell_net_proceeds(feed[asset][-1]["close"],position["qty"],costs)
            cash+=receipt
            events.append({"asset":asset,"reason":"END_OF_SEGMENT",
                "exit_year":datetime.fromtimestamp(
                    feed[asset][-1]["timestamp_ms"]/1000,timezone.utc).year,
                "net_eur":round(receipt-position["basis"],4)})
    annual={str(y):{"trades":sum(e["exit_year"]==y for e in events),
        "pnl_eur":round(sum(e["net_eur"] for e in events if e["exit_year"]==y),2)}
        for y in range(2021,2027)}
    return {"trades":len(events),"wins":sum(e["net_eur"]>0 for e in events),
        "realized_by_exit_year":annual,
        "stops":sum("STOP" in e["reason"] for e in events),
        "pnl_eur":round(cash-5000,2),"end_eur":round(cash,2),
        "final_fully_liquidated":True}

def buy_hold_20pct(eras,costs=FEE):
    # Benchmark 10% of starting capital into BTC and 10% into ETH
    # bought at first research-eligible daily open and liquidated at
    # last observed close; do NOT extrapolate through missing days.
    # Only valid for one continuous segment per era.
    if len(eras)!=1:return {"available":False,"reason":"noncontiguous_daily_sections"}
    feed,min_ts=eras[0]
    bars=feed[PAIRS[0]]
    start=next((i for i in range(WARMUP,len(bars))
                if bars[i]["timestamp_ms"]>=min_ts),None)
    if start is None:return {"available":False,"reason":"insufficient_history"}
    net=4000.
    for symbol in PAIRS:
        p=feed[symbol][start]["open"]
        qty=500/buy_total_cost(p,1,costs)
        net+=sell_net_proceeds(feed[symbol][-1]["close"],qty,costs)
    return {"available":True,"pnl_eur":round(net-5000,2),
            "end_eur":round(net,2),
            "note":"20% total BTC ETH exposure, 80% cash, no stop"}

def study(sections,metadata):
    eras=split_eras(sections)
    rows=[]
    for rule in RULES:
        a=replay(eras["early"],rule);b=replay(eras["later"],rule)
        c=replay(eras["early"],rule,STRESS)
        d=replay(eras["later"],rule,STRESS)
        rows.append({"rule":rule,"early":a,"later":b,
            "early_double":c,"later_double":d,
            "positive_eras_and_costs":all(v["pnl_eur"]>0 for v in (a,b,c,d))})
    return {
        "mode":"REAL_1D_BTC_ETH_LONG_HORIZON_READ_ONLY",
        "history":metadata,
        "cash_eur_5000_benchmark":0,
        "btc_eth_20pct_buy_hold":{
            "early":buy_hold_20pct(eras["early"]),
            "later":buy_hold_20pct(eras["later"])},
        "strategies":rows,
        "historical_positive_candidates":[r["rule"] for r in rows
            if r["positive_eras_and_costs"]],
        "live_approved":False,
        "limitations":[
            "Historical periods already studied; NOT independent validation.",
            "Actual market fills/spreads differ from OHLC estimates.",
            "Daily gaps excluded and open positions force-exited on segment end.",
            "No income tax, no leverage, only one concurrent position.",
            "Nominal stop risk can be exceeded by overnight price gaps."]}

if __name__=="__main__":
    print(json.dumps(study(*history()),ensure_ascii=False))
