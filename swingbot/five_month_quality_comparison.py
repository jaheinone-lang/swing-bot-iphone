"""Compare predeclared quality gate versus old BTC ETH strategy on same 150d.

This is a retrospective, descriptive test, NOT independent validation of
profitability. One pooled account per scenario; identical historical gaps.
"""
from __future__ import annotations
import json
from .bitvavo_intraday_history import historical_five_minute,contiguous_observed_segments
from .shared_btc_eth_portfolio import shared_replay,PAIRS
from .intraday_risk_regime import regime_buy_signal
from .btc_eth_quality_gate import quality_buy_signal
from .intraday_net_target import ExecutionCosts

def run(days=150):
    feed={s:historical_five_minute(s,days=days,require_complete=False)
          for s in PAIRS}
    lookups={s:{b["timestamp_ms"]:b for b in feed[s]} for s in PAIRS}
    common=sorted(set(lookups[PAIRS[0]])&set(lookups[PAIRS[1]]))
    sections=contiguous_observed_segments(
        [lookups[PAIRS[0]][t] for t in common],min_bars=180)
    results={}
    for name,signal in (("existing",regime_buy_signal),
                        ("quality_gate",quality_buy_signal)):
        normal=5000.;stress=5000.
        buys=0; wins=0;stops=0
        for seq in sections:
            keys=[b["timestamp_ms"] for b in seq]
            rows={s:[lookups[s][t] for t in keys] for s in PAIRS}
            outcome=shared_replay(rows,capital=normal,signal=signal,
                                  first_entry_index=160)
            fee_outcome=shared_replay(rows,capital=stress,signal=signal,
                first_entry_index=160,costs=ExecutionCosts(50,50,30,30))
            normal=outcome["final_liquidation_estimate_eur"]
            stress=fee_outcome["final_liquidation_estimate_eur"]
            buys+=outcome["buys"]
            wins+=outcome["half_take_profits"]
            stops+=outcome["stop_exits"]
        results[name]={"end_eur":round(normal,2),
            "profit_eur":round(normal-5000,2),
            "double_cost_end_eur":round(stress,2),
            "double_cost_profit_eur":round(stress-5000,2),
            "buys":buys,"half_tp_events":wins,"stop_events":stops}
    return {"mode":"HISTORICAL_DESCRIPTIVE_NOT_DEPLOYABLE",
            "days":days,"common_candles":len(common),
            "eligible_contiguous_segments":len(sections),
            "evaluated_candles":sum(len(x) for x in sections),
            "models":results,
            "warning":"Neither strategy has proven positive expectancy. "
            "This selection is based on already examined historical data. "
            "Gap-segmented, estimated fills, no tax or live orders."}

if __name__=="__main__":print(json.dumps(run(),indent=2))
