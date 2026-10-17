"""Read-only OHLC providers; all returned prices MUST be in EUR.

Stock/ETF CSV: Stooq, may require a personal API key / CAPTCHA.
Crypto: Kraken public daily OHLC, returns at most the recent ~720 bars.
No authentication to exchanges and no order endpoints are used.
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from .portfolio import Bar


USER_AGENT = "SwingBotPrototype/0.2 (research-only)"


class MarketDataError(RuntimeError):
    pass


def _request_text(url: str, *, timeout: int = 25) -> str:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read(6_000_000)
            if len(content) >= 6_000_000:
                raise MarketDataError("Response exceeds 6 MB limit")
            return content.decode("utf-8-sig")
    except (urllib.error.HTTPError, urllib.error.URLError, UnicodeError, TimeoutError) as err:
        raise MarketDataError(f"Data provider unavailable: {type(err).__name__}") from err


def stooq_eur_daily(symbol: str, *, api_key: str | None = None,
                    today: date | None = None) -> list[Bar]:
    """Only use symbols whose EXCHANGE LISTING and quote currency are EUR.

    The provider does not certify currency in the historical CSV. Validate it
    independently before enabling a symbol. Excludes today's daily bar.
    """
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789.")
    ticker = symbol.lower().strip()
    if not ticker or not ticker.endswith(".de") or any(ch not in allowed for ch in ticker):
        raise MarketDataError("Only explicitly EUR-verified .DE listings are allowed")
    key = api_key if api_key is not None else os.getenv("STOOQ_API_KEY", "")
    params = {"s": ticker, "i": "d", "d1": "20230101"}
    if key:
        params["apikey"] = key
    raw = _request_text("https://stooq.com/q/d/l/?" + urllib.parse.urlencode(params))
    if not raw.lstrip().lower().startswith("date,open,high,low,close"):
        raise MarketDataError("Stooq did not return daily CSV; an API key may be required")
    parsed = []
    limit = today or datetime.now(timezone.utc).date()
    for row in csv.DictReader(io.StringIO(raw)):
        try:
            day = date.fromisoformat(row["Date"])
            if day >= limit:
                continue
            parsed.append(Bar(day, float(row["Open"]), float(row["High"]),
                              float(row["Low"]), float(row["Close"])))
        except (ValueError, KeyError, TypeError) as err:
            raise MarketDataError("Bad Stooq OHLC input") from err
    parsed.sort(key=lambda bar: bar.day)
    if len(parsed) < 61:
        raise MarketDataError("Too few completed Stooq daily bars")
    return _dedupe_or_raise(parsed)


def kraken_eur_daily(pair: str, *, today: date | None = None) -> list[Bar]:
    """Download COMPLETED Kraken UTC daily candles, omitting live last candle."""
    allowed = {"XBTEUR", "ETHEUR", "SOLEUR"}
    if pair not in allowed:
        raise MarketDataError(f"Unsupported EUR pair: {pair}")
    url = ("https://api.kraken.com/0/public/OHLC?"
           + urllib.parse.urlencode({"pair": pair, "interval": 1440}))
    try:
        payload = json.loads(_request_text(url))
        if payload.get("error") or not payload.get("result"):
            raise MarketDataError("Kraken OHLC returned an API error")
        result = payload["result"]
        pair_keys = [k for k in result if k != "last"]
        if len(pair_keys) != 1:
            raise MarketDataError("Unexpected Kraken OHLC response")
        entries = result[pair_keys[0]]
        # Kraken's last entry is always unfinished, irrespective of its time.
        entries = entries[:-1]
        limit = today or datetime.now(timezone.utc).date()
        bars = [
            Bar(datetime.fromtimestamp(int(r[0]), timezone.utc).date(),
                float(r[1]), float(r[2]), float(r[3]), float(r[4]))
            for r in entries
            if datetime.fromtimestamp(int(r[0]), timezone.utc).date() < limit
        ]
    except (ValueError, KeyError, TypeError, IndexError) as err:
        raise MarketDataError("Bad Kraken OHLC data") from err
    bars.sort(key=lambda bar: bar.day)
    if len(bars) < 61:
        raise MarketDataError("Too few completed Kraken daily bars")
    return _dedupe_or_raise(bars)


def _dedupe_or_raise(bars: list[Bar]) -> list[Bar]:
    if any(a.day >= b.day for a, b in zip(bars, bars[1:])):
        raise MarketDataError("Price provider returned duplicate or unordered dates")
    return bars
