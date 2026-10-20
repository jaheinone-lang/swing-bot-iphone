"""Conservative Helsinki Trading 212 metadata screening, PRIVATE aggregate only.

An ISIN starting FI does NOT prove the trading venue is Helsinki.
This reports EUR-denominated Finnish-ISIN stock candidates only; does
not match a curated watchlist to a broker instrument or grant order rights.
"""
from __future__ import annotations
import re
from collections import Counter

def helsinki_broker_candidates(instruments: list[dict]) -> dict:
    seen=set()
    currencies=Counter()
    total=0
    for row in instruments:
        if not isinstance(row,dict) or row.get("type")!="STOCK":
            continue
        isin=row.get("isin")
        ticker=row.get("ticker")
        currency=row.get("currencyCode")
        if (not isinstance(isin,str) or
            not re.fullmatch(r"FI[A-Z0-9]{10}",isin) or
            not isinstance(ticker,str) or not ticker or
            not isinstance(currency,str) or
            not re.fullmatch(r"[A-Z]{3}",currency)):
            continue
        key=(isin,ticker)
        if key in seen:
            continue
        seen.add(key)
        total+=1
        currencies[currency]+=1
    return {
        "mode":"FI_ISIN_STOCK_AGGREGATES_ONLY",
        "fi_isin_stock_instruments":total,
        "fi_isin_eur_quoted_instruments":currencies["EUR"],
        "by_quote_currency":dict(sorted(currencies.items())),
        "nasdaq_helsinki_venue_verified":False,
        "curated_symbol_identity_verified":False,
        "price_feed_broker_mapping_verified":False,
        "top10_ready":False,
        "orders_enabled":False,
    }
