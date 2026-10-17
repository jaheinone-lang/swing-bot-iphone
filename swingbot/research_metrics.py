"""Transparent research-only comparison of a swing strategy to equal-weight hold.

Uses the exact same EUR OHLC history and illustrative fee/slippage model as
the strategy backtest. No strategy optimisation, no live orders, no secrets.
Raw historical stock candles can omit dividends, splits, delistings and taxes:
comparisons are *not* total-return or investable performance estimates.
"""
from __future__ import annotations

from datetime import date
from math import floor, sqrt, isfinite
from statistics import mean, stdev
from typing import Mapping, Sequence

from .portfolio import Bar, COST_BPS, _validated


def _metrics(curve: Sequence[dict], *, year_days: int = 365) -> dict:
    """Statistics on calendar-day union of observations, zero cash rate."""
    if len(curve) < 2:
        raise ValueError("At least two equity observations are needed")
    days = [date.fromisoformat(row["day"]) for row in curve]
    balances = [float(row["equity_eur"]) for row in curve]
    if any(not isfinite(x) or x <= 0 for x in balances):
        raise ValueError("All equity values must be positive and finite")
    if any(a >= b for a, b in zip(days, days[1:])):
        raise ValueError("Equity curve must have strictly increasing days")
    elapsed = (days[-1] - days[0]).days
    if elapsed < 1:
        raise ValueError("Time span too short")
    peak, max_drawdown = balances[0], 0.0
    for equity in balances:
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
    change = balances[-1] / balances[0] - 1
    # Include every calendar day in the risk series. Non-observation dates
    # are treated as carrying forward last known equity. This is necessary
    # for stock-only portfolios and conservative when markets are closed.
    by_day = dict(zip(days, balances))
    previous = balances[0]
    start = days[0]
    from datetime import timedelta
    returns = []
    for step in range(1, elapsed + 1):
        mark = by_day.get(start + timedelta(days=step), previous)
        returns.append(mark / previous - 1)
        previous = mark
    deviation = stdev(returns) if len(returns) >= 2 else 0.0
    # These daily closes cannot measure intraday/gap volatility faithfully.
    return {
        "period_start": days[0].isoformat(),
        "period_end": days[-1].isoformat(),
        "calendar_days": elapsed,
        "total_return_pct": round(100 * change, 2),
        "cagr_pct": round(100 * ((balances[-1] / balances[0]) ** (year_days / elapsed) - 1), 2)
        if elapsed >= 60 else None,
        "max_drawdown_pct": round(100 * max_drawdown, 2),
        "annualized_volatility_pct": round(100 * deviation * sqrt(year_days), 2)
        if elapsed >= 60 else None,
        "sharpe_zero_cash_rate": round(mean(returns) / deviation * sqrt(year_days), 2)
        if elapsed >= 60 and deviation > 1e-12 else None,
    }


