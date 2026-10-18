"""Trading 212 Invest DEMO metadata discovery, READ-ONLY and private by default.

Official endpoint returns the entire accessible catalog and has a 50 second
rate limit. This code never publishes the returned licensed metadata and
never sends orders. Account approval + secrets required to fetch it.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

DEMO_CATALOG_URL = "https://demo.trading212.com/api/v0/equity/metadata/instruments"
VALID_TYPES = frozenset({"STOCK", "ETF"})


class UniverseUnavailable(RuntimeError):
    pass


def load_demo_universe(*, api_key: str | None = None,
                       api_secret: str | None = None) -> list[dict]:
    """One authenticated GET (never live), no keys in logs or exception text."""
    key = api_key if api_key is not None else os.getenv("TRADING212_DEMO_KEY", "")
    secret = api_secret if api_secret is not None else os.getenv(
        "TRADING212_DEMO_SECRET", ""
    )
    if not key or not secret:
        raise UniverseUnavailable("Trading 212 DEMO API credentials not configured")
    basic = base64.b64encode((key + ":" + secret).encode()).decode()
    request = urllib.request.Request(
        DEMO_CATALOG_URL, method="GET",
        headers={"Authorization": "Basic " + basic, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            raw = response.read(12_000_001)
            if len(raw) > 12_000_000:
                raise UniverseUnavailable("Metadata response exceeds 12 MB")
        records = json.loads(raw)
    except urllib.error.HTTPError as exc:
        # Do not print HTTP body, request URL, Authorization or tracebacks.
        # 403 can be entitlement or a provider CDN/IP policy; cannot
        # distinguish those reliably from status alone.
        status = int(exc.code)
        categories = {
            400: "BAD_REQUEST",
            401: "AUTHENTICATION_REJECTED",
            403: "FORBIDDEN_OR_PROVIDER_ACCESS_BLOCK",
            408: "REQUEST_TIMEOUT",
            429: "RATE_LIMIT_RETRY_LATER",
        }
        label = categories.get(status, "REMOTE_HTTP_ERROR")
        raise UniverseUnavailable(
            f"Trading 212 DEMO metadata HTTP {status} ({label}); no credentials exposed"
        ) from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise UniverseUnavailable(
            "Trading 212 DEMO metadata NETWORK_ERROR; no credentials exposed"
        ) from None
    except (ValueError, UnicodeError) as exc:
        raise UniverseUnavailable(
            "Trading 212 DEMO metadata response INVALID_JSON; no credentials exposed"
        ) from None
    if not isinstance(records, list):
        raise UniverseUnavailable("Unrecognized Trading 212 metadata response")
    if len(records) > 100_000:
        raise UniverseUnavailable("Unexpectedly large instrument universe")
    clean = []
    for row in records:
        if not isinstance(row, dict):
            continue
        kind = row.get("type")
        if kind not in VALID_TYPES:
            continue
        ticker = row.get("ticker")
        currency = row.get("currencyCode")
        if (not isinstance(ticker, str) or not ticker.strip()
                or not isinstance(currency, str) or len(currency) != 3):
            continue
        clean.append({
            "ticker": ticker,
            "shortName": row.get("shortName"),
            "type": kind,
            "currencyCode": currency.upper(),
            "isin": row.get("isin"),
            "addedOn": row.get("addedOn"),
            "maxOpenQuantity": row.get("maxOpenQuantity"),
            "workingScheduleId": row.get("workingScheduleId"),
        })
    return clean


def _added_date(item: dict):
    value = item.get("addedOn")
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc).date()
    except ValueError:
        return None


def summarize_universe(items: list[dict], *, as_of=None) -> dict:
    """Counts only; no licensed instrument dump, no unverified quotes."""
    as_of = as_of or datetime.now(timezone.utc).date()
    tickers = {i["ticker"] for i in items if i.get("type") in VALID_TYPES
               and isinstance(i.get("ticker"), str)}
    stocks = [i for i in items if i.get("type") == "STOCK"]
    etfs = [i for i in items if i.get("type") == "ETF"]
    added = [i for i in items
             if (d := _added_date(i)) and timedelta(0) <=
             (as_of-d) <= timedelta(days=30)]
    return {
        "mode": "METADATA_COUNTS_ONLY",
        "source": "Trading 212 DEMO authenticated metadata endpoint",
        "as_of": as_of.isoformat(),
        "stock_instruments": len(stocks),
        "etf_instruments": len(etfs),
        "unique_tickers": len(tickers),
        "unique_isins": len({i.get("isin") for i in items if i.get("isin")}),
        "currencies": dict(sorted(Counter(
            i.get("currencyCode") for i in items if i.get("type") in VALID_TYPES
        ).items())),
        "platform_additions_30d": len(added),
        "ipo_discovered": None,
        "price_data_available": False,
        "fundamentals_available": False,
        "warning": (
            "Trading 212 addedOn means added to platform, NOT an exchange IPO. "
            "Metadata has no daily OHLC, verified volume or SEC fundamentals. "
            "Do not infer investor performance or place orders."
        ),
    }


def main():
    """No secrets printed; summary is safe to see in private Actions logs."""
    try:
        data = load_demo_universe()
    except UniverseUnavailable as exc:
        print(json.dumps({"status": "UNAVAILABLE", "reason": str(exc)}))
        return
    print(json.dumps(summarize_universe(data), ensure_ascii=False))


if __name__ == "__main__":
    main()
