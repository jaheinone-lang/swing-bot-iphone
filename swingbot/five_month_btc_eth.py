"""150-day BTC + ETH shared paper portfolio, gap-aware (no invented prices).

Intersects actual exchange bar timestamps and separately replays each contiguous
section. Positions are *assumed liquidated* at section's last observed close;
fees charged and portfolio cash carried forward. Any section <110 bars is
excluded; gap-period PnL cannot be assessed. Never pretend 150d uninterrupted.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from .bitvavo_intraday_history import (
    historical_five_minute,contiguous_observed_segments,BAR_MS)
from .intraday_net_target import ExecutionCosts
from .shared_btc_eth_portfolio import shared_replay,PAIRS

def five_month_research(*, days=150):
    data={s:historical_five_minute(s,days=days,require_complete=False)
          for s in PAIRS}
    hashes={s:{b["timestamp_ms"]:b for b in data[s]} for s in PAIRS}
    common=sorted(set(hashes[PAIRS[0]])&set(hashes[PAIRS[1]]))
    observed=[hashes[PAIRS[0]][t] for t in common]
    sections=contiguous_observed_segments(observed,min_bars=120)
    cash=5000.
    double_cash=5000.
    outputs=[]
    for seq in sections:
        keys=[b["timestamp_ms"] for b in seq]
        feed={s:[hashes[s][t] for t in keys] for s in PAIRS}
        a=shared_replay(feed,capital=cash,first_entry_index=110)
        stress=shared_replay(feed,capital=double_cash,first_entry_index=110,
            costs=ExecutionCosts(50,50,30,30))
        cash=a["final_liquidation_estimate_eur"]
        double_cash=stress["final_liquidation_estimate_eur"]
        outputs.append({"first":keys[0],"last":keys[-1],
            "bars":len(keys),
            "trades":a["buys"],"takeprofits":a["half_take_profits"],
            "stops":a["stop_exits"],"end_eur":cash,
            "end_double_cost_eur":double_cash})
    expected=days*288
    return {
        "mode":"NO_LIVE_150D_SHARED_PORTFOLIO",
        "days_requested":days,"bars_expected":expected,
        "btc_bars":len(data["BTC-EUR"]),
        "eth_bars":len(data["ETH-EUR"]),
        "common_bars":len(common),
        "missing_or_unmatched":expected-len(common),
        "eligible_segments":len(sections),
        "bars_in_eligible_segments":sum(x["bars"] for x in outputs),
        "segments":outputs,
        "initial_eur":5000,
        "final_eur_modelled":round(cash,2),
        "final_eur_double_costs":round(double_cash,2),
        "pnl_eur_modelled":round(cash-5000,2),
        "pnl_eur_double_costs":round(double_cash-5000,2),
        "completed_order_count":sum(x["trades"] for x in outputs),
        "tax_included":False,
        "warning":"IMPORTANT: missing market intervals are excluded; "
        "each eligible segment restarts flat after estimated last-close "
        "liquidation (including exit costs). Sections <120 candles not traded. "
        "Results are not a continuous full-horizon 5m backtest; "
        "excluded intervals can materially change performance. "
        "No 1% daily guarantee, no actual fills and no real orders."
    }

if __name__=="__main__":
    print(json.dumps(five_month_research(),ensure_ascii=False,indent=2))
