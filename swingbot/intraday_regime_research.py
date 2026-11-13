"""Read-only regime/risk overlay trial vs frozen 5m signal baseline."""
from __future__ import annotations
import json
from .bitvavo_intraday_history import historical_five_minute,contiguous_observed_segments
from .intraday_research import replay
from .intraday_entry_filters import filtered_buy_signal
from .intraday_risk_regime import regime_buy_signal,max_affordable_units
from .intraday_net_target import ExecutionCosts

def compare():
    out={"mode":"READ_ONLY_REGIME_RISK_RESEARCH","assets":{}}
    for symbol in ("BTC-EUR","ETH-EUR","SOL-EUR"):
        raw=historical_five_minute(symbol,days=7,require_complete=False)
        segments=contiguous_observed_segments(raw,min_bars=400)
        if not segments:
            out["assets"][symbol]={"status":"NO_LONG_ENOUGH_CONTIGUOUS_SEGMENT"}
            continue
        bars=max(segments,key=len)
        split=int(len(bars)*.6)
        data=bars[split-110:]
        old=replay(data,signal=filtered_buy_signal,first_entry_index=110)
        new=replay(data,signal=regime_buy_signal,first_entry_index=110,
                   sizing=lambda cash,equity,price:max_affordable_units(
                       cash,equity,price,stop_raw_price=price*.985))
        stressed=replay(data,signal=regime_buy_signal,first_entry_index=110,
                        costs=ExecutionCosts(50,50,30,30),
                        sizing=lambda cash,equity,price:max_affordable_units(
                           cash,equity,price,stop_raw_price=price*.985,
                           costs=ExecutionCosts(50,50,30,30)))
        out["assets"][symbol]={"observed_contiguous_bars":len(bars),
            "holdout_bars":len(bars)-split,
            "baseline_pnl_eur":old["estimated_pnl_eur"],
            "regime_risk_pnl_eur":new["estimated_pnl_eur"],
            "regime_risk_double_cost_eur":stressed["estimated_pnl_eur"],
            "baseline_buys":old["buys"],"regime_buys":new["buys"],
            "baseline_drawdown_pct":old["max_mark_to_market_drawdown_pct"],
            "regime_drawdown_pct":new["max_mark_to_market_drawdown_pct"]}
    out["warning"]="Very short retrospective data and no individual trade tax. "
    out["warning"]+="No live/paper orders or automatic strategy selection."
    return out

if __name__=="__main__":
    print(json.dumps(compare(),indent=2))
