"""EUR-denominated, long-only, NEXT-BAR-OPEN paper backtest.

Never submits orders. Stocks use whole shares; crypto uses 8 decimal places.
Daily close timestamps across exchanges are approximate and NOT simultaneous.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import floor, isfinite
from typing import Mapping, Sequence

from .strategy import evaluate_signal


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        values = (self.open, self.high, self.low, self.close)
        if not all(isfinite(x) and x > 0 for x in values):
            raise ValueError("OHLC prices must be finite and positive")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("OHLC bar violates its high/low range")


@dataclass
class Position:
    quantity: float
    stop: float
    entry_price: float
    entry_day: date


# Conservative ILLUSTRATIVE costs; actual fee tiers vary by broker / exchange.
COST_BPS = {"stock": (10.0, 5.0), "crypto": (40.0, 15.0)}
MAX_DRAWDOWN = 0.25


def _atr(bars: Sequence[Bar], days: int = 14) -> float:
    if len(bars) < days + 1:
        return 0.0
    ranges = []
    for i in range(len(bars) - days, len(bars)):
        b, previous = bars[i], bars[i - 1]
        ranges.append(max(b.high - b.low, abs(b.high - previous.close),
                          abs(b.low - previous.close)))
    return sum(ranges) / len(ranges)


def _validated(data: Mapping[str, Sequence[Bar]], markets: Mapping[str, str]):
    if not data or set(data) != set(markets):
        raise ValueError("Each symbol needs a market type and at least one bar")
    for symbol, bars in data.items():
        if markets[symbol] not in COST_BPS or not bars:
            raise ValueError(f"Invalid market or missing data for {symbol}")
        if any(a.day >= b.day for a, b in zip(bars, bars[1:])):
            raise ValueError(f"Dates must be strictly increasing for {symbol}")


def backtest(
    data: Mapping[str, Sequence[Bar]],
    markets: Mapping[str, str],
    initial_eur: float = 5000.0,
) -> dict:
    """Simulate closed-bar signals, next eligible open fills and intraday stops.

    All assets MUST be quoted in EUR. Splits and distributions must be
    adjusted in upstream input. Fractional shares are not supported.
    """
    _validated(data, markets)
    if not isfinite(initial_eur) or initial_eur <= 0:
        raise ValueError("initial_eur must be positive")
    by_day = {}
    for symbol, bars in data.items():
        for bar in bars:
            by_day.setdefault(bar.day, {})[symbol] = bar

    cash = initial_eur
    peak = initial_eur
    latest = {}
    history = {symbol: [] for symbol in data}
    positions = {}
    pending = {}
    events = []
    curve = []
    total_fees = 0.0
    halted = False

    def fill_exit(symbol, price, day, reason):
        nonlocal cash, total_fees
        position = positions.pop(symbol)
        fee_bps, slip_bps = COST_BPS[markets[symbol]]
        sell_price = max(0.0, price * (1 - slip_bps / 10000))
        proceeds = position.quantity * sell_price
        fee = proceeds * fee_bps / 10000
        total_fees += fee
        cash += proceeds - fee
        events.append({
            "day": day.isoformat(), "symbol": symbol, "side": "SELL",
            "reason": reason, "price": round(sell_price, 6),
            "quantity": round(position.quantity, 8), "fee_eur": round(fee, 4),
        })

    for day in sorted(by_day):
        active = by_day[day]
        stopped_today = set()
        # Exits of OLD positions happen before entries; a gap crosses the stop
        # at the worse opening price rather than an imaginary guaranteed stop.
        for symbol, bar in sorted(active.items()):
            position = positions.get(symbol)
            if position and bar.low <= position.stop:
                raw_price = min(bar.open, position.stop)
                fill_exit(symbol, raw_price, day, "stop")
                stopped_today.add(symbol)

        # Yesterday's close signal may only enter on the NEXT available bar.
        for symbol, bar in sorted(active.items()):
            signal_atr = pending.pop(symbol, None)
            if signal_atr is None or halted or symbol in positions or symbol in stopped_today:
                continue
            fee_bps, slip_bps = COST_BPS[markets[symbol]]
            buy_price = bar.open * (1 + slip_bps / 10000)
            stop_distance = signal_atr * 2
            stop = buy_price - stop_distance
            if stop <= 0:
                continue
            latest_value = cash + sum(
                p.quantity * latest.get(s, p.entry_price) for s, p in positions.items()
            )
            max_risk_eur = latest_value * 0.01
            qty_risk = max_risk_eur / stop_distance
            qty_cap = (latest_value * 0.20) / buy_price
            qty_cash = cash / (buy_price * (1 + fee_bps / 10000))
            qty = min(qty_risk, qty_cap, qty_cash)
            precision = 0 if markets[symbol] == "stock" else 8
            qty = floor(qty * 10 ** precision) / 10 ** precision
            if qty <= 0:
                continue
            notional = qty * buy_price
            fee = notional * fee_bps / 10000
            cash -= notional + fee
            total_fees += fee
            positions[symbol] = Position(qty, stop, buy_price, day)
            events.append({
                "day": day.isoformat(), "symbol": symbol, "side": "BUY",
                "reason": "prior_close_breakout", "price": round(buy_price, 6),
                "quantity": round(qty, 8), "fee_eur": round(fee, 4),
            })
            # Conservatively let a newly entered position stop out the same day.
            if bar.low <= stop:
                fill_exit(symbol, min(bar.open, stop), day, "same_day_stop")
                stopped_today.add(symbol)

        for symbol, bar in active.items():
            history[symbol].append(bar)
            latest[symbol] = bar.close

        equity = cash + sum(p.quantity * latest[s] for s, p in positions.items())
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak
        if drawdown >= MAX_DRAWDOWN:
            halted = True
            pending.clear()  # Never permit queued entries after a halt.
        curve.append({"day": day.isoformat(), "equity_eur": round(equity, 2),
                      "drawdown_pct": round(drawdown * 100, 2)})

        for symbol, bar in sorted(active.items()):
            bars = history[symbol]
            if symbol in positions:
                # The completed bar can only tighten tomorrow's stop.
                atr = _atr(bars)
                if atr > 0:
                    positions[symbol].stop = max(
                        positions[symbol].stop, bar.close - 2 * atr
                    )
            elif not halted and symbol not in stopped_today and symbol not in pending:
                result = evaluate_signal(
                    [x.close for x in bars], [x.high for x in bars],
                    [x.low for x in bars], equity=equity, peak_equity=peak
                )
                if result["action"] == "BUY":
                    pending[symbol] = _atr(bars)

    final_equity = curve[-1]["equity_eur"]
    return {
        "mode": "BACKTEST_ONLY_NO_REAL_ORDERS",
        "starting_eur": initial_eur,
        "final_equity_eur": final_equity,
        "pnl_eur": round(final_equity - initial_eur, 2),
        "return_pct": round(100 * (final_equity / initial_eur - 1), 2),
        "max_drawdown_pct": max(row["drawdown_pct"] for row in curve),
        "halted_new_entries": halted,
        "estimated_fees_eur": round(total_fees, 2),
        "trade_events": events,
        "open_positions": {
            s: {"quantity": round(p.quantity, 8),
                "stop": round(p.stop, 6), "last_close": latest[s]}
            for s, p in positions.items()
        },
        "pending_signals": sorted(pending),
        "daily_curve": curve,
        "symbols": {symbol: {"market": markets[symbol], "bars": len(data[symbol])}
                    for symbol in data},
    }
