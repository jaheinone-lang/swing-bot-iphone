"""One shared EUR cash account, BTC + ETH spot 5m paper backtest.

Read-only, no exchange trade endpoints. No SOL, leverage or real account.
Decisions on fully completed bars, orders at next bar open; stops assumed
before targets when both touched. Both instruments share one cash balance.
"""
from __future__ import annotations
from .intraday_risk_regime import regime_buy_signal, max_affordable_units
from .intraday_net_target import (
    ExecutionCosts, buy_total_cost, sell_net_proceeds, minimum_target_price)
from .bitvavo_intraday_history import historical_five_minute, contiguous_observed_segments

PAIRS=("BTC-EUR","ETH-EUR")
START_EUR=5000.0
PER_TRADE_RISK_PCT=.25
TOTAL_OPEN_RISK_PCT=.5
POSITION_LIMIT_PCT=20.0

def _risk(basis, qty, stop, costs):
    return max(0.,basis-sell_net_proceeds(stop,qty,costs))

def shared_replay(feeds, *, capital=START_EUR, costs=ExecutionCosts(),
                  signal=regime_buy_signal, first_entry_index=110,
                  stop_pct=1.5, take_profit_pct=1., take_fraction=.5):
    if set(feeds)!=set(PAIRS):
        raise ValueError("Exactly BTC-EUR and ETH-EUR feeds required")
    if capital<=0: raise ValueError("Positive initial EUR required")
    if not (.5<=stop_pct<=5 and 1<=take_profit_pct<=5 and
            0<take_fraction<=1):
        raise ValueError("Invalid scenario risk / target parameters")
    lengths={len(rows) for rows in feeds.values()}
    if len(lengths)!=1 or min(lengths)<max(120,first_entry_index+2):
        raise ValueError("Same length, enough candles")
    size=lengths.pop()
    times=[[row["timestamp_ms"] for row in feeds[s]] for s in PAIRS]
    if times[0]!=times[1] or any(b-a!=300000 for a,b in zip(times[0],times[0][1:])):
        raise ValueError("Aligned contiguous 5 minute candles required")
    cash=float(capital)
    positions={}
    pending=set()
    events=[]
    equity_curve=[]
    for i in range(size):
        # Process open holdings before new positions and never reuse the
        # proceeds for a same-bar fresh signal; signals are for NEXT bar.
        for symbol in PAIRS:
            if symbol not in positions:continue
            p=positions[symbol];b=feeds[symbol][i]
            if b["low"]<=p["stop"]:
                received=sell_net_proceeds(min(b["open"],p["stop"]),p["qty"],costs)
                cash+=received
                events.append({"bar":i,"symbol":symbol,"type":"STOP",
                               "net_eur":round(received-p["basis"],2)})
                del positions[symbol]
            elif not p["partial"] and b["high"]>=p["tp"]:
                units=p["qty"]*take_fraction
                proceeds=sell_net_proceeds(p["tp"],units,costs)
                basis=p["basis"]*take_fraction
                cash+=proceeds
                p["qty"]-=units
                p["basis"]-=basis
                p["partial"]=True
                if p["qty"]<=1e-12:
                    del positions[symbol]
                    continue
                p["stop"]=max(p["stop"],minimum_target_price(
                    p["entry"],net_target_pct=.000001,costs=costs))
                events.append({"bar":i,"symbol":symbol,"type":"HALF_TP",
                               "net_eur":round(proceeds-basis,2)})
        if pending and i>=first_entry_index:
            # Deterministic priority: stronger 20 bar relative momentum;
            # this ranks existing already-completed signals only.
            ranked=sorted(pending,key=lambda s:(
                -(feeds[s][i-1]["close"]/feeds[s][i-21]["close"]-1),s))
            for symbol in ranked:
                if symbol in positions:continue
                price=feeds[symbol][i]["open"]
                mark=sum(p["qty"]*feeds[s][i]["open"]
                         for s,p in positions.items())
                equity=cash+mark
                open_risk=sum(_risk(p["basis"],p["qty"],p["stop"],costs)
                              for p in positions.values())
                available_risk=max(0.,equity*TOTAL_OPEN_RISK_PCT/100-open_risk)
                if available_risk<=0 or cash<=0:continue
                risk_pct=min(PER_TRADE_RISK_PCT,100*available_risk/equity)
                qty=max_affordable_units(
                    cash,equity,price,risk_budget_pct=risk_pct,
                    max_position_pct=POSITION_LIMIT_PCT,
                    stop_raw_price=price*(1-stop_pct/100),costs=costs)
                if qty<=0:continue
                basis=buy_total_cost(price,qty,costs)
                cash-=basis
                positions[symbol]={"entry":price,"qty":qty,
                    "basis":basis,"stop":price*(1-stop_pct/100),"partial":False,
                    "tp":minimum_target_price(price,net_target_pct=take_profit_pct,costs=costs)}
                events.append({"bar":i,"symbol":symbol,"type":"BUY",
                               "basis_eur":round(basis,2)})
                # Protect entry-bar drawdown, never claim an entry-bar TP.
                if feeds[symbol][i]["low"]<=price*(1-stop_pct/100):
                    proceeds=sell_net_proceeds(min(price,price*(1-stop_pct/100)),qty,costs)
                    cash+=proceeds
                    events.append({"bar":i,"symbol":symbol,"type":"ENTRY_STOP",
                                   "net_eur":round(proceeds-basis,2)})
                    del positions[symbol]
        pending=set()
        if i>=first_entry_index:
            for symbol in PAIRS:
                if symbol not in positions and signal(feeds[symbol],i):
                    pending.add(symbol)
        value=cash+sum(p["qty"]*feeds[s][i]["close"]
                       for s,p in positions.items())
        equity_curve.append(value)
    last_equity=cash+sum(sell_net_proceeds(
        feeds[s][-1]["close"],p["qty"],costs) for s,p in positions.items())
    peak=capital; dd=0.
    for eq in equity_curve:
        peak=max(peak,eq);dd=max(dd,(peak-eq)/peak*100)
    return {"mode":"READ_ONLY_SHARED_BTC_ETH_SPOT",
            "initial_eur":capital,"final_liquidation_estimate_eur":round(last_equity,2),
            "profit_eur_before_tax":round(last_equity-capital,2),
            "max_marked_drawdown_pct":round(dd,2),
            "buys":sum(e["type"]=="BUY" for e in events),
            "half_take_profits":sum(e["type"]=="HALF_TP" for e in events),
            "stop_exits":sum(e["type"] in ("STOP","ENTRY_STOP") for e in events),
            "open_positions":list(positions),
            "events":events,
            "joint_eur_cash":round(cash,2),
            "live_orders":False,"tax_included":False}

def main():
    feeds={s:historical_five_minute(s,days=7,require_complete=False) for s in PAIRS}
    sets=[set(x["timestamp_ms"] for x in feeds[s]) for s in PAIRS]
    common=sorted(sets[0]&sets[1])
    aligned={s:[x for x in feeds[s] if x["timestamp_ms"] in set(common)]
             for s in PAIRS}
    segments=contiguous_observed_segments(aligned[PAIRS[0]],min_bars=400)
    if not segments:raise ValueError("Not enough common uninterrupted candles")
    best=max(segments,key=len)
    stamp={x["timestamp_ms"] for x in best}
    valid={s:[x for x in aligned[s] if x["timestamp_ms"] in stamp] for s in PAIRS}
    import json
    result=shared_replay(valid)
    print(json.dumps({"bars":len(best),"shared_portfolio":result},indent=2))
if __name__=="__main__":
    main()
