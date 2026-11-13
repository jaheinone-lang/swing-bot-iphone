"""150-day BTC/ETH pooled account: stop, TP and fee stress experiment.

All candidates are predeclared here and scored on the older 90 days only.
Final 60 days is descriptive chronological later validation and MUST NOT
be used to pick/tune the winner. The historical data was previously seen,
so this is not independent real-world out-of-sample validation.
No real/paper account trading.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from .bitvavo_intraday_history import (
    historical_five_minute, contiguous_observed_segments, BAR_MS)
from .btc_eth_quality_gate import quality_buy_signal
from .intraday_net_target import ExecutionCosts
from .shared_btc_eth_portfolio import shared_replay, PAIRS

START_CASH = 5000.
WARMUP = 160
DOUBLE_COSTS = ExecutionCosts(50, 50, 30, 30)


@dataclass(frozen=True)
class ExitPolicy:
    name: str
    stop_pct: float
    take_profit_pct: float
    sell_fraction: float


# Do not change based on later-window performance.
PREDECLARED = (
    ExitPolicy("control_stop1p5_tp1_half", 1.5, 1., .5),
    ExitPolicy("stop0p8_tp1_half", .8, 1., .5),
    ExitPolicy("stop2p5_tp1_half", 2.5, 1., .5),
    ExitPolicy("stop1p5_tp2_half", 1.5, 2., .5),
    ExitPolicy("stop1p5_tp1_full", 1.5, 1., 1.),
    ExitPolicy("stop1p5_tp2_full", 1.5, 2., 1.),
)


def _period_windows(maps: dict, *, split_ms: int):
    """Build non-overlapping TRADE windows with 160-bar indicator warmup.

    Every section is independent and is flat/liquidated at observed last
    close. Missing/gapped intervals are excluded, never interpolated.
    Training and later holdout cannot share executed trades.
    """
    common = sorted(set(maps[PAIRS[0]]) & set(maps[PAIRS[1]]))
    pieces = contiguous_observed_segments(
        [maps[PAIRS[0]][t] for t in common], min_bars=WARMUP + 21
    )
    windows = {"train": [], "later": []}
    for piece in pieces:
        for period in ("train", "later"):
            selected = [x for x in piece if
                        (x["timestamp_ms"] < split_ms if period == "train"
                         else x["timestamp_ms"] >= split_ms)]
            if len(selected) < 21:
                continue
            # Directly preceding 160 candles only if the segment includes
            # those observations; no cross-gap indicator peeking.
            at_start = piece.index(selected[0])
            warmup = piece[max(0, at_start - WARMUP):at_start]
            combined = warmup + selected
            if len(combined) < WARMUP + 21:
                # Train sections are usually from segment start, so first
                # WARMUP bars within combined become indicator-only.
                if len(selected) < WARMUP + 21:
                    continue
                first_idx = WARMUP
            else:
                first_idx = WARMUP if len(warmup) == WARMUP else max(WARMUP, len(warmup))
            # Require at least 20 eligible completed candles for entries.
            if len(combined) - first_idx < 21:
                continue
            times = [x["timestamp_ms"] for x in combined]
            feed = {symbol: [maps[symbol][t] for t in times] for symbol in PAIRS}
            windows[period].append((feed, first_idx, len(selected)))
    return windows, len(common), len(pieces)


def _evaluate(sections, spec: ExitPolicy, *, fees: ExecutionCosts):
    cash = START_CASH
    buys = full_tp = half_tp = stops = 0
    max_window_drawdown = 0.
    tradeable_candles = 0
    for feeds, first_index, eligible_count in sections:
        trial=shared_replay(
            feeds, capital=cash, costs=fees, signal=quality_buy_signal,
            first_entry_index=first_index, stop_pct=spec.stop_pct,
            take_profit_pct=spec.take_profit_pct,
            take_fraction=spec.sell_fraction
        )
        cash=trial["final_liquidation_estimate_eur"]
        buys+=trial["buys"]
        half_tp+=trial["half_take_profits"]
        full_tp+=trial["full_take_profits"]
        stops+=trial["stop_exits"]
        max_window_drawdown=max(max_window_drawdown,
                                trial["max_marked_drawdown_pct"])
        tradeable_candles+=eligible_count
    return {
        "final_eur": round(cash, 2),
        "profit_eur": round(cash-START_CASH, 2),
        "buys": buys,
        "half_take_profits": half_tp,
        "full_take_profits": full_tp,
        "stop_exits": stops,
        "max_within_window_drawdown_pct": round(max_window_drawdown, 2),
        "eligible_bars_including_warmup": tradeable_candles,
        "segments": len(sections),
    }


def study(days: int = 150):
    bars={sym: historical_five_minute(sym,days=days,require_complete=False)
          for sym in PAIRS}
    by_ms={sym:{bar["timestamp_ms"]: bar for bar in bars[sym]}
           for sym in PAIRS}
    last=min(max(by_ms[s]) for s in PAIRS)
    split_ms=last-60*288*BAR_MS
    windows, common, runs=_period_windows(by_ms,split_ms=split_ms)
    if not windows["train"] or not windows["later"]:
        raise ValueError("Insufficient chronological train and later windows")

    rows=[]
    for spec in PREDECLARED:
        t=_evaluate(windows["train"],spec,fees=ExecutionCosts())
        ts=_evaluate(windows["train"],spec,fees=DOUBLE_COSTS)
        rows.append({
            "policy":spec.__dict__,
            "train":t,
            "train_double_cost":ts,
            "training_qualifies": (
                t["buys"]>=20 and t["profit_eur"]>0 and
                ts["profit_eur"]>0
            ),
        })
    eligible=[x for x in rows if x["training_qualifies"]]
    winner=(max(eligible,key=lambda x:x["train_double_cost"]["profit_eur"])
            if eligible else None)

    # For transparency, display later results for all preregistered policies,
    # but do NOT use these figures to select a winner.
    for row in rows:
        spec=ExitPolicy(**row["policy"])
        row["later"]=_evaluate(windows["later"],spec,fees=ExecutionCosts())
        row["later_double_cost"]=_evaluate(
            windows["later"],spec,fees=DOUBLE_COSTS)
    return {
        "mode":"READ_ONLY_TRAIN_THEN_LATER_EXIT_RESEARCH",
        "days_requested":days,
        "initial_eur_per_period":START_CASH,
        "chronological_training_days":days-60,
        "chronological_later_days":60,
        "training_segments":len(windows["train"]),
        "later_segments":len(windows["later"]),
        "common_observed_candles":common,
        "contiguous_segments_before_split":runs,
        "candidates":rows,
        "training_selected_candidate":winner["policy"]["name"] if winner else None,
        "approved_for_live":False,
        "caveat":"Multiple tests evaluated on historically seen data. "
                 "No real execution, taxes or guaranteed take-profit fill. "
                 "Gaps and sectional flat resets distort performance. "
                 "Later data MUST NOT be used to retune or declare proven edge.",
    }


if __name__ == "__main__":
    print(json.dumps(study(),indent=2))
