"""Private EU EODHD EOD + split-event validator (no trading or price publishing).

EODHD documents that default OHLC are unadjusted, adjusted_close adds BOTH
splits and cash dividends, and volume is already split-adjusted. We use
raw OHLC divided by the cumulative factor for FUTURE split ex-dates.
Never use adjusted_close as OHLC, never split-adjust volume a second time.

No result automatically proves listing venue, issuer ISIN, Trading 212 exact
instrument match, redistribution rights or personal non-display permission.
Those are separate gates in EUHistory. No network in this module other than
explicit read-only EODHD split downloads called by a user-approved job.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from math import isfinite

from .eodhd_feed import EodhdFeed, EodhdUnavailable
from .equity_screen import DailyBar
from .eu_swing_lab import EUHistory, VERIFIED
from .eu_watchlist import EU_BY_SYMBOL


def parse_split_events(rows: object, *, first_day: date, as_of: date
                       ) -> tuple[tuple[date, float], ...]:
    """EODHD's "new/old" split ratios, ex-date relative to raw OHLC."""
    if not isinstance(rows, list) or len(rows) > 1000:
        raise EodhdUnavailable("Invalid EU split-event response")
    events = []
    for row in rows:
        if not isinstance(row, dict):
            raise EodhdUnavailable("Malformed split event")
        try:
            day = date.fromisoformat(row["date"])
            ratio = row["split"]
            if not isinstance(ratio, str) or not re.fullmatch(
                r"[0-9]+(?:\.[0-9]+)?/[0-9]+(?:\.[0-9]+)?", ratio
            ):
                raise ValueError("Not an EODHD new/old ratio")
            new, old = (float(z) for z in ratio.split("/"))
            factor = new / old
        except (KeyError, ValueError, TypeError, ZeroDivisionError, OverflowError):
            raise EodhdUnavailable("Unusable EU split ratio") from None
        if (not 0 < new < 1_000_000_000 or
                not 0 < old < 1_000_000_000 or
                not isfinite(factor) or not 0 < factor < 100_000 or
                not first_day <= day < as_of):
            raise EodhdUnavailable("Split date or factor out of bounds")
        events.append((day, factor))
    events.sort()
    if any(a[0] == b[0] for a, b in zip(events, events[1:])):
        raise EodhdUnavailable("Duplicate split ex-date")
    return tuple(events)


def split_adjusted_eur_history(
    raw: EodhdFeed, split_rows: object, *,
    as_of: date, research_symbol: str, exact_eodhd_venue_verified: bool,
    broker_isin_and_listing_verified: bool,
    personal_non_display_rights_verified: bool,
) -> EUHistory:
    """Build split-only OHLCV; fail closed on any missing prerequisite.

    These three permissions are independently verified assertions by the
    caller, NOT inferred from a successful EODHD HTTP 200 response.
    """
    listing = EU_BY_SYMBOL.get(research_symbol)
    if listing is None or listing.currency != "EUR":
        raise EodhdUnavailable("EU research symbol not EUR quoted")
    if (not isinstance(raw, EodhdFeed) or raw.quote_currency != "EUR"
            or not isinstance(as_of, date) or
            not raw.ticker or not raw.ticker.endswith(".XETRA")
            and not raw.ticker.endswith((".PA", ".AS", ".MC", ".MI", ".BR"))):
        raise EodhdUnavailable("Unverified native EUR source")
    if (not exact_eodhd_venue_verified or not broker_isin_and_listing_verified
            or not personal_non_display_rights_verified):
        raise PermissionError("EU listing/broker identity/data usage not approved")
    # Convert only from the *raw* vendor feed, never from already adjusted data.
    if raw.adjustment_status != "RAW_OHLC_NOT_VERIFIED_SPLIT_OR_DIVIDEND_ADJUSTED":
        raise EodhdUnavailable("Unexpected EU OHLC price adjustment status")
    bars = raw.completed
    if (len(bars) < 201 or
            any(a.day >= b.day for a, b in zip(bars, bars[1:])) or
            not 1 <= (as_of - bars[-1].day).days <= 7):
        raise EodhdUnavailable("Insufficient, stale or duplicate EU history")
    events = parse_split_events(split_rows, first_day=bars[0].day, as_of=as_of)
    # Every earlier date must reflect all split ex-dates strictly AFTER it.
    by_day_desc = list(reversed(events))
    pos = 0
    factor = 1.0
    result = []
    for bar in reversed(bars):
        while pos < len(by_day_desc) and by_day_desc[pos][0] > bar.day:
            factor *= by_day_desc[pos][1]
            if not isfinite(factor) or not 1e-8 < factor < 1e8:
                raise EodhdUnavailable("Cumulative split adjustment out of range")
            pos += 1
        try:
            adjusted = DailyBar(
                bar.day, bar.open/factor, bar.high/factor,
                bar.low/factor, bar.close/factor,
                bar.volume,  # vendor volume is ALREADY split-adjusted
            )
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            raise EodhdUnavailable("Invalid split-adjusted EU OHLCV") from None
        result.append(adjusted)
    result.reverse()
    return EUHistory(
        symbol=research_symbol, currency="EUR", bars=tuple(result),
        source=VERIFIED, exchange_verified=True,
        exact_broker_instrument_verified=True,
        split_adjustment_verified=True,
        personal_non_display_rights_verified=True,
    )


EODHD_BASE = "https://eodhd.com/api/splits/"
EODHD_SYMBOL = re.compile(r"^[A-Z0-9_-]{1,20}\.[A-Z]{2,12}$")


def fetch_eodhd_splits(*, provider_symbol: str, first_day: date,
                       as_of: date, api_token: str | None = None,
                       urlopen=urllib.request.urlopen) -> list[dict]:
    """Read-only, bounded request. NEVER include token/URL in exceptions/logs."""
    key = (api_token if api_token is not None else
           os.environ.get("EODHD_API_TOKEN", "")).strip()
    if not key:
        raise EodhdUnavailable("EU EODHD credential not configured")
    if not EODHD_SYMBOL.fullmatch(provider_symbol):
        raise EodhdUnavailable("Invalid EODHD exchange-qualified symbol")
    if not first_day < as_of:
        raise EodhdUnavailable("Invalid split historical date window")
    url = (EODHD_BASE + urllib.parse.quote(provider_symbol)
           + "?" + urllib.parse.urlencode({
               "api_token": key, "fmt": "json",
               "from": first_day.isoformat(),
               "to": (as_of-timedelta(days=1)).isoformat()
           }))
    req = urllib.request.Request(url, method="GET", headers={
        "Accept": "application/json",
        "User-Agent": "SwingBotPersonalEUResearch/0.1",
    })
    try:
        with urlopen(req, timeout=25) as response:
            blob = response.read(400_001)
        if len(blob) > 400_000:
            raise EodhdUnavailable("Unexpectedly large EU split response")
        data = json.loads(blob)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            ValueError, UnicodeError, OSError):
        # No exception chaining: EODHD uses query-string API credentials.
        raise EodhdUnavailable("EU split provider request unavailable") from None
    if not isinstance(data, list):
        raise EodhdUnavailable("Split response not a validated event list")
    return data
