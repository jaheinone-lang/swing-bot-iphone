"""ECB reference exchange rates via Frankfurter v2, not tradeable FX quotes.

Records are point-in-time published reference rates, not bid/ask conversion
prices. Strictly refuse FX rates dated after the equity close being converted.
Never return a current exchange rate for historical observations.
"""
from __future__ import annotations

import json
from datetime import date
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://api.frankfurter.dev/v2/providers/ecb/rate/eur/"
CURRENCIES = frozenset({"USD", "GBP", "CHF", "NOK", "SEK", "DKK"})


class FxUnavailable(ValueError):
    pass


def parse_ecb_rate(payload: dict, *, expected_quote: str,
                   trading_day: date, max_staleness_days: int = 5) -> dict:
    """Validate ECB spot reference date <= signal day, <=5 days old."""
    if not isinstance(payload, dict):
        raise FxUnavailable("Unexpected ECB FX response")
    if payload.get("base", "").upper() != "EUR":
        raise FxUnavailable("FX rate is not EUR based")
    if payload.get("quote", "").upper() != expected_quote:
        raise FxUnavailable("Wrong quote currency")
    try:
        published = date.fromisoformat(payload["date"])
        rate = float(payload["rate"])
    except (ValueError, TypeError, KeyError) as exc:
        raise FxUnavailable("Invalid reference FX rate") from exc
    age = (trading_day-published).days
    if age < 0 or age > max_staleness_days or not isfinite(rate) or rate <= 0:
        raise FxUnavailable("Future, stale or invalid reference FX data")
    return {"date":published.isoformat(), "rate_quote_per_eur":rate,
            "base":"EUR", "quote":expected_quote,
            "source":"ECB via Frankfurter v2", "age_days":age}


def eur_value(quote_amount: float, record: dict) -> float:
    """Quote-currency amount / (quote per EUR) = EUR amount."""
    rate = float(record["rate_quote_per_eur"])
    if not isfinite(quote_amount) or not isfinite(rate) or rate <= 0:
        raise FxUnavailable("Invalid FX conversion")
    return quote_amount/rate


def ecb_rate_for_day(currency: str, trading_day: date) -> dict:
    """Optional network source: no keys and no write endpoints.

    Requests that fall on non-ECB-business days may not have a quote.
    Fail rather than use a future rate. Historical backfills need caching.
    """
    currency=currency.upper()
    if currency not in CURRENCIES:
        raise FxUnavailable("Unsupported ECB quoted currency")
    # Frankfurter v2 single-rate query returns a record from selected date;
    # still verify published date because weekends and holidays can differ.
    url=ENDPOINT+currency.lower()+"?date="+trading_day.isoformat()
    req=Request(url, headers={"User-Agent":"SwingBotResearch/0.5",
                              "Accept":"application/json"})
    try:
        with urlopen(req,timeout=14) as response:
            raw=response.read(100_001)
        if len(raw)>100_000:
            raise FxUnavailable("Oversized ECB response")
        payload=json.loads(raw)
    except (HTTPError,URLError,TimeoutError,UnicodeError,ValueError) as exc:
        raise FxUnavailable("ECB reference rate not available") from exc
    return parse_ecb_rate(payload,expected_quote=currency,trading_day=trading_day)
