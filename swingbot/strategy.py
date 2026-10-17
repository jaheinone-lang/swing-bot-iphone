"""Deterministic daily swing-entry signal and position sizing.

This prototype NEVER places orders. It uses only completed daily OHLC
bars provided by the caller. The 25% drawdown guard pauses new entries;
it cannot guarantee a maximum realized or intraday loss.
"""
from __future__ import annotations

from statistics import mean
from typing import Sequence


def evaluate_signal(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    *,
    equity: float = 5000.0,
    peak_equity: float = 5000.0,
    breakout_days: int = 20,
    trend_days: int = 50,
    atr_days: int = 14,
    risk_per_trade: float = 0.01,
    max_position_fraction: float = 0.20,
    max_drawdown: float = 0.25,
) -> dict:
    """Return a signal. BUY is hypothetical, never an executable order."""
    if not (len(closes) == len(highs) == len(lows)):
        raise ValueError("OHLC input series must have the same length")
    if not closes:
        raise ValueError("At least one price bar is required")
    if any(
        c <= 0 or l <= 0 or h <= 0 or l > h or not (l <= c <= h)
        for c, h, l in zip(closes, highs, lows)
    ):
        raise ValueError("Each candle must contain valid positive OHLC values")
    if equity < 0 or peak_equity <= 0 or equity > peak_equity:
        raise ValueError("Require 0 <= equity <= peak_equity and peak_equity > 0")
    if min(breakout_days, trend_days, atr_days) < 2:
        raise ValueError("Lookback windows must be at least 2 days")
    if not (0 < risk_per_trade <= 1 and 0 < max_position_fraction <= 1
            and 0 < max_drawdown < 1):
        raise ValueError("Risk controls must be fractions between 0 and 1")

    drawdown = (peak_equity - equity) / peak_equity
    if drawdown >= max_drawdown:
        return {"action": "HALT", "reason": "drawdown_limit",
                "drawdown_pct": round(100 * drawdown, 2), "quantity": 0.0}

    needed = max(trend_days + 1, breakout_days + 1, atr_days + 1)
    if len(closes) < needed:
        return {"action": "HOLD", "reason": "not_enough_history",
                "required_bars": needed, "quantity": 0.0}

    last = float(closes[-1])
    prior_breakout_high = max(closes[-breakout_days-1:-1])
    previous_trend_average = mean(closes[-trend_days-1:-1])
    if not (last > prior_breakout_high and last > previous_trend_average):
        return {"action": "HOLD", "reason": "no_breakout_or_trend",
                "quantity": 0.0}

    true_ranges = []
    for idx in range(len(closes) - atr_days, len(closes)):
        previous_close = closes[idx - 1]
        true_ranges.append(max(
            highs[idx] - lows[idx],
            abs(highs[idx] - previous_close),
            abs(lows[idx] - previous_close),
        ))
    atr = mean(true_ranges)
    if atr <= 0:
        return {"action": "HOLD", "reason": "zero_volatility",
                "quantity": 0.0}

    stop_distance = 2 * atr
    by_risk = (equity * risk_per_trade) / stop_distance
    by_allocation = (equity * max_position_fraction) / last
    quantity = min(by_risk, by_allocation)
    if quantity <= 0:
        return {"action": "HOLD", "reason": "insufficient_equity",
                "quantity": 0.0}

    return {
        "action": "BUY",
        "reason": "20_day_breakout_above_trend",
        "price": round(last, 6),
        "stop_price": round(max(0.0, last - stop_distance), 6),
        "quantity": round(quantity, 8),
        "notional": round(quantity * last, 2),
        "atr": round(atr, 6),
        "drawdown_pct": round(100 * drawdown, 2),
    }
