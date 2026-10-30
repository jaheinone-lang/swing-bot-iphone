"""150 days BTC/ETH: one trade per Finnish calendar day, shared €5000.

Three PREDECLARED strategies on identical observed Bitvavo 5-minute bars:
A: prior multiple-entries pooled strategy (reference only);
B: 1/day, full target, same quality-buy signal;
C: 1/day, full target, 3 consecutive green closes / rising impulse.

Costs are 25bps fee + 15bps slip per side, double-cost stress.
Historic sample was previously inspected; do NOT label as true independent
forward validation. Missing/gapped intervals are NEVER forward filled.
"""
from __future__ import annotations

import json
from .bitvavo_intraday_history import (
    historical_five_minute, contiguous_observed_segments)
from .btc_eth_quality_gate import quality_buy_signal
from .daytrade_one_per_day import (
    PAIRS, confirmed_upward_move, replay_one_per_day)
from .intraday_net_target import ExecutionCosts
from .shared_btc_eth_portfolio import shared_replay

DOUBLE=ExecutionCosts(50,50,30,30)
MODELS=(
    ("old_unlimited_day_entries",None),
    ("one_day_quality_entry",quality_buy_signal),
    ("one_day_confirmed_15m_rise",confirmed_upward_move),
)


def compare(days=150):
    feeds={s:historical_five_minute(s,days=days,require_complete=False)
           for s in PAIRS}
    indexes={s:{bar["timestamp_ms"]:bar for bar in feeds[s]} for s in PAIRS}
    common=sorted(set(indexes[PAIRS[0]])&set(indexes[PAIRS[1]]))
    pieces=contiguous_observed_segments(
        [indexes[PAIRS[0]][t] for t in common],min_bars=190)
    if not pieces:
        raise ValueError("No sufficient uninterrupted market history")
    results={}
    for label,signal in MODELS:
        outcomes={}
        for fee_name,cost in (("base",ExecutionCosts()),("double",DOUBLE)):
            cash=5000.
            buys=exits=tp=stops=flat=0
            traded_days=set()
            by_month={}
            for piece in pieces:
                stamps=[x["timestamp_ms"] for x in piece]
                feed={s:[indexes[s][t] for t in stamps] for s in PAIRS}
                if signal is None:
                    result=shared_replay(feed,capital=cash,costs=cost,
                                         signal=quality_buy_signal,
                                         first_entry_index=160)
                    buys+=result["buys"]
                    tp+=result["half_take_profits"]
                    stops+=result["stop_exits"]
                    cash=result["final_liquidation_estimate_eur"]
                else:
                    result=replay_one_per_day(
                        feed,capital=cash,costs=cost,signal=signal,
                        first_entry_index=160,
                        previously_traded_days=traded_days,
                        net_target_pct=1.)
                    # Persist the day registry across separate market-data
                    # segments so discontinuities cannot create second buys
                    # on the same Finnish calendar date.
                    traded_days.update(result["daily_trade_dates"])
                    buys+=result["buys"]
                    tp+=result["full_take_profits"]
                    stops+=result["stop_exits"]
                    flat+=result["session_end_exits"]
                    cash=result["end_eur"]
                key=__import__("datetime").datetime.fromtimestamp(
                    stamps[-1]/1000,__import__("datetime").timezone.utc
                ).strftime("%Y-%m")
                by_month[key]=round(cash,2)
            outcomes[fee_name]={
                "start_eur":5000.,
                "end_eur":round(cash,2),
                "pnl_eur":round(cash-5000,2),
                "pnl_pct":round((cash/5000-1)*100,2),
                "buys":buys,
                "net_target_exits":tp,
                "stop_exits":stops,
                "forced_day_flat_exits":flat,
                "distinct_fi_trade_days":len(traded_days),
                "monthly_end_balances":by_month,
            }
        results[label]=outcomes
    return {
        "mode":"READ_ONLY_BTC_ETH_ONE_TRADE_PER_FI_DAY",
        "days_requested":days,"common_observed_candles":len(common),
        "gap_segments":len(pieces),
        "evaluated_candles":sum(len(x) for x in pieces),
        "settings":{
            "instruments":PAIRS,"shared_eur_account":5000.,
            "entry_hours_fi":"09:00–19:59",
            "forced_flat_fi":"21:55",
            "one_opening_trade_per_fi_calendar_day_across_BOTH_assets":True,
            "full_position_sold_at_first_plus_1pct_net_target":True,
            "spot_only":True,"live_orders":False,"income_tax_included":False},
        "results":results,
        "warnings":[
            "Model fill at target is assumed from OHLC high; real limit fill may fail.",
            "Historic BTC/ETH candles are previously explored, not independent validation.",
            "Missing candles segment test and reset positions; forced segment "
            "last-close sale may differ from real gap pricing.",
            "1% gain applies only to successful trades before income taxes; "
            "overall daily returns may be negative.",
            "This updates neither live trading nor the prior Momentum E forward account.",
        ]
    }


if __name__=="__main__":
    print(json.dumps(compare(),ensure_ascii=False,indent=2))
