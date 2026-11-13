"""All-provider-available US *common-stock listing metadata* inventory.

Source: EODHD US composite exchange common_stock active + delisted,
read-only GET. Do NOT conflate current data with historically point-in-time
membership; ticker renames, ticker re-use and vintage/splits are unresolved.

https://eodhd.com/financial-apis/delisted-stock-companies-data-2
https://eodhd.com/help/methodology

Only major US exchange venues and USD common stocks. Vendor filters may
vary and metadata may be missing. No OHLCV data is fetched, no account or
trading endpoint is accessed, and no raw inventory is ever printed by CLI.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from typing import Callable

from .broad_market_catalog import (
    EODHD_BASE,SYMBOL_RE,MAX_ASSETS,CatalogUnavailable,_json_get
)

US_MAJOR_VENUES=frozenset({
    "NASDAQ","NYSE","AMEX","NYSE MKT","NYSE ARCA","BATS",
})
US_ALLOWED_TYPES=frozenset({"Common Stock","Stock"})


def fetch_eodhd_us_common_stocks(*, delisted:bool, api_token:str|None=None,
                                opener:Callable=urllib.request.urlopen
                                ) -> list[dict]:
    """Source-supported, not historical PIT. No automatic price backtest."""
    if type(delisted) is not bool:
        raise ValueError("Delisted catalog switch must be boolean")
    token=(api_token if api_token is not None
           else os.getenv("EODHD_API_TOKEN","")).strip()
    if not token:
        raise CatalogUnavailable("EODHD metadata token not configured")
    url=(f"{EODHD_BASE}/exchange-symbol-list/US?"
         +urllib.parse.urlencode({
             "api_token":token,"fmt":"json",
             "type":"common_stock","delisted":1 if delisted else 0
         }))
    rows=_json_get(url,opener=opener)
    if not isinstance(rows,list) or not rows or len(rows)>MAX_ASSETS:
        raise CatalogUnavailable("EODHD US catalog unavailable or malformed")
    unique={}
    for row in rows:
        if not isinstance(row,dict):
            raise CatalogUnavailable("Malformed US exchange symbol row")
        sym=row.get("Code")
        venue=row.get("Exchange")
        if row.get("Type") not in US_ALLOWED_TYPES:
            continue
        if not isinstance(sym,str) or not SYMBOL_RE.fullmatch(sym):
            continue
        if venue not in US_MAJOR_VENUES or row.get("Currency")!="USD":
            continue
        isin=row.get("Isin")
        if isin is not None and not isinstance(isin,str):
            raise CatalogUnavailable("Invalid US listing ISIN")
        isin=isin.strip() if isinstance(isin,str) else None
        identity=(sym,venue,isin)
        if identity in unique:
            raise CatalogUnavailable("Duplicate US listing identity in source")
        unique[identity]={
            "source":"EODHD_US_EXCHANGE_DIRECTORY",
            "symbol":sym,
            "venue":venue,
            "currency":"USD",
            "isin":isin,
            "kind":"COMMON_STOCK_SOURCE_LABEL",
            "listing_status":("CURRENTLY_DELISTED" if delisted
                              else "ACTIVE_IN_CURRENT_PROVIDER_DIRECTORY"),
            "historical_listing_start_verified":False,
            "historical_listing_end_verified":False,
            "ticker_change_history_verified":False,
            "survivorship_bias_removed":False,
            "split_price_history_verified":False,
            "provider_non_display_data_rights_verified":False,
            "paper_order_authorized":False,
            "real_order_authorized":False,
        }
    if not unique:
        raise CatalogUnavailable("No major exchange USD common stocks verified")
    return [unique[k] for k in sorted(unique)]


def summarize_us_coverage(active:list[dict],delisted:list[dict]) -> dict:
    """Aggregate metadata without symbols, quote data or secret values."""
    if not active or not delisted:
        raise ValueError("Both active and delisted inventories required")
    for label,rows in (("ACTIVE_IN_CURRENT_PROVIDER_DIRECTORY",active),
                       ("CURRENTLY_DELISTED",delisted)):
        for row in rows:
            if (row.get("listing_status")!=label or
                    row.get("source")!="EODHD_US_EXCHANGE_DIRECTORY" or
                    row.get("venue") not in US_MAJOR_VENUES):
                raise ValueError("Catalog provenance mismatch")
    asyms={r["symbol"] for r in active}
    dsyms={r["symbol"] for r in delisted}
    by_active=dict(sorted(Counter(r["venue"] for r in active).items()))
    by_delisted=dict(sorted(Counter(r["venue"] for r in delisted).items()))
    return {
        "status":"US_HISTORICAL_INVENTORY_DISCOVERY_METADATA_ONLY",
        "active_major_exchange_common_stock_listings":len(active),
        "delisted_major_exchange_common_stock_listings":len(delisted),
        "combined_listing_entries":len(active)+len(delisted),
        "symbols_appearing_in_both_statuses":len(asyms & dsyms),
        "active_listing_counts_by_venue":by_active,
        "delisted_listing_counts_by_venue":by_delisted,
        "source_universe_is_complete_guaranteed":False,
        "historical_point_in_time_membership_verified":False,
        "historical_ohlcv_or_full_split_adjustments_verified":False,
        "provider_data_license_for_automated_backtests_verified":False,
        "ticker_reuse_and_renames_resolved":False,
        "delisted_symbol_does_not_imply_failed_company":True,
        "stock_symbols_or_licenses_published":False,
        "paper_orders_enabled":False,
        "real_orders_enabled":False,
        "next_step":"Validate listing history, licensing and actual OHLCV in bounded private research batches"
    }


def main()->None:
    from argparse import ArgumentParser
    parser=ArgumentParser(description="US active+delisted metadata, no prices")
    parser.add_argument("--approved-personal-metadata-read",action="store_true")
    args=parser.parse_args()
    if not args.approved_personal_metadata_read:
        print(json.dumps({
            "status":"NOT_RUN_WITHOUT_PERSONAL_METADATA_APPROVAL",
            "requested":0,"orders_enabled":False
        }))
        return
    try:
        active=fetch_eodhd_us_common_stocks(delisted=False)
        inactive=fetch_eodhd_us_common_stocks(delisted=True)
        print(json.dumps(summarize_us_coverage(active,inactive),
                         allow_nan=False))
    except (CatalogUnavailable,ValueError):
        # Redact URL/token/vendor rows from ALL public errors
        parser.exit(2,"US catalog source unavailable or incompatible\n")


if __name__=="__main__":
    main()
