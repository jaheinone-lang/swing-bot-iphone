"""Independent read-only diagnostics for a crypto swing research replay.

Do not modify strategy selection, historic trade fills, or the persistent
forward paper state. Same-bar BUY/HOLD baselines begin only after a uniform
201-completed-candle warmup to support the longest indicator.
"""
from __future__ import annotations

from .research_metrics import _metrics, buy_and_hold_equal_weight

WARMUP_BARS = 201
WINDOW_DAYS = 90


def hold_benchmarks(data: dict, markets: dict, starting_eur: float, split_day: str) -> dict:
    """Two transparent BTC / equal basket controls, same clock and start."""
    choices = (
        ("BTC only", {"BTC-EUR": data["BTC-EUR"]}, {"BTC-EUR": "crypto"}),
        ("Equal BTC-ETH-SOL", data, markets),
    )
    results = {}
    for name, prices, kinds in choices:
        replay = buy_and_hold_equal_weight(
            prices, kinds, initial_eur=starting_eur, warmup_bars=WARMUP_BARS
        )
        curve = replay["daily_curve"]
        later = [row for row in curve if row["day"] >= split_day]
        results[name] = {
            "warmup_bars": WARMUP_BARS,
            "invest_after": replay["invest_after"],
            "final_equity_eur": replay["final_equity_eur"],
            "entry_fees_eur": replay["estimated_buy_fees_eur"],
            "whole_period": _metrics(curve),
            "later_period": _metrics(later),
            "caveat": (
                "Unrealized gain is not taxed; entry fees/slippage only; "
                "no end-of-test selling costs or Finnish tax on liquidation."
            ),
        }
    return results


def contiguous_windows(curve: list[dict], *, begin_day: str,
                       window_days: int = WINDOW_DAYS) -> list[dict]:
    """Disjoint consecutive 90-day periods; ignore unfinished final fragment.

    Start of the next window equals prior end so period returns never overlap
    and every complete period has exactly window_days daily changes.
    """
    if window_days < 2:
        raise ValueError("Require at least two days per window")
    series = [row for row in curve if row["day"] >= begin_day]
    periods = []
    for start in range(0, len(series) - window_days, window_days):
        part = series[start:start + window_days + 1]
        metrics = _metrics(part)
        if metrics["calendar_days"] != window_days:
            raise ValueError("Gap in daily research equity curve")
        periods.append({
            "start": metrics["period_start"],
            "end": metrics["period_end"],
            "return_pct": metrics["total_return_pct"],
            "max_drawdown_pct": metrics["max_drawdown_pct"],
        })
    return periods


def window_summary(windows: list[dict]) -> dict:
    if not windows:
        raise ValueError("No complete 90-day windows")
    returns = [r["return_pct"] for r in windows]
    return {
        "windows_count": len(windows),
        "losing_windows": sum(r < 0 for r in returns),
        "worst_90d_return_pct": min(returns),
        "best_90d_return_pct": max(returns),
        "max_90d_drawdown_pct": max(r["max_drawdown_pct"] for r in windows),
        "windows": windows,
    }
