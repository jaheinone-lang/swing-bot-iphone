"""BTC/ETH only read-only intraday strategy configuration.

SOL intentionally excluded from active candidate markets but retained
as an observation-only benchmark in other research modules.
No exchange orders or modification of existing forward paper ledger.
"""
from __future__ import annotations
import json
from .bitvavo_intraday_history import historical_five_minute, contiguous_observed_segments
from .intraday_research import replay
from .intraday_risk_regime import regime_buy_signal, max_affordable_units
from .intraday_net_target import ExecutionCosts

ACTIVE_PAIRS=("BTC-EUR","ETH-EUR")
OBSERVE_ONLY=("SOL-EUR",)
STARTING_EUR=5000.
RISK_PER_TRADE_PCT=.25
MAX_POSITION_PCT=20.
NET_TP_PCT=1.

def compare():
    result={"mode":"READ_ONLY_BTC_ETH_ONLY", "active_pairs":ACTIVE_PAIRS,
            "observe_only":OBSERVE_ONLY, "markets":{}}
    for symbol in ACTIVE_PAIRS:
        bars=historical_five_minute(symbol,days=7,require_complete=False)
        segments=contiguous_observed_segments(bars,min_bars=400)
        if not segments:
            result["markets"][symbol]={"status":"INSUFFICIENT_HISTORY"}
            continue
        series=max(segments,key=len)
        cut=int(len(series)*.6)
        holdout=series[cut-110:]
        costs=ExecutionCosts()
        # Conservative entry risk budget, no cross-asset allocation claim:
        # each series is an INDEPENDENT €5k research account.
        size=lambda cash,equity,price:max_affordable_units(
            cash,equity,price,stop_raw_price=price*.985,
            risk_budget_pct=RISK_PER_TRADE_PCT,
            max_position_pct=MAX_POSITION_PCT,costs=costs)
        outcome=replay(holdout,initial_eur=STARTING_EUR,costs=costs,
                       signal=regime_buy_signal,
                       first_entry_index=110,sizing=size)
        result["markets"][symbol]={
            "outcome":outcome,"available_contiguous_bars":len(series)}
    result["policy"]={
        "max_nominal_risk_per_trade_pct":RISK_PER_TRADE_PCT,
        "max_position_pct":MAX_POSITION_PCT,
        "target_net_after_trading_costs_before_tax_pct":NET_TP_PCT,
        "actual_live_orders":False,
        "joint_portfolio_simulated":False}
    result["warning"]="Separate 5000 EUR accounts, not pooled 5000 EUR. "
    result["warning"]+="Short retrospective test, model execution, tax excluded. "
    result["warning"]+="Risk limit is nominal, gap or slippage losses can exceed it."
    return result

if __name__=="__main__":
    print(json.dumps(compare(),indent=2))
