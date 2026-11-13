"""Independent forward-only, DELAYED paper trading for frozen strategy E.

NO broker APIs, funds, or credentials. Actual future daily closes are recorded,
then hypothetical next-open fills are booked only once that next daily candle
has completed. This is not executable forward paper trading.
Never touches paper/state.json or the existing combined stock/crypto ledger.
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta, timezone
from math import floor, isfinite
from pathlib import Path
from typing import Mapping, Sequence

from .bitvavo_data import bitvavo_eur_daily
from .crypto_alpha_research import CANDIDATES, SYMBOLS
from .crypto_validation import WARMUP_BARS
from .fi_tax_estimate import annual_tax_schedule
from .portfolio import Bar, COST_BPS, _atr
from .strategy_lab import _signal

MODE = "DELAYED_CRYPTO_E_SHADOW_V1"
CFG = CANDIDATES[2]
STARTING_EUR = 5000.0
TOTAL_STOP_RISK = 0.03
HALT_DRAWDOWN = 0.25
MAX_CATCHUP_DAYS = 7
if CFG.name != "E - filtered momentum" or CFG.risk_per_trade != .02:
    raise RuntimeError("Frozen crypto paper research strategy was changed")


def _e(state: dict) -> float:
    return (state["cash_eur"] +
            sum(p["qty"] * state["last_closes_eur"][s]
                for s, p in state["positions"].items()) -
            state["tax_reserved_eur"])


def _validate(data: Mapping[str, Sequence[Bar]], today: date) -> list[date]:
    if set(data) != set(SYMBOLS):
        raise ValueError("All three frozen BTC/ETH/SOL symbols required")
    final = {sym: bars[-1].day for sym, bars in data.items() if bars}
    if len(final) != len(SYMBOLS) or len(set(final.values())) != 1:
        raise ValueError("Missing or desynchronized crypto market feeds")
    as_of = next(iter(final.values()))
    if not 1 <= (today - as_of).days <= 3:
        raise ValueError("Missing, future or stale completed market candle")
    days = [b.day for b in data[SYMBOLS[0]]]
    if len(days) < WARMUP_BARS + 2:
        raise ValueError("Not enough indicator history to start new paper account")
    for sym in SYMBOLS:
        bars = data[sym]
        if [b.day for b in bars] != days:
            raise ValueError("History dates differ or contain gaps")
    if any(b != a + timedelta(days=1) for a, b in zip(days, days[1:])):
        raise ValueError("Missing, duplicate or unordered crypto candle")
    return days


def _check_state(state: dict) -> None:
    if state.get("schema_version") != 1 or state.get("mode") != MODE:
        raise ValueError("Unknown immutable shadow state format")
    if state.get("starting_eur") != STARTING_EUR:
        raise ValueError("Unexpected account starting equity")
    if state.get("strategy") != CFG.name:
        raise ValueError("Frozen strategy state differs")
    if set(state.get("last_closes_eur", {})) != set(SYMBOLS):
        raise ValueError("Shadow symbols changed")
    if not set(state.get("positions", {})).issubset(SYMBOLS):
        raise ValueError("Corrupted positions")
    if not set(state.get("pending_entries", {})).issubset(SYMBOLS):
        raise ValueError("Corrupted pending entries")
    if not set(state.get("pending_exits", [])).issubset(SYMBOLS):
        raise ValueError("Corrupted pending exits")
    if not (isfinite(state["cash_eur"]) and state["cash_eur"] >= -0.000001
            and isfinite(state["peak_equity_eur"]) and state["peak_equity_eur"] > 0
            and isfinite(state["tax_reserved_eur"]) and state["tax_reserved_eur"] >= 0
            and isfinite(_e(state)) and _e(state) > 0):
        raise ValueError("Corrupt paper ledger values")


def initialize(data: Mapping[str, Sequence[Bar]], today: date) -> dict:
    _validate(data, today)
    last = data[SYMBOLS[0]][-1].day.isoformat()
    state = {
        "schema_version": 1, "mode": MODE, "strategy": CFG.name,
        "started_on": last, "last_processed_day": last,
        "starting_eur": STARTING_EUR, "cash_eur": STARTING_EUR,
        "tax_reserved_eur": 0.0, "peak_equity_eur": STARTING_EUR,
        "last_closes_eur": {s: data[s][-1].close for s in SYMBOLS},
        "positions": {}, "pending_entries": {}, "pending_exits": [],
        "disposals": [], "trades": [], "fees_eur": 0.0,
        "halted": False, "equity_curve": [
            {"day": last, "equity_eur": STARTING_EUR, "drawdown_pct": 0.0}
        ],
    }
    _check_state(state)
    return state


def _sell(st: dict, symbol: str, raw: float, day: date, reason: str) -> None:
    p = st["positions"].pop(symbol)
    fee_bps, slip_bps = COST_BPS["crypto"]
    price = max(0.0, raw * (1 - slip_bps / 10000))
    proceeds = price * p["qty"]
    fee = proceeds * fee_bps / 10000
    realized = proceeds - fee - p["basis"]
    st["cash_eur"] += proceeds - fee
    st["fees_eur"] += fee
    st["disposals"].append({"year": day.year, "gain_eur": realized})
    st["tax_reserved_eur"] = annual_tax_schedule(st["disposals"])[
        "total_estimated_tax_eur"
    ]
    st["trades"].append({"day": day.isoformat(), "symbol": symbol,
                         "side": "SELL", "price": round(price, 6),
                         "qty": p["qty"], "reason": reason,
                         "realized_eur": round(realized, 4)})


def advance_shadow(data: Mapping[str, Sequence[Bar]], previous: dict | None,
                   *, as_of: date | None = None) -> dict:
    """Apply completed future daily bars, never retroactively invent trades.

    Caller atomically persists returned state only if all checks pass.
    """
    today = as_of or datetime.now(timezone.utc).date()
    days = _validate(data, today)
    if previous is None:
        return initialize(data, today)
    st = copy.deepcopy(previous)
    _check_state(st)
    last_day = date.fromisoformat(st["last_processed_day"])
    if days[-1] <= last_day:
        return st
    if (days[-1] - last_day).days > MAX_CATCHUP_DAYS:
        raise ValueError("Forward shadow >7 days behind; manual review required")
    if last_day not in days:
        raise ValueError("Paper history no longer covers last processed day")

    new_days = [day for day in days if day > last_day]
    if new_days[0] != last_day + timedelta(days=1):
        raise ValueError("Forward shadow missing completed daily bar")
    by_day = {
        day: {sym: next(b for b in data[sym] if b.day == day) for sym in SYMBOLS}
        for day in new_days
    }
    histories = {
        sym: [b for b in data[sym] if b.day <= last_day] for sym in SYMBOLS
    }
    for day in new_days:
        today_bars = by_day[day]
        stopped = set()
        # 1. Execute stops and exits from PRIOR completed-day information.
        for sym in SYMBOLS:
            p = st["positions"].get(sym)
            bar = today_bars[sym]
            if p and bar.low <= p["stop"]:
                _sell(st, sym, min(bar.open, p["stop"]), day, "STOP")
                stopped.add(sym)
        for sym in list(st["pending_exits"]):
            if sym in st["positions"] and sym not in stopped:
                _sell(st, sym, today_bars[sym].open, day, "TIME_EXIT")
        st["pending_exits"] = []

        ready = sorted(st["pending_entries"].items(),
                       key=lambda x: (-x[1]["momentum"], x[0]))
        st["pending_entries"] = {}
        if not st["halted"]:
            for sym, entry in ready[:2]:
                if sym in st["positions"] or sym in stopped:
                    continue
                if date.fromisoformat(entry["signal_day"]) >= day:
                    raise ValueError("Same-day or future signal invalid")
                bar = today_bars[sym]
                fee_bps, slip_bps = COST_BPS["crypto"]
                price = bar.open * (1 + slip_bps / 10000)
                dist = CFG.stop_atr * entry["atr"]
                if dist <= 0 or price <= dist:
                    continue
                equity = _e(st)
                exposed = sum(
                    p["qty"] * max(0.0, p["entry"] - p["stop"])
                    for p in st["positions"].values()
                )
                remaining_risk = max(0.0, TOTAL_STOP_RISK*equity - exposed)
                free_cash = max(0.0, st["cash_eur"] - st["tax_reserved_eur"])
                qty = floor(max(0.0, min(
                    free_cash / (price * (1 + fee_bps/10000)),
                    equity * CFG.max_position / price,
                    equity * CFG.risk_per_trade / dist,
                    remaining_risk / dist,
                )) * 1e8 + 1e-10) / 1e8
                if qty <= 0:
                    continue
                fee = qty * price * fee_bps / 10000
                st["cash_eur"] -= qty*price + fee
                st["fees_eur"] += fee
                st["positions"][sym] = {
                    "qty": qty, "entry": price, "basis": qty*price + fee,
                    "stop": price - dist, "bars": 0,
                }
                st["trades"].append({
                    "day": day.isoformat(), "symbol": sym, "side": "BUY",
                    "price": round(price, 6), "qty": qty,
                    "reason": "PRIOR_CLOSE_SIGNAL",
                })
                # Same-day stop possible, but fill cannot be better than
                # simulated stop (or a gap below).
                if bar.low <= price - dist:
                    _sell(st, sym, min(bar.open, price - dist),
                          day, "SAME_DAY_STOP")
                    stopped.add(sym)

        # 2. Observe completed candles, compute close equity and drawdown.
        for sym in SYMBOLS:
            bar = today_bars[sym]
            histories[sym].append(bar)
            st["last_closes_eur"][sym] = bar.close
        equity = _e(st)
        st["peak_equity_eur"] = max(st["peak_equity_eur"], equity)
        dd = (st["peak_equity_eur"] - equity) / st["peak_equity_eur"]
        if dd >= HALT_DRAWDOWN:
            st["halted"] = True
            st["pending_entries"] = {}
        st["equity_curve"].append({
            "day": day.isoformat(), "equity_eur": round(equity, 6),
            "drawdown_pct": round(dd*100, 4),
        })

        # 3. Tomorrow's stop updates and candidate signals use only TODAY's close.
        candidates = []
        for sym in SYMBOLS:
            hist = histories[sym]
            p = st["positions"].get(sym)
            if p:
                p["bars"] += 1
                atr = _atr(hist)
                if atr > 0:
                    p["stop"] = max(p["stop"], hist[-1].close - CFG.stop_atr*atr)
                if CFG.time_exit_bars and p["bars"] >= CFG.time_exit_bars:
                    if hist[-1].close < p["entry"]*1.02:
                        st["pending_exits"].append(sym)
            elif not st["halted"] and sym not in stopped:
                signal = _signal(hist, CFG)
                if signal:
                    candidates.append((sym, signal))
        if not st["halted"]:
            candidates = sorted(candidates,
                                key=lambda x: (-x[1]["momentum"], x[0]))[:2]
            st["pending_entries"] = {
                s: {"momentum": signal["momentum"], "atr": signal["atr"],
                    "signal_day": day.isoformat()}
                for s, signal in candidates
            }
        st["last_processed_day"] = day.isoformat()
    _check_state(st)
    return st


def run_to_files(state_path: Path = Path("paper/crypto_e_shadow.json"),
                 output_path: Path = Path("docs/crypto_e_shadow_summary.json")) -> dict:
    bars = {sym: bitvavo_eur_daily(sym) for sym in SYMBOLS}
    old = json.loads(state_path.read_text()) if state_path.exists() else None
    st = advance_shadow(bars, old)
    # Neither report nor ledger contains account secrets, only fictional data.
    state_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "mode": st["mode"], "strategy": st["strategy"],
        "started_on": st["started_on"],
        "last_processed_day": st["last_processed_day"],
        "starting_eur": st["starting_eur"],
        "equity_eur": round(_e(st), 2),
        "return_pct": round((_e(st)/STARTING_EUR-1)*100, 2),
        "tax_reserved_eur": round(st["tax_reserved_eur"], 2),
        "fees_eur": round(st["fees_eur"], 2),
        "halted": st["halted"],
        "positions": sorted(st["positions"]),
        "trades_count": len(st["trades"]),
        "recent_equity": st["equity_curve"][-100:],
        "message": "DELAYED simulated forward-only ledger; never real orders.",
    }
    for path, obj in ((state_path, st), (output_path, report)):
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2,
                                  allow_nan=False) + "\n", encoding="utf-8")
        tmp.replace(path)
    return report


def main() -> None:
    print(json.dumps(run_to_files(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
