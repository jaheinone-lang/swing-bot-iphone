"""Broad US/European exchange listing discovery, never a trading signal.

Independent inventory layer: supports all provider-returned venues instead of
the old hand-picked 50/50 symbol lists. This is NOT a price-data backtest:
no historical candles, spread, provider rights, ownership crosswalk or broker
tradability is assumed from a listed instrument.

US: authenticated Alpaca PAPER /v2/assets GET (US equities including ETFs).
Europe: EODHD exchange directory + filtered common-stock exchange lists.
Both are metadata-only and confidential. No account positions or order APIs.
Print only aggregates; never publish vendor or broker symbol dumps.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Callable

PAPER_ASSETS_URL = "https://paper-api.alpaca.markets/v2/assets"
EODHD_BASE = "https://eodhd.com/api"
# Geographical Europe, NOT merely the EU-27 or euro area; not claims of
# issuer domicile. Provider exchange CountryISO2 is the *venue* country.
EUROPE_VENUES = frozenset({
    "AD", "AL", "AT", "BA", "BE", "BG", "BY", "CH", "CY", "CZ",
    "DE", "DK", "EE", "ES", "FI", "FR", "GB", "GR", "HR", "HU",
    "IE", "IS", "IT", "LI", "LT", "LU", "LV", "MC", "MD", "ME",
    "MK", "MT", "NL", "NO", "PL", "PT", "RO", "RS", "RU", "SE",
    "SI", "SK", "SM", "TR", "UA", "VA", "XK"
})
SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-_]{0,39}$")
EXCHANGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,20}$")
ALPACA_VENUES = frozenset({"AMEX","ARCA","BATS","NYSE","NASDAQ","NYSEARCA","OTC","TXSE"})
US_LIT_VENUES = ALPACA_VENUES - {"OTC"}
MAX_ASSETS = 150_000
MAX_RESPONSE_BYTES = 25_000_000


class CatalogUnavailable(RuntimeError):
    """Sanitized error: do not leak request URL/query containing EODHD key."""


def _json_get(url: str, *, headers: dict[str, str] | None = None,
              opener: Callable = urllib.request.urlopen) -> object:
    request = urllib.request.Request(
        url, headers={"Accept":"application/json", **(headers or {})},
        method="GET"
    )
    try:
        with opener(request, timeout=35) as response:
            raw = response.read(MAX_RESPONSE_BYTES+1)
        if len(raw)>MAX_RESPONSE_BYTES:
            raise CatalogUnavailable("Catalog response exceeds safe byte limit")
        return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise CatalogUnavailable(f"Catalog request rejected (HTTP {int(exc.code)})") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, UnicodeError):
        raise CatalogUnavailable("Catalog request failed or returned invalid JSON") from None


def fetch_alpaca_paper_assets(*, api_key: str | None = None,
                              api_secret: str | None = None,
                              opener: Callable = urllib.request.urlopen) -> list[dict]:
    """GET only, default all active US equity class assets, no 50-name cap.

    Alpaca's asset class 'us_equity' includes equities and ETFs: the result
    MUST NOT be presented as a count of stock *companies* alone.
    """
    key=(api_key if api_key is not None else os.getenv("ALPACA_PAPER_DATA_KEY_ID","")).strip()
    secret=(api_secret if api_secret is not None else os.getenv("ALPACA_PAPER_DATA_SECRET_KEY","")).strip()
    if not key or not secret:
        raise CatalogUnavailable("Alpaca PAPER credentials unavailable")
    url=PAPER_ASSETS_URL+"?"+urllib.parse.urlencode(
        {"status":"active","asset_class":"us_equity"}
    )
    rows=_json_get(url,headers={"APCA-API-KEY-ID":key,
                                "APCA-API-SECRET-KEY":secret},
                   opener=opener)
    if not isinstance(rows,list) or len(rows)>MAX_ASSETS or not rows:
        raise CatalogUnavailable("Unexpected Alpaca asset catalog size/schema")
    by_id={}
    for row in rows:
        if not isinstance(row,dict):
            raise CatalogUnavailable("Invalid Alpaca asset metadata row")
        ticker=row.get("symbol")
        venue=row.get("exchange")
        if (row.get("class")!="us_equity" or row.get("status")!="active"
                or not isinstance(ticker,str) or not SYMBOL_RE.fullmatch(ticker)
                or venue not in ALPACA_VENUES):
            continue
        asset_id=row.get("id")
        if not isinstance(asset_id,str) or not asset_id:
            raise CatalogUnavailable("Missing stable Alpaca asset ID")
        if asset_id in by_id:
            raise CatalogUnavailable("Duplicate Alpaca asset ID")
        by_id[asset_id]={
            "source":"ALPACA_PAPER_ASSETS",
            "asset_id":asset_id,
            "symbol":ticker,
            "venue":venue,
            "venue_country":"US",
            "asset_type":"US_EQUITY_CLASS_STOCK_OR_ETF",
            "broker_tradable_flag":row.get("tradable") is True,
            "historical_price_data_verified":False,
            "history_non_display_rights_verified":False,
            "real_order_authorized":False,
        }
    if not by_id:
        raise CatalogUnavailable("No qualifying Alpaca US-equity-class assets")
    return sorted(by_id.values(),key=lambda x:(x["venue"],x["symbol"],x["asset_id"]))


def fetch_eodhd_exchanges(*, api_token: str | None = None,
                          opener: Callable = urllib.request.urlopen) -> list[dict]:
    key=(api_token if api_token is not None else os.getenv("EODHD_API_TOKEN","")).strip()
    if not key:
        raise CatalogUnavailable("EODHD catalog token unavailable")
    url=f"{EODHD_BASE}/exchanges-list/?"+urllib.parse.urlencode({"api_token":key})
    rows=_json_get(url,opener=opener)
    if not isinstance(rows,list) or len(rows)>200 or not rows:
        raise CatalogUnavailable("Invalid EODHD exchange directory")
    normalized={}
    for row in rows:
        if not isinstance(row,dict):
            raise CatalogUnavailable("Invalid EODHD exchange row")
        code=row.get("Code")
        country=row.get("CountryISO2")
        if not isinstance(code,str) or not EXCHANGE_RE.fullmatch(code):
            continue
        if not isinstance(country,str):
            continue
        country=country.upper().strip()
        if country=="UK":
            country="GB"
        if country not in EUROPE_VENUES:
            continue
        if code in normalized and normalized[code]!=country:
            raise CatalogUnavailable("Conflicting exchange-country metadata")
        normalized[code]=country
    if not normalized:
        raise CatalogUnavailable("No European exchange venues in provider catalog")
    return [{"exchange_code":code,"venue_country":country}
            for code,country in sorted(normalized.items())]


def fetch_eodhd_common_stocks(exchange_code: str, *, venue_country: str,
                              api_token: str | None = None,
                              include_delisted: bool = False,
                              opener: Callable = urllib.request.urlopen) -> list[dict]:
    """Read one venue's common stocks; keep delisted separate from active.

    No broker/ISIN crosswalk or trading permission is inferred. All source
    identifiers remain in memory; CLI intentionally reports only aggregates.
    """
    if not isinstance(exchange_code,str) or not EXCHANGE_RE.fullmatch(exchange_code):
        raise ValueError("Invalid EODHD exchange code")
    if venue_country not in EUROPE_VENUES:
        raise ValueError("Selected exchange not in geographical Europe")
    key=(api_token if api_token is not None else os.getenv("EODHD_API_TOKEN","")).strip()
    if not key:
        raise CatalogUnavailable("EODHD catalog token unavailable")
    params={"api_token":key,"fmt":"json","type":"common_stock",
            "delisted": 1 if include_delisted else 0}
    url=f"{EODHD_BASE}/exchange-symbol-list/{exchange_code}?"+urllib.parse.urlencode(params)
    rows=_json_get(url,opener=opener)
    if not isinstance(rows,list) or len(rows)>MAX_ASSETS:
        raise CatalogUnavailable("Invalid EODHD exchange symbol list")
    unique={}
    for row in rows:
        if not isinstance(row,dict):
            raise CatalogUnavailable("Invalid EODHD symbol metadata")
        code=row.get("Code")
        kind=row.get("Type")
        # Provider's type=common_stock filter is useful but still validate
        # each row: never quietly accept ETFs, warrants or preferred.
        if kind not in ("Common Stock","Stock"):
            continue
        if not isinstance(code,str) or not SYMBOL_RE.fullmatch(code):
            continue
        ccy=row.get("Currency")
        if not isinstance(ccy,str) or not re.fullmatch(r"[A-Z]{3}",ccy):
            continue
        identity=(exchange_code,code,ccy)
        if identity in unique:
            raise CatalogUnavailable("Duplicate exchange symbol+currency")
        unique[identity]={
            "source":"EODHD_EXCHANGE_SYMBOLS",
            "exchange_code":exchange_code,
            "venue_country":venue_country,
            "symbol":code,
            "quote_currency":ccy,
            "isin":row.get("Isin") if isinstance(row.get("Isin"),str) else None,
            "listing_state":"DELISTED_HISTORY_ONLY" if include_delisted else "ACTIVE_CATALOG",
            "broker_availability_verified":False,
            "historical_price_data_verified":False,
            "history_non_display_rights_verified":False,
            "real_order_authorized":False,
        }
    return [unique[k] for k in sorted(unique)]


def plan_batches(records: list[dict], *, batch_size: int = 200,
                 batch_index: int = 0) -> dict:
    """Deterministic non-overlapping slices; no fabricated prices/signals.

    A run over batch indices 0..N-1 covers each provided catalog entry once.
    Uses (source, venue, symbol, currency or asset_id) to avoid collapsing
    genuinely distinct regional listings under the same ticker.
    """
    if (type(batch_size) is not int or not 1<=batch_size<=5000 or
            type(batch_index) is not int or batch_index<0):
        raise ValueError("Invalid batch size/index")
    if not isinstance(records,list) or len(records)>1_000_000:
        raise ValueError("Invalid inventory")
    keys=set()
    ordered=[]
    for item in records:
        if not isinstance(item,dict):
            raise ValueError("Invalid inventory row")
        source=item.get("source")
        venue=item.get("venue",item.get("exchange_code"))
        symbol=item.get("symbol")
        if not all(isinstance(x,str) and x for x in (source,venue,symbol)):
            raise ValueError("Missing listing identity")
        identity=(source,venue,symbol,
                  item.get("quote_currency",item.get("asset_id","")))
        if identity in keys:
            raise ValueError("Duplicate listing in inventory")
        keys.add(identity)
        ordered.append((identity,item))
    ordered.sort(key=lambda x:x[0])
    start=batch_index*batch_size
    return {
        "total_listings":len(ordered),
        "batch_index":batch_index,
        "batch_size":batch_size,
        "batch_count":(len(ordered)+batch_size-1)//batch_size,
        "listings":[item for _,item in ordered[start:start+batch_size]],
        "priced_count":0,
        "paper_order_authorized":False,
        "real_order_authorized":False,
    }


def safe_counts(records: list[dict]) -> dict:
    """Summary without ticker/ISIN/customer data; no company-count claim."""
    by_country=Counter(row["venue_country"] for row in records)
    by_source=Counter(row["source"] for row in records)
    return {
        "mode":"METADATA_ONLY_BROAD_MARKET_DISCOVERY",
        "listing_count":len(records),
        "by_venue_country":dict(sorted(by_country.items())),
        "by_provider":dict(sorted(by_source.items())),
        "includes_issuer_duplicates_and_etfs_if_alpaca":True,
        "all_exchange_coverage_proven":False,
        "historical_price_coverage_proven":False,
        "securities_tradeable_by_user_verified":False,
        "paper_order_authorized":False,
        "real_order_authorized":False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description="Private metadata counts only")
    parser.add_argument("--provider",choices=("alpaca","eodhd"),default="alpaca")
    parser.add_argument("--start-exchange",type=int,default=0)
    parser.add_argument("--max-exchanges",type=int,default=2)
    args=parser.parse_args()
    try:
        if args.provider=="alpaca":
            assets=fetch_alpaca_paper_assets()
            print(json.dumps(safe_counts(assets)))
            return
        venues=fetch_eodhd_exchanges()
        if (args.start_exchange<0 or args.max_exchanges<1 or
                args.max_exchanges>5 or args.start_exchange>=len(venues)):
            raise ValueError("Invalid EODHD exchange chunk")
        chosen=venues[args.start_exchange:args.start_exchange+args.max_exchanges]
        instruments=[]
        for venue in chosen:
            instruments.extend(fetch_eodhd_common_stocks(
                venue["exchange_code"],venue_country=venue["venue_country"]))
        counts=safe_counts(instruments)
        counts.update({
            "provider_exchange_count":len(venues),
            "exchanges_processed":len(chosen),
            "start_exchange":args.start_exchange,
            "full_europe_coverage_in_this_run":len(chosen)==len(venues),
            "missing_exchanges":len(venues)-len(chosen),
        })
        print(json.dumps(counts))
    except (CatalogUnavailable, ValueError) as exc:
        # Only sanitized errors; never reveal tokens or raw provider rows.
        parser.exit(2,str(exc)+"\n")


if __name__=="__main__":
    main()
