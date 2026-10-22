"""Cross-asset, nonoverlapping historical 5-minute entry-filter robustness test.

Not independent prospective data: these frozen filters were conceived knowing
prior market histories. Evaluates each asset and time block without selecting
the strongest result or hiding inactive windows. No live orders.
"""
from __future__ import annotations
import json
from .bitvavo_intraday import intraday_candles
from .intraday_entry_filters import filtered_buy_signal
from .intraday_research import replay
from .intraday_net_target import ExecutionCosts

PAIRS=("BTC-EUR","ETH-EUR","SOL-EUR")
COSTS=(("base",ExecutionCosts()),
       ("double_costs",ExecutionCosts(50,50,30,30)))


def compare_windows(bars: list[dict], *, blocks: int = 3,
                    history_bars: int = 80) -> list[dict]:
    if blocks < 2 or history_bars < 60 or len(bars) < history_bars+blocks*100:
        raise ValueError("Insufficient data for distinct independent windows")
    # Each window starts with its own initial 5000 EUR and pre-window indicator
    # warm-up bars. The first 60 bars never cause an entry for the filtered rule.
    active=(len(bars)-history_bars)//blocks
    reports=[]
    for index in range(blocks):
        left=history_bars+index*active
        right=(history_bars+(index+1)*active
               if index < blocks-1 else len(bars))
        history=bars[left-history_bars:right]
        result={}
        for cost_name,cost in COSTS:
            old=replay(history,signal=None,costs=cost)
            filtered=replay(history,signal=filtered_buy_signal,costs=cost)
            result[cost_name]={
                "old": {k: old[k] for k in (
                    "estimated_pnl_eur","buys","half_take_profits",
                    "full_or_partial_stop_exits","max_mark_to_market_drawdown_pct")},
                "filtered": {k: filtered[k] for k in (
                    "estimated_pnl_eur","buys","half_take_profits",
                    "full_or_partial_stop_exits","max_mark_to_market_drawdown_pct")},
            }
        reports.append({
            "segment":index+1,"first_tradeable_ms":bars[left]["timestamp_ms"],
            "last_ms":bars[right-1]["timestamp_ms"],
            "indicator_warmup_bars":history_bars,
            "results":result,
        })
    return reports


def main():
    report={"mode":"READ_ONLY_MULTIMARKET_ROBUSTNESS",
            "assets":{},"warnings":[
                "Only ~1000 completed 5-minute bars per symbol, not months.",
                "A replay segment includes indicator warmup before its "
                "designated trade period. Baseline may trade in warmup; "
                "results therefore remain exploratory and not a clean "
                "independent trade-window comparison.",
                "No taxes. Simulated fill/liquidity, no true live execution.",
                "No model tuning or automatic strategy deployment.",
            ]}
    for pair in PAIRS:
        bars=intraday_candles(pair,limit=1000)
        report["assets"][pair]=compare_windows(bars)
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
