"""Public, read-only Bitvavo EUR OHLC feed.

No API keys. No trade endpoints. No credentials.
Bitvavo candle data is returned newest-first; the current UTC day is omitted.
"""
from __future__ import annotations

import json
import urllib.parse
from datetime import date, datetime, timezone

from .market_data import MarketDataError, _dedupe_or_raise, _request_text
from .portfolio import Bar

PAIRS = frozenset({"BTC-EUR", "ETH-EUR", "SOL-EUR"})


def bitvavo_eur_daily(pair: str, *, today: date | None = None) -> list[Bar]:
    if pair not in PAIRS:
        raise MarketDataError("Only approved EUR markets are supported")
    url = "https://api.bitvavo.com/v2/" + pair + "/candles?" + urllib.parse.urlencode({
        "interval": "1d",
        "limit": 720,
    })
    try:
        rows = json.loads(_request_text(url))
        if not isinstance(rows, list):
            raise MarketDataError("Bitvavo returned an invalid candle payload")
        cutoff = today or datetime.now(timezone.utc).date()
        bars = [
            Bar(
                datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc).date(),
                float(row[1]), float(row[2]), float(row[3]), float(row[4])
            )
            for row in rows
            if datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc).date() < cutoff
        ]
        bars.sort(key=lambda bar: bar.day)
    except (TypeError, ValueError, IndexError, OverflowError) as exc:
        raise MarketDataError("Invalid Bitvavo OHLC response") from exc
    if len(bars) < 61:
        raise MarketDataError("Too few completed Bitvavo daily bars")
    return _dedupe_or_raise(bars)
