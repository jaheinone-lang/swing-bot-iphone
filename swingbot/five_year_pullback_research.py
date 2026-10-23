"""Five-year BTC/ETH historical retracement-entry vs chase-entry comparisons.

Predefined prior-data-only hypotheses:
- morning_strict: old confirmed-breakout / volume chase control.
- breakout_pullback_reclaim: 3-12 completed bars after a recent
  breakout, retest near 20SMA, bullish 5m reclaim.
- trend_pullback_reclaim: 20>50>100 SMA rising trend, retracement
  followed by a bullish reclaim.

Each rule uses one pooled €5000 cash spot account; max 1 Finnish-day
entry, 100% +1% net after-cost take-profit, stop or 21:55 hard-flat.
Risk sizing and fee assumptions are unchanged. No online optimization
or future-candle data. Results are retrospective and NOT independent
prospective validation. Report 2021-2023 and 2024-2026 separately.
"""
from __future__ import annotations
from .daytrade_one_per_day import PAIRS,replay_one_per_day
from .intraday_net_target import ExecutionCosts
from .pullback_reclaim_5year import ALL_POLICIES, causal_pullback_signals

DOUBLE_COSTS=ExecutionCosts(50,50,30,30)
YEAR_BUCKETS=("2021","2022","2023","2024","2025","2026")


def inject_reclaim_signals(prepared):
    """Add 2 new causal policy caches on observed gap-free segments."""
    for feed,caches in prepared:
        for symbol in PAIRS:
            signals=causal_pullback_signals(feed[symbol])
            if not caches[symbol].keys().isdisjoint(signals.keys()):
                raise ValueError("Duplicate policy key in signal cache")
            caches[symbol].update(signals)
    return prepared


def evaluate(prepared, policy, *, costs=ExecutionCosts()):
    if policy not in ALL_POLICIES:
        raise ValueError("Unknown entry candidate")
    funds=5000.
    days=set()
    yearly={year:{"buys":0,"take_profits":0,"stops":0,
                  "end_of_day":0,"gap_exits":0,"net_profit_eur":0.}
            for year in YEAR_BUCKETS}
    counts={"buys":0,"full_tp":0,"stops":0,"end_of_day":0,"gap_exits":0}
    for feed,caches in prepared:
        if len(feed[PAIRS[0]])<162:
            continue
        signal=lambda bars,i: i in caches[
            "BTC-EUR" if bars is feed["BTC-EUR"] else "ETH-EUR"][policy]
        trial=replay_one_per_day(
            feed,capital=funds,costs=costs,signal=signal,
            first_entry_index=160,previously_traded_days=days)
        funds=trial["end_eur"]
        days.update(trial["daily_trade_dates"])
        counts["buys"]+=trial["buys"]
        counts["full_tp"]+=trial["full_take_profits"]
        counts["stops"]+=trial["stop_exits"]
        counts["end_of_day"]+=trial["session_end_exits"]
        counts["gap_exits"]+=trial["end_segment_forced_exits"]
        for event in trial["events"]:
            yr=event["day_local"][:4]
            if yr not in yearly:raise ValueError("Unexpected data period")
            if event["type"]=="BUY":
                yearly[yr]["buys"]+=1
            else:
                yearly[yr]["net_profit_eur"]+=event["net_eur_before_tax"]
                if event["type"]=="FULL_TP":
                    yearly[yr]["take_profits"]+=1
                elif event["type"] in ("STOP","ENTRY_BAR_STOP"):
                    yearly[yr]["stops"]+=1
                elif event["type"]=="DAY_FLAT":
                    yearly[yr]["end_of_day"]+=1
                elif event["type"]=="END_OF_OBSERVED_SEGMENT":
                    yearly[yr]["gap_exits"]+=1
    for item in yearly.values():
        item["net_profit_eur"]=round(item["net_profit_eur"],2)
    old=sum(yearly[y]["net_profit_eur"] for y in ("2021","2022","2023"))
    later=sum(yearly[y]["net_profit_eur"] for y in ("2024","2025","2026"))
    return {
        "starting_eur":5000.,
        "final_eur":round(funds,2),
        "profit_eur":round(funds-5000,2),
        "return_pct":round((funds/5000-1)*100,3),
        "events":counts,
        "by_year":yearly,
        "2021_to_2023_realized_pnl":round(old,2),
        "2024_to_2026_realized_pnl":round(later,2),
        "no_real_orders":True,
    }


def study(prepared):
    inject_reclaim_signals(prepared)
    scenarios={
        rule:{
            "normal_costs":evaluate(prepared,rule),
            "double_costs":evaluate(
                prepared,rule,costs=DOUBLE_COSTS)
        } for rule in ALL_POLICIES}
    return {
        "mode":"READ_ONLY_5Y_PULLBACK_ENTRY_COMPARISON",
        "predefined_rules":ALL_POLICIES,
        "prices":"Bitvavo 5m BTC-EUR ETH-EUR original fixed historical candles",
        "results":scenarios,
        "auto_selected":None,
        "live_enabled":False,
        "warning":"Historic strategies were informed by previously explored "
                  "2024-2026 data, so even this older/later view is NOT "
                  "independent holdout validation. Gaps force last observed "
                  "close liquidation, fill price is modeled on OHLC high, "
                  "trading costs assumed, personal taxes excluded."
    }
