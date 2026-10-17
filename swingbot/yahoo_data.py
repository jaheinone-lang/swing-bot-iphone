"""UNOFFICIAL Yahoo Finance daily OHLC research adapter.

Yahoo's chart endpoint has no documented SLA. Do not use this feed to
send real orders. Fails closed if currency is not EUR or history is stale.
"""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from .market_data import MarketDataError, _dedupe_or_raise
from .portfolio import Bar

ALLOWED = frozenset({"SAP.DE"})  # independently verify venue and EUR currency
CHART_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
STOCK_EXCHANGE_ZONE = ZoneInfo("Europe/Berlin")


def _yahoo_json(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SwingBotResearch/0.3)",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=14) as response:
            raw = response.read(3_000_000)
            if len(raw) >= 3_000_000:
                raise MarketDataError("Yahoo chart response too large")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Not an object")
        return payload
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            ValueError, UnicodeError) as exc:
        raise MarketDataError("Yahoo historical EUR prices unavailable") from exc


def yahoo_eur_daily(symbol: str, *, today: date | None = None) -> list[Bar]:
    symbol = symbol.upper().strip()
    if symbol not in ALLOWED:
        raise MarketDataError("Symbol not approved for EUR history")
    # Daily bars reported by Yahoo can include the current incomplete session.
    # We exclude the present day even if it is currently after stock-market close.
    cutoff = today or datetime.now(STOCK_EXCHANGE_ZONE).date()
    query = urllib.parse.urlencode({
        "range": "2y", "interval": "1d", "events": "false",
        "includeAdjustedClose": "false",
    })
    last_error = None
    for host in CHART_HOSTS:
        url = f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol)}?{query}"
        try:
            payload = _yahoo_json(url)
            chart = payload["chart"]
            if chart.get("error"):
                raise MarketDataError("Yahoo chart signalled an error")
            results = chart.get("result")
            if not isinstance(results, list) or len(results) != 1:
                raise MarketDataError("Unexpected Yahoo chart shape")
            result = results[0]
            metadata = result.get("meta", {})
            if metadata.get("currency") != "EUR":
                raise MarketDataError("Yahoo listing is NOT EUR quoted")
            if metadata.get("symbol", "").upper() != symbol:
                raise MarketDataError("Wrong Yahoo symbol returned")
            quotes = result["indicators"]["quote"][0]
            stamps = result["timestamp"]
            if not stamps or any(len(quotes.get(field, [])) != len(stamps)
                                 for field in ("open", "high", "low", "close")):
                raise MarketDataError("Broken Yahoo candle arrays")
            bars = []
            for idx, epoch in enumerate(stamps):
                day = datetime.fromtimestamp(int(epoch), STOCK_EXCHANGE_ZONE).date()
                if day >= cutoff:
                    continue
                values = [quotes[field][idx] for field in
                          ("open", "high", "low", "close")]
                if any(v is None or not isinstance(v, (float, int))
                       or not math.isfinite(v) for v in values):
                    continue
                bars.append(Bar(day, *(float(v) for v in values)))
            bars.sort(key=lambda b: b.day)
            bars = _dedupe_or_raise(bars)
            if len(bars) < 61:
                raise MarketDataError("Insufficient completed stock daily candles")
            if (cutoff - bars[-1].day).days > 7:
                raise MarketDataError("Stale Yahoo stock data")
            return bars
        except (MarketDataError, KeyError, TypeError, ValueError, IndexError) as exc:
            last_error = exc
            continue
    raise MarketDataError(
        "EUR stock feed unavailable from both Yahoo chart endpoints"
    ) from last_error
