"""Dual-market demonstration/backtest CLI.

python -m swingbot.multi_cli --mode demo
python -m swingbot.multi_cli --mode live  # needs accessible Stooq API data
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from .market_data import MarketDataError, kraken_eur_daily, stooq_eur_daily
from .portfolio import Bar, backtest


def synthetic_dataset():
    """Fabricated EUR data, only for repeatable code tests, NOT forecasts."""
    start = date(2025, 1, 1)
    stock, crypto = [], []
    for day_index in range(240):
        d = start + timedelta(days=day_index)
        if d.weekday() < 5:
            # Periodic breakouts exercise the trading code.
            c = 110 + 0.11 * day_index + (5 if day_index % 47 > 39 else 0)
            stock.append(Bar(d, c - 0.6, c + 2, c - 2, c))
        c = 60000 + 60 * day_index + (2200 if day_index % 37 > 30 else 0)
        crypto.append(Bar(d, c - 80, c + 800, c - 800, c))
    return {"DEMO_EUR_STOCK": stock, "DEMO_BTCEUR": crypto}, {
        "DEMO_EUR_STOCK": "stock", "DEMO_BTCEUR": "crypto"
    }


def live_dataset():
    """EUR instruments only. Do not silently use synthetic fallback."""
    data = {
        "SAP.DE": stooq_eur_daily("sap.de"),
        "XBTEUR": kraken_eur_daily("XBTEUR"),
        "ETHEUR": kraken_eur_daily("ETHEUR"),
    }
    # Restrict all assets to a common history window to avoid biased comparison
    # caused by one feed having a much longer historical period.
    start = max(bars[0].day for bars in data.values())
    end = min(bars[-1].day for bars in data.values())
    data = {key: [bar for bar in bars if start <= bar.day <= end]
            for key, bars in data.items()}
    if any(len(bars) < 61 for bars in data.values()):
        raise MarketDataError("Insufficient overlapping market history")
    return data, {"SAP.DE": "stock", "XBTEUR": "crypto", "ETHEUR": "crypto"}


def main():
    parser = argparse.ArgumentParser(
        description="Backtest-only combined equity and crypto strategy, NO real orders"
    )
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--initial-eur", type=float, default=5000.0)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    try:
        data, markets = synthetic_dataset() if args.mode == "demo" else live_dataset()
        report = backtest(data, markets, initial_eur=args.initial_eur)
    except (MarketDataError, ValueError) as err:
        parser.exit(2, f"Backtest could not run: {err}\n")
    report["data_mode"] = (
        "SYNTHETIC_PRICES_NOT_REAL" if args.mode == "demo"
        else "HISTORICAL_PROVIDER_PRICES_NOT_LIVE_TRADING"
    )
    if args.summary_only:
        report.pop("daily_curve")
        report.pop("trade_events")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
