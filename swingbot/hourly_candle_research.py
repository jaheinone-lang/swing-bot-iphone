"""Read-only 5-year BTC ETH completed-hour candlestick portfolio study.

Spot only, EUR 5000 pooled account and one buy per Finnish day, 09-14.
Use exactly the existing entry/stop/TP/close and fee/slippage models.
Train=before 2024, later=from 2024, already explored (not holdout).
"""
from __future__ import annotations
from .hourly_candle_hypotheses import PATTERNS,signals
from .positive_rules_5year import split_feeds
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts

STRESS=ExecutionCosts(50,50,30,30)

def run_segmented(windows,pattern,costs=ExecutionCosts()):
    if pattern not in PATTERNS: raise ValueError("Unknown candle hypothesis")
    funds=5000.;dates=set();buys=tp=stops=0
    for feed,_ in windows:
        cache={s:signals(feed[s])[pattern] for s in PAIRS}
        def decide(rows,i):
            asset="BTC-EUR" if rows is feed["BTC-EUR"] else "ETH-EUR"
            return i in cache[asset]
        trial=replay_one_per_day(feed,capital=funds,costs=costs,
            signal=decide,first_entry_index=160,
            previously_traded_days=dates)
        funds=trial["end_eur"]
        dates.update(trial["daily_trade_dates"])
        buys+=trial["buys"];tp+=trial["full_take_profits"]
        stops+=trial["stop_exits"]
    return {"trades":buys,"take_profits":tp,"stops":stops,
            "ending_eur":round(funds,2),"pnl_eur":round(funds-5000,2)}

def study(prepared):
    periods=split_feeds(prepared)
    rows=[]
    for name in PATTERNS:
        a=run_segmented(periods["train"],name)
        b=run_segmented(periods["later"],name)
        c=run_segmented(periods["train"],name,STRESS)
        d=run_segmented(periods["later"],name,STRESS)
        rows.append({"pattern":name,"early":a,"later":b,
                    "early_double":c,"later_double":d,
                    "positive_both_eras_both_costs":
                      all(x["pnl_eur"]>0 and x["trades"]>=15 for x in (a,b,c,d))})
    return {"mode":"READ_ONLY_HOURLY_CANDLE_5_YEAR_TEST",
           "rules":rows,
           "qualified_patterns":[r["pattern"] for r in rows
                                 if r["positive_both_eras_both_costs"]],
           "no_live_trading":True,
           "limitations":"Prior market history and rule choices are exploratory; "
             "not independent validation. Only 5m-derived complete hourly "
             "candles, conservative 5m exits with unverified fill assumptions; "
             "estimated spread/slippage/fees and no tax. No guarantee of profit."}
