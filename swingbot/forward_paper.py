"""Persistent, daily-bar FORWARD PAPER ledger; NEVER sends actual orders.

A fill is simulated only after the NEXT daily bar has completed and the
next day's OPEN is known. It is a delayed research simulation, NOT a
live paper execution service. Financial values and positions are public.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from math import floor, isfinite
from typing import Mapping, Sequence

from .portfolio import Bar, _atr, _validated
from .strategy import evaluate_signal

INITIAL_EUR = 5000.0
RISK_FRACTION = 0.01
POSITION_CAP = 0.20
HALT_DRAWDOWN = 0.25
# Illustrative costs, not verified broker execution quotes:
# Trading 212 EUR share: zero trading commission + 5 bps slippage.
# Bitvavo: assumed taker 25 bps + 15 bps slippage per direction.
PAPER_COST_BPS = {"stock": (0.0, 5.0), "crypto": (25.0, 15.0)}
MAX_MISSED_DAYS = 7


def _money(amount: float) -> float:
    return round(amount, 6)


def _equity(state: dict) -> float:
    return state["cash_eur"] + sum(
        p["quantity"] * state["last_closes_eur"][symbol]
        for symbol, p in state["positions"].items()
    )


def _check_state(state: dict, expected_symbols: set[str]) -> None:
    if state.get("schema_version") != 1 or state.get("mode") != "DELAYED_FORWARD_PAPER":
        raise ValueError("Unsupported paper account state; refusing to reset")
    if set(state.get("last_closes_eur", {})) != expected_symbols:
        raise ValueError("Paper account symbols changed; manual migration required")
    if state["initial_eur"] != INITIAL_EUR:
        raise ValueError("Unexpected paper initial balance")
    if not (isfinite(state["cash_eur"]) and state["cash_eur"] >= -0.000001
            and isfinite(state["peak_equity_eur"])
            and state["peak_equity_eur"] > 0):
        raise ValueError("Paper account state is corrupt")
    if not set(state["positions"]).issubset(expected_symbols):
        raise ValueError("Unrecognized open position")
    if not set(state["pending"]).issubset(expected_symbols):
        raise ValueError("Unrecognized pending order")


def initialize_paper(data: Mapping[str, Sequence[Bar]], markets: Mapping[str, str]) -> dict:
    """Start today, NO replay of earlier historical prices or imaginary gains."""
    _validated(data, markets)
    started = max(bars[-1].day for bars in data.values())
    return {
        "schema_version": 1,
        "mode": "DELAYED_FORWARD_PAPER",
        "started_on": started.isoformat(),
        "last_processed_day": started.isoformat(),
        "initial_eur": INITIAL_EUR,
        "cash_eur": INITIAL_EUR,
        "peak_equity_eur": INITIAL_EUR,
        "last_closes_eur": {s: bars[-1].close for s, bars in data.items()},
        "last_price_days": {s: bars[-1].day.isoformat() for s, bars in data.items()},
        "positions": {},
        "pending": {},
        "events": [],
        "daily_equity": [{"day": started.isoformat(), "equity_eur": INITIAL_EUR,
                          "drawdown_pct": 0.0}],
        "fees_eur": 0.0,
        "halted_new_entries": False,
    }


def advance_paper(
    data: Mapping[str, Sequence[Bar]],
    markets: Mapping[str, str],
    previous: dict | None = None,
    *,
    as_of: date | None = None,
) -> dict:
    """Return new account state, leaving the supplied previous dict untouched.

    Completed candles only. Missing/stale data raises before any mutation.
    Re-running with the same candles is idempotent.
    """
    _validated(data, markets)
    today = as_of or datetime.now(timezone.utc).date()
    for symbol, bars in data.items():
        max_stale = 3 if markets[symbol] == "crypto" else 7
        age = (today - bars[-1].day).days
        if age < 1 or age > max_stale:
            raise ValueError(f"Missing, future or stale completed data for {symbol}")
    if previous is None:
        return initialize_paper(data, markets)

    import copy
    state = copy.deepcopy(previous)
    _check_state(state, set(data))
    last_day = date.fromisoformat(state["last_processed_day"])
    if (today - last_day).days > MAX_MISSED_DAYS + 1:
        raise ValueError("Update delayed >7 days. Manual review needed; no backfill trades.")
    # Earlier or identical observations must never regenerate fills.
    if all(bars[-1].day <= last_day for bars in data.values()):
        return state
    by_day: dict[date, dict[str, Bar]] = {}
    for symbol, bars in data.items():
        for bar in bars:
            if bar.day > last_day:
                by_day.setdefault(bar.day, {})[symbol] = bar
    if not by_day:
        return state
    if min(by_day) > last_day.fromordinal(last_day.toordinal() + MAX_MISSED_DAYS):
        raise ValueError("Unrecoverable gap in paper history; manual review required")

    for day, active in sorted(by_day.items()):
        stopped_today = set()
        # Existing stops; overnight gaps fill at worse next OPEN (plus slippage).
        for symbol, bar in sorted(active.items()):
            p = state["positions"].get(symbol)
            if p is not None and bar.low <= p["stop"]:
                raw = min(bar.open, p["stop"])
                _sell(state, symbol, raw, markets[symbol], day, "STOP")
                stopped_today.add(symbol)

        # Prior close signals are simulated at the following DAILY opening
        # only once that daily candle is COMPLETED and fully observed.
        for symbol, bar in sorted(active.items()):
            planned = state["pending"].pop(symbol, None)
            if planned is None or state["halted_new_entries"]:
                continue
            if symbol in state["positions"] or symbol in stopped_today:
                continue
            if date.fromisoformat(planned["signal_day"]) >= day:
                raise ValueError("Invalid pending order date")
            fee_bps, slip_bps = PAPER_COST_BPS[markets[symbol]]
            price = bar.open * (1 + slip_bps / 10000)
            stop_distance = float(planned["atr"]) * 2
            if stop_distance <= 0 or price <= stop_distance:
                continue
            budget_equity = _equity(state)
            qty = min(
                budget_equity * RISK_FRACTION / stop_distance,
                budget_equity * POSITION_CAP / price,
                state["cash_eur"] / (price * (1 + fee_bps / 10000)),
            )
            precision = 0 if markets[symbol] == "stock" else 8
            qty = floor(max(0.0, qty) * 10 ** precision) / 10 ** precision
            if qty <= 0:
                continue
            fee = qty * price * fee_bps / 10000
            state["cash_eur"] = _money(state["cash_eur"] - qty * price - fee)
            state["fees_eur"] = _money(state["fees_eur"] + fee)
            state["positions"][symbol] = {
                "quantity": qty, "entry_price_eur": _money(price),
                "entry_day": day.isoformat(), "stop_eur": _money(price - stop_distance),
            }
            _event(state, day, symbol, "BUY", qty, price, fee, "NEXT_BAR_OPEN")
            if bar.low <= price - stop_distance:
                _sell(state, symbol, min(bar.open, price - stop_distance),
                      markets[symbol], day, "SAME_DAY_STOP")
                stopped_today.add(symbol)

        for symbol, bar in active.items():
            state["last_closes_eur"][symbol] = bar.close
            state["last_price_days"][symbol] = day.isoformat()

        equity = _equity(state)
        state["peak_equity_eur"] = max(state["peak_equity_eur"], equity)
        drawdown = (state["peak_equity_eur"] - equity) / state["peak_equity_eur"]
        if drawdown >= HALT_DRAWDOWN:
            state["halted_new_entries"] = True
            state["pending"].clear()
        state["daily_equity"].append({
            "day": day.isoformat(), "equity_eur": round(equity, 2),
            "drawdown_pct": round(drawdown * 100, 2),
        })

        # Trailing stop uses only data completed by this date.
        for symbol, bar in sorted(active.items()):
            bars = [b for b in data[symbol] if b.day <= day]
            p = state["positions"].get(symbol)
            if p is not None:
                atr = _atr(bars)
                if atr > 0:
                    p["stop_eur"] = _money(max(p["stop_eur"], bar.close - 2 * atr))
            elif not state["halted_new_entries"] and symbol not in stopped_today:
                signal = evaluate_signal([b.close for b in bars],
                                         [b.high for b in bars],
                                         [b.low for b in bars],
                                         equity=equity,
                                         peak_equity=state["peak_equity_eur"])
                if signal["action"] == "BUY":
                    atr = _atr(bars)
                    if atr > 0:
                        state["pending"][symbol] = {
                            "signal_day": day.isoformat(), "atr": atr,
                        }
        state["last_processed_day"] = day.isoformat()
    _check_state(state, set(data))
    return state


def _event(state: dict, day: date, symbol: str, side: str, qty: float,
           price: float, fee: float, reason: str) -> None:
    state["events"].append({
        "day": day.isoformat(), "symbol": symbol, "side": side, "reason": reason,
        "quantity": qty, "price_eur": _money(price),
        "fee_eur": _money(fee),
    })


def _sell(state: dict, symbol: str, price: float, market: str,
          day: date, reason: str) -> None:
    p = state["positions"].pop(symbol)
    fee_bps, slip_bps = PAPER_COST_BPS[market]
    fill = max(0.0, price * (1 - slip_bps / 10000))
    gross = fill * p["quantity"]
    fee = gross * fee_bps / 10000
    state["cash_eur"] = _money(state["cash_eur"] + gross - fee)
    state["fees_eur"] = _money(state["fees_eur"] + fee)
    _event(state, day, symbol, "SELL", p["quantity"], fill, fee, reason)


def public_paper_summary(state: dict, *, status: str = "ACTIVE",
                         reason: str = "") -> dict:
    """Return non-sensitive, read-only view; no broker balances anywhere."""
    equity = _equity(state)
    dd = (state["peak_equity_eur"] - equity) / state["peak_equity_eur"] * 100
    return {
        "status": status,
        "reason": reason,
        "mode": "DELAYED_FORWARD_PAPER",
        "started_on": state["started_on"],
        "last_processed_day": state["last_processed_day"],
        "initial_eur": state["initial_eur"],
        "cash_eur": round(state["cash_eur"], 2),
        "equity_eur": round(equity, 2),
        "pnl_eur": round(equity - state["initial_eur"], 2),
        "return_pct": round(100 * (equity / state["initial_eur"] - 1), 2),
        "drawdown_pct": round(dd, 2),
        "halted_new_entries": state["halted_new_entries"],
        "fees_eur": round(state["fees_eur"], 2),
        "positions": [
            {"symbol": symbol, **p,
             "last_close_eur": state["last_closes_eur"][symbol],
             "market_value_eur": round(p["quantity"] *
                                        state["last_closes_eur"][symbol], 2),
             "price_day": state["last_price_days"][symbol]}
            for symbol, p in sorted(state["positions"].items())
        ],
        "pending": [
            {"symbol": symbol, "signal_day": p["signal_day"]}
            for symbol, p in sorted(state["pending"].items())
        ],
        "events": state["events"][-80:][::-1],
        "equity_history": state["daily_equity"][-160:],
    }
