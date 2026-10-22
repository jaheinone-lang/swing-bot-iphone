"""Read-only crypto-only strategy research, NEVER live trading.

Uses historical Bitvavo BTC/ETH/SOL EUR candles and the existing next-open,
stop-aware, tax-reserving swing backtester. Candidates are fixed in advance.
No account API keys, no order submission, no modification of paper state.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta
from unittest.mock import patch

from .bitvavo_data import bitvavo_eur_daily
from .portfolio import COST_BPS
from .research_metrics import _metrics
from .strategy_lab import Spec, research_backtest

SYMBOLS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
MARKETS = {symbol: "crypto" for symbol in SYMBOLS}

# Freeze just three hypotheses: current crypto-only reference and two
# distinct aggressive candidates. Larger size is NOT evidence of edge.
CANDIDATES = (
    Spec("A - existing crypto-only", 20, 50, 2.0, .20, False, None, None),
    Spec("D - aggressive breakout", 10, 30, 2.5, .55, False, 15, 2,
         risk_per_trade=.02),
    Spec("E - filtered momentum", 15, 50, 3.0, .60, True, 30, 2,
         risk_per_trade=.02),
)


def aligned_crypto_data(raw: dict) -> dict:
    """Require the SAME continuous observed days; never forward-fill gaps."""
    if set(raw) != set(SYMBOLS):
        raise ValueError("BTC-EUR, ETH-EUR and SOL-EUR all required")
    dates = [set(b.day for b in raw[sym]) for sym in SYMBOLS]
    common = set.intersection(*dates)
    if len(common) < 300:
        raise ValueError("Fewer than 300 common completed daily candles")
    calendar = sorted(common)
    if any(b != a + timedelta(days=1) for a, b in zip(calendar, calendar[1:])):
        raise ValueError("Missing daily candle in common research window")
    start, end = calendar[0], calendar[-1]
    aligned = {}
    for sym in SYMBOLS:
        series = [b for b in raw[sym] if start <= b.day <= end]
        if len(series) != len(calendar) or [b.day for b in series] != calendar:
            raise ValueError("Missing, unsorted or duplicate candle for " + sym)
        aligned[sym] = series
    return aligned


def analyse(data: dict, *, initial_eur: float = 5000.0) -> dict:
    """Chronological selection ONLY on training; report later slice honestly."""
    aligned = aligned_crypto_data(data)
    calendar = [bar.day for bar in aligned[SYMBOLS[0]]]
    split = calendar[int(len(calendar) * .65)].isoformat()
    rows = []
    for spec in CANDIDATES:
        normal = research_backtest(aligned, MARKETS, spec, starting_eur=initial_eur)
        curve = normal["daily_curve"]
        dev = [row for row in curve if row["day"] <= split]
        later = [row for row in curve if row["day"] >= split]
        train = _metrics(dev)
        validation = _metrics(later)
        # Stress both exchange taker fee and slippage: normal 25+15bps
        # per direction, 2x stress 50+30bps. Never assume maker fill.
        with patch.dict(COST_BPS, {"crypto": (50.0, 30.0)}):
            stressed = research_backtest(aligned, MARKETS, spec,
                                         starting_eur=initial_eur)
        rows.append({
            "name": spec.name,
            "spec": asdict(spec),
            "development": train,
            "later_period": validation,
            "training_score": round(
                train["total_return_pct"] - 1.5 * train["max_drawdown_pct"], 4
            ),
            "full_period_after_tax_eur": normal["after_tax_equity_eur"],
            "full_period_after_tax": normal["stats_after_tax"],
            "fee_stress_after_tax_eur": stressed["after_tax_equity_eur"],
            "estimated_fees_eur": normal["estimated_fees_eur"],
            "trade_events": len(normal["trade_events"]),
            "halted": normal["halted"],
        })
    selected = max(rows, key=lambda row: (row["training_score"], row["name"]))
    return {
        "mode": "RESEARCH_ONLY_NO_ORDERS",
        "instruments": list(SYMBOLS),
        "start": calendar[0].isoformat(),
        "end": calendar[-1].isoformat(),
        "calendar_days": len(calendar),
        "split_day": split,
        "selection_uses": "training only: total return - 1.5 x max drawdown",
        "winner_on_training": selected["name"],
        "later_result_of_selected": selected["later_period"],
        "candidates": rows,
        "costs": "normal 25bps taker + 15bps slippage EACH side; stress 2x",
        "tax": "simplified Finnish personal realized-gains reserve",
        "disclaimer": (
            "Historical research is not independently verified future performance; "
            "the strategy concepts were informed by known market history. "
            "Only 3 crypto pairs and about 2 years of candles. "
            "Daily OHLC bars cannot prove real-world fills, stops or 25% cap. "
            "No margin, no shorting, no API orders, no real funds."
        ),
    }


def main() -> None:
    # Deliberately read-only: no credentials or trading account API.
    raw = {sym: bitvavo_eur_daily(sym) for sym in SYMBOLS}
    print(json.dumps(analyse(raw), ensure_ascii=False, indent=2,
                     allow_nan=False))


if __name__ == "__main__":
    main()
