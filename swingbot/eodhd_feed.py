"""Optional historical end-of-day stock and ETF data source (EODHD).

This adapter validates raw native-currency OHLCV. It does NOT assert a
security's trading currency or that dividends/splits are fully adjusted.
Nothing here authorizes entries in the EUR paper portfolio. The provider
requires a separate token and a license covering the intended usage.

Secrets stay in EODHD_API_TOKEN; never publish query URLs or responses.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite

from .equity_screen import DailyBar


class EodhdUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class EodhdFeed:
    ticker: str
    quote_currency: str
    completed: tuple[DailyBar, ...]
    adjustment_status: str
    provider: str = "EODHD optional licensed EOD"
    order_ready: bool = False


SYMBOL_RE = re.compile(r"^[A-Z0-9^._-]{2,28}$")


def validate_eodhd_rows(rows: object, *, ticker: str,
                        quote_currency: str, as_of: date,
                        max_stale_days: int = 7) -> EodhdFeed:
    """Returns NON-ADJUSTED research candles. Never assume total return."""
    if not SYMBOL_RE.fullmatch(ticker):
        raise EodhdUnavailable("Invalid exchange ticker identifier")
    if (not re.fullmatch(r"[A-Z]{3}", quote_currency)
            or quote_currency not in {"EUR", "USD", "GBP", "CHF", "NOK", "SEK", "DKK"}):
        raise EodhdUnavailable("Explicit supported quote currency required")
    if not isinstance(rows, list) or len(rows) > 20000:
        raise EodhdUnavailable("Unrecognized or excessive EOD price response")
    bars = []
    for record in rows:
        if not isinstance(record, dict):
            raise EodhdUnavailable("Invalid daily bar")
        try:
            day = date.fromisoformat(record["date"])
            if day >= as_of:  # no same-day still trading or future bars
                continue
            bar = DailyBar(day, float(record["open"]), float(record["high"]),
                           float(record["low"]), float(record["close"]),
                           float(record["volume"]))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise EodhdUnavailable("Malformed EOD OHLCV values") from exc
        bars.append(bar)
    bars.sort(key=lambda x: x.day)
    if len(bars) < 201:
        raise EodhdUnavailable("Need at least 201 completed OHLCV observations")
    if any(a.day >= b.day for a, b in zip(bars, bars[1:])):
        raise EodhdUnavailable("Duplicate or unordered completed EOD dates")
    freshness = (as_of-bars[-1].day).days
    if freshness < 1 or freshness > max_stale_days:
        raise EodhdUnavailable("Historical feed stale or from future")
    return EodhdFeed(ticker, quote_currency, tuple(bars),
                     "RAW_OHLC_NOT_VERIFIED_SPLIT_OR_DIVIDEND_ADJUSTED")


def fetch_eodhd_eod(ticker: str, *, quote_currency: str,
                    as_of: date | None = None, from_day: date | None = None,
                    api_token: str | None = None) -> EodhdFeed:
    """One request per instrument; limit bulk scans to licensed quota.

    Default is DEMO only for provider's approved test symbols, if no private
    key exists. No whole-universe fetching without opt-in/contract.
    """
    token = api_token if api_token is not None else os.getenv("EODHD_API_TOKEN", "")
    if not token:
        raise EodhdUnavailable("EODHD_API_TOKEN not configured")
    if not SYMBOL_RE.fullmatch(ticker):
        raise EodhdUnavailable("Ticker must use EODHD SYMBOL.EXCHANGE format")
    as_of=as_of or datetime.now(timezone.utc).date()
    parameters={"api_token":token,"fmt":"json","period":"d",
                "to":(as_of).isoformat()}
    if from_day:
        parameters["from"]=from_day.isoformat()
    url=("https://eodhd.com/api/eod/"+urllib.parse.quote(ticker)
         +"?"+urllib.parse.urlencode(parameters))
    req=urllib.request.Request(url,headers={
        "User-Agent":"SwingBotPaperResearch/0.6","Accept":"application/json"
    })
    try:
        with urllib.request.urlopen(req,timeout=22) as response:
            raw=response.read(4_000_001)
        if len(raw)>4_000_000:
            raise EodhdUnavailable("EOD daily response too large")
        rows=json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError,
            TimeoutError, ValueError, UnicodeError) as exc:
        # Intentionally discard the exception; the request URL contains token.
        raise EodhdUnavailable("EODHD price feed failed; credentials not logged") from None
    return validate_eodhd_rows(rows,ticker=ticker,quote_currency=quote_currency,
                               as_of=as_of)
