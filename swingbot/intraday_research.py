"""5-minute BTC-EUR research prototype. No orders, no future leakage.

Single position, next-candle-open entry, 50% take-profit once +1% net after
assumed round-trip costs, rest exits at tightened entry break-even stop, or
final observed close. Signals use previous 20 COMPLETED bars only.
This is an unvalidated short-window research probe, not alpha evidence.
"""
from __future__ import annotations
import json
from statistics import mean
from typing import Callable
from .bitvavo_intraday import intraday_candles
from .intraday_net_target import (
    ExecutionCosts, minimum_target_price, buy_total_cost, sell_net_proceeds,
    net_profit_pct,
)

def replay(bars: list[dict], *, initial_eur: float = 5000.0,
           costs: ExecutionCosts = ExecutionCosts(),
           signal: Callable[[list[dict], int], bool] | None = None) -> dict:
    if len(bars)<40 or initial_eur<=0:
        raise ValueError("Need 40 bars and positive capital")
    if any(b["timestamp_ms"]-a["timestamp_ms"]!=300000
           for a,b in zip(bars,bars[1:])):
        raise ValueError("Requires contiguous 5m bars")
    cash=initial_eur
    holding=None
    pending=False
    sells=[]
    buys=0
    curve=[]
    for i,bar in enumerate(bars):
        if holding:
            h=holding
            # For original stop-vs-target ambiguity assume STOP first.
            stop=h["stop"]
            if bar["low"]<=stop:
                exit_price=min(bar["open"],stop)
                received=sell_net_proceeds(exit_price,h["qty"],costs)
                basis=h["basis"]
                cash+=received
                sells.append({"reason":"STOP","pnl_eur":round(received-basis,2)})
                holding=None
            elif not h["partial"] and bar["high"]>=h["tp"]:
                units=h["qty"]*.5
                received=sell_net_proceeds(h["tp"],units,costs)
                basis=h["basis"]*.5
                cash+=received
                sells.append({"reason":"HALF_TP","pnl_eur":round(received-basis,2)})
                h["qty"]-=units
                h["basis"]-=basis
                h["partial"]=True
                # protect remainder with a raw break-even level AFTER costs
                h["stop"]=max(h["stop"],minimum_target_price(
                    h["entry"],net_target_pct=.000001,costs=costs,tick_size=.01))
        # Only fill a prior-candle signal; no re-entry on stop/TP candle.
        elif pending:
            price=bar["open"]
            # 20% position, no all-in: avoid unbounded capital-at-risk.
            available=cash*.20
            qty=available/buy_total_cost(price,1,costs)
            if qty>0:
                paid=buy_total_cost(price,qty,costs)
                cash-=paid
                holding={"entry":price,"qty":qty,"basis":paid,
                         "tp":minimum_target_price(price,net_target_pct=1,
                                                   costs=costs,tick_size=.01),
                         "stop":price*.985,"partial":False}
                buys+=1
                # Same bar adverse excursion counts; target cannot be
                # claimed on the entry bar without tick-level ordering.
                if bar["low"]<=holding["stop"]:
                    received=sell_net_proceeds(min(bar["open"],holding["stop"]),
                                               qty,costs)
                    cash+=received
                    sells.append({"reason":"ENTRY_BAR_STOP",
                                  "pnl_eur":round(received-paid,2)})
                    holding=None
            pending=False
        mark=holding["qty"]*bar["close"] if holding else 0.
        curve.append(cash+mark)
        if i>=20 and holding is None and not pending:
            previous=bars[i-20:i]
            # Current completed candle confirmed breaking prior max; next
            # open is the earliest entry. Momentum must also be positive.
            if ((signal(bars, i) if signal is not None else
                 (bar["close"]>max(x["close"] for x in previous) and
                  bar["close"]>mean(x["close"] for x in previous)))):
                pending=True
    # Mark unsettled inventory separately from realized cash.
    last=bars[-1]["close"]
    liquidatable=cash+(sell_net_proceeds(last,holding["qty"],costs) if holding else 0.)
    realized_takeprofits=[s for s in sells if s["reason"]=="HALF_TP"]
    return {"mode":"READ_ONLY_INTRADAY_BACKTEST",
            "bars":len(bars),"start_ms":bars[0]["timestamp_ms"],
            "end_ms":bars[-1]["timestamp_ms"],
            "initial_eur":initial_eur,"cash_eur":round(cash,2),
            "estimated_liquidation_eur":round(liquidatable,2),
            "estimated_pnl_eur":round(liquidatable-initial_eur,2),
            "buys":buys,"half_take_profits":len(realized_takeprofits),
            "full_or_partial_stop_exits":len(sells)-len(realized_takeprofits),
            "open_position":bool(holding),
            "max_mark_to_market_drawdown_pct":round(max(
                (max(curve[:j+1])-v)/max(curve[:j+1])*100
                for j,v in enumerate(curve)),2),
            "warning":"Short historical sample, model fees, fills assumed. No taxes. "
                      "No performance inference and no live execution."}

def main():
    data=intraday_candles("BTC-EUR",interval="5m",limit=1000)
    print(json.dumps(replay(data),indent=2))

if __name__=="__main__":
    main()
