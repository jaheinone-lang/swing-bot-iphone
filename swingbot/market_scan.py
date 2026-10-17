"""Fetch public EUR candles and print NON-EXECUTABLE swing signals.

Example: python -m swingbot.market_scan --crypto
Exits nonzero if a requested provider fails. No simulated fallback data.
No broker keys and no trade endpoints.
"""
from __future__ import annotations

import argparse
import json

from .bitvavo_data import bitvavo_eur_daily
from .market_data import MarketDataError, stooq_eur_daily
from .strategy import evaluate_signal

CRYPTO = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
STOCKS = ("sap.de",)


def scan(*, crypto: bool = True, stocks: bool = False) -> dict:
    if not crypto and not stocks:
        raise ValueError("Select at least one market")
    result = {
        "mode": "READ_ONLY_MARKET_SCAN",
        "notice": "Signals are research-only, not executable trade orders",
        "signals": [],
    }
    for pair in (CRYPTO if crypto else ()):
        bars = bitvavo_eur_daily(pair)
        info = evaluate_signal(
            [b.close for b in bars], [b.high for b in bars], [b.low for b in bars]
        )
        result["signals"].append({
            "symbol": pair, "market": "crypto", "quote_currency": "EUR",
            "date": bars[-1].day.isoformat(), "bars": len(bars),
            "signal": info["action"], "reason": info["reason"],
            "reference_price_eur": bars[-1].close,
        })
    for ticker in (STOCKS if stocks else ()):
        bars = stooq_eur_daily(ticker)
        info = evaluate_signal(
            [b.close for b in bars], [b.high for b in bars], [b.low for b in bars]
        )
        result["signals"].append({
            "symbol": ticker.upper(), "market": "stock",
            "quote_currency": "EUR (symbol requires independent verification)",
            "date": bars[-1].day.isoformat(), "bars": len(bars),
            "signal": info["action"], "reason": info["reason"],
            "reference_price_eur": bars[-1].close,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="Public EUR candles, read-only")
    parser.add_argument("--crypto", action="store_true", help="Bitvavo EUR pairs")
    parser.add_argument("--stocks", action="store_true",
                        help="SAP.DE: Stooq key and EUR verification may be needed")
    args = parser.parse_args()
    try:
        report = scan(crypto=args.crypto or not args.stocks, stocks=args.stocks)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    except (ValueError, MarketDataError) as exc:
        parser.exit(2, f"Market scan unavailable: {exc}\n")


if __name__ == "__main__":
    main()
