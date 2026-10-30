"""Five-year BTC/ETH profit-order execution sensitivity (research only).

Hold original frozen 'morning_strict' entries and 5000 EUR pooled cash.
Scenarios change ONLY profit target touch assumption / fee type.
A limit-touch does NOT prove a fill; bps trade-through is an artificial
sensitivity buffer, not evidence of real execution.
"""
from __future__ import annotations
from .daytrade_one_per_day import replay_one_per_day, PAIRS
from .intraday_net_target import ExecutionCosts

SCENARIOS=(
    ("old_taker_touch",0.,None),
    ("taker_trade_through_10bps",10.,None),
    ("taker_trade_through_30bps",30.,None),
    # Entry and stop assumed taker. Maker TP has 15bps fee and zero
    # market-order slippage; fill buffer 10/30bps is separate.
    ("maker_tp_10bps_through",10.,
        ExecutionCosts(25.,15.,15.,0.)),
    ("maker_tp_30bps_through",30.,
        ExecutionCosts(25.,15.,15.,0.)),
)


def evaluate(prepared, buffer_bps, maker_tp_costs, *, doubled=False):
    starting=5000.
    cash=starting
    traded_days=set()
    counts={"buy":0,"tp":0,"stop":0,"day_end":0,"gap":0}
    baseline=ExecutionCosts(50,50,30,30) if doubled else ExecutionCosts()
    profit_costs=None
    if maker_tp_costs is not None:
        profit_costs=ExecutionCosts(
            baseline.entry_fee_bps,30. if doubled else 15.,
            baseline.entry_slippage_bps,0.)
    for feeds,caches in prepared:
        signal=lambda b,i:i in caches[
            "BTC-EUR" if b is feeds["BTC-EUR"] else "ETH-EUR"
        ]["morning_strict"]
        out=replay_one_per_day(
            feeds,capital=cash,costs=baseline,
            signal=signal,previously_traded_days=traded_days,
            first_entry_index=160,tp_fill_buffer_bps=buffer_bps,
            take_profit_costs=profit_costs)
        cash=out["end_eur"]
        traded_days.update(out["daily_trade_dates"])
        counts["buy"]+=out["buys"]
        counts["tp"]+=out["full_take_profits"]
        counts["stop"]+=out["stop_exits"]
        counts["day_end"]+=out["session_end_exits"]
        counts["gap"]+=out["end_segment_forced_exits"]
    return {"ending_eur":round(cash,2),
            "profit_eur":round(cash-starting,2),
            "trades_and_exits":counts,
            "verified_limit_fills":False,
            "income_tax_included":False}


def study(prepared):
    return {"mode":"READ_ONLY_FIVE_YEAR_TP_FILL_SENSITIVITY",
            "entries":"unchanged morning_strict",
            "results":{
                name:{
                    "normal":evaluate(prepared,buffer,costs),
                    "double":evaluate(prepared,buffer,costs,doubled=True)
                }
                for name,buffer,costs in SCENARIOS
            },
            "live_orders":False,
            "warning":"A 5-minute candle trading 10 or 30bps above the TP "
                "does NOT guarantee a maker order fill. Spot execution, "
                "order-book queue, real spreads, fees and market impact "
                "require prospective verification; past data inspected. "
                "No tax or independent evidence of positive returns."}