def buy_and_hold_equal_weight(
    data: Mapping[str, Sequence[Bar]],
    markets: Mapping[str, str],
    *,
    initial_eur: float = 5000.0,
    warmup_bars: int = 51,
) -> dict:
    """Invest equal EUR budgets after 51 completed bars per asset.

    Each asset fills at its next available OPEN. No rebalancing; unused budget
    remains cash. Costs are illustrative. Mark-to-market uses completed closes.
    """
    _validated(data, markets)
    if initial_eur <= 0 or not isfinite(initial_eur):
        raise ValueError("Invalid initial equity")
    if warmup_bars < 2 or any(len(bars) < warmup_bars + 2 for bars in data.values()):
        raise ValueError("Not enough history for a warmup-aligned comparison")
    start_day = min(bars[0].day for bars in data.values())
    invest_after = max(bars[warmup_bars - 1].day for bars in data.values())
    by_day: dict[date, dict[str, Bar]] = {}
    for symbol, bars in data.items():
        for bar in bars:
            by_day.setdefault(bar.day, {})[symbol] = bar
    cash = initial_eur
    per_symbol_budget = initial_eur / len(data)
    shares: dict[str, float] = {}
    marks: dict[str, float] = {}
    fills = {}
    fees = 0.0
    curve = []
    for day, active in sorted(by_day.items()):
        # Capture old closes for closed markets, then mark after new bars arrive.
        for symbol, bar in sorted(active.items()):
            if day > invest_after and symbol not in shares:
                fee_bps, slippage_bps = COST_BPS[markets[symbol]]
                fill = bar.open * (1 + slippage_bps / 10000)
                max_cash = min(cash, per_symbol_budget)
                precision = 0 if markets[symbol] == "stock" else 8
                units = floor(max_cash / (fill * (1 + fee_bps / 10000)) * 10 ** precision) / (
                    10 ** precision
                )
                if units > 0:
                    fee = units * fill * fee_bps / 10000
                    cash -= units * fill + fee
                    fees += fee
                    shares[symbol] = units
                    fills[symbol] = {
                        "day": day.isoformat(), "price_eur": round(fill, 6),
                        "quantity": units, "fee_eur": round(fee, 4),
                    }
            marks[symbol] = bar.close
        equity = cash + sum(shares[symbol] * marks[symbol] for symbol in shares)
        curve.append({"day": day.isoformat(), "equity_eur": equity})
    return {
        "start": start_day.isoformat(), "invest_after": invest_after.isoformat(),
        "initial_eur": initial_eur, "final_equity_eur": round(curve[-1]["equity_eur"], 2),
        "estimated_buy_fees_eur": round(fees, 2),
        "positions_bought": len(shares), "expected_positions": len(data),
        "fills": fills, "daily_curve": curve,
    }


def compare_to_hold(
    data: Mapping[str, Sequence[Bar]],
    markets: Mapping[str, str],
    swing_result: dict,
) -> dict:
    """Compare consistent starting capital and common completed-price dates."""
    baseline = buy_and_hold_equal_weight(data, markets, initial_eur=swing_result["starting_eur"])
    curve = swing_result["daily_curve"]
    if [x["day"] for x in curve] != [x["day"] for x in baseline["daily_curve"]]:
        raise ValueError("Benchmark and swing use different calendar dates")
    swing = _metrics(curve)
    hold = _metrics(baseline["daily_curve"])
    from datetime import timedelta
    last_day = date.fromisoformat(curve[-1]["day"])
    threshold = last_day - timedelta(days=180)
    start_idx = next((i for i, row in enumerate(curve)
                      if date.fromisoformat(row["day"]) >= threshold), None)
    # Last 180 days refers to a fixed segment of ONE unchanged full replay,
    # not a separately tuned out-of-sample strategy.
    recent = None
    if start_idx is not None and len(curve) - start_idx >= 61:
        recent = {
            "label": "Viimeiset 180 kalenteripäivää (ei riippumaton validointi)",
            "swing": _metrics(curve[start_idx:]),
            "buy_hold": _metrics(baseline["daily_curve"][start_idx:]),
        }
    return {
        "kind": "RESEARCH_ONLY_HISTORICAL_SIMULATION",
        "benchmark": "equal_EUR_buy_hold_no_rebalance",
        "benchmark_warmup_bars": 51,
        "benchmark_invest_after": baseline["invest_after"],
        "method_note": (
            "Sama EUR-historia ja lähtöpääoma. Osta ja pidä sijoittaa tasaisesti "
            "seuraavaan avaukseen 51 kynttilän lämmittelyn jälkeen, ilman "
            "uudelleentasapainotusta. Swing ostaa vain signaalista ja voi "
            "pitää käteistä. Ei sama markkinariski eikä validoitu etu."
        ),
        "limitations": (
            "Epävirallinen osakedata ei sisällä varmennettua osinkojen, splittien, "
            "delistausten tai verojen käsittelyä. Oletetut kulut eivät ole toteutuneita. "
            "Kryptomarkkinat ovat auki myös viikonloppuisin."
        ),
        "swing": swing,
        "buy_hold": hold,
        "excess_return_percentage_points": round(
            swing["total_return_pct"] - hold["total_return_pct"], 2
        ),
        "benchmark_final_equity_eur": baseline["final_equity_eur"],
        "benchmark_buy_fees_eur": baseline["estimated_buy_fees_eur"],
        "comparison_window": {
            "start": curve[0]["day"], "end": curve[-1]["day"],
        },
        "last_180_days": recent,
    }
