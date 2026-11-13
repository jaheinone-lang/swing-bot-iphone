"""US broad-listing price screening, separate from legacy fixed-50 lab.

Only read-only historical data calls after explicit non-display research
permission. Inventories originate from Alpaca PAPER active asset metadata
and are processed in bounded, deterministic batches. No broker orders, no
price data or per-symbol ranks in logs, no return/outperformance claims.
An Alpaca asset can be an ETF rather than an operating company.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from typing import Callable

from .alpaca_iex import AlpacaUnavailable, fetch_iex_bars, preliminary_iex_score
from .broad_market_catalog import (
    fetch_alpaca_paper_assets, plan_batches, CatalogUnavailable, US_LIT_VENUES
)

MAX_BATCH = 100


def private_wide_us_scan(*, as_of: date | None = None,
                         inventory: list[dict] | None = None,
                         batch_index: int = 0,
                         batch_size: int = 25,
                         feed: str = "iex",
                         personal_research_data_rights_confirmed: bool = False,
                         loader: Callable = fetch_iex_bars) -> dict:
    """Preliminary restricted batch scan; no best-trades output.

    By default does NOTHING without explicit permission. API credentials
    remain in environment secrets; no data are persisted or published.
    """
    if not personal_research_data_rights_confirmed:
        return {
            "status":"AWAITING_NON_DISPLAY_DATA_USE_PERMISSION",
            "attempted":0,
            "qualified_ranks":0,
            "asset_catalog_loaded":False,
            "real_order_authorized":False,
            "paper_order_authorized":False,
        }
    if type(batch_size) is not int or not 1 <= batch_size <= MAX_BATCH:
        raise ValueError("Batch size must be 1..100")
    if type(batch_index) is not int or batch_index < 0:
        raise ValueError("Invalid batch index")
    if feed not in ("iex","sip"):
        raise ValueError("Invalid Alpaca feed")
    as_of = as_of or datetime.now(timezone.utc).date()
    inventory = fetch_alpaca_paper_assets() if inventory is None else inventory
    # No OTC and no temporarily nontradable assets in the shortlist.
    # Tradable flag alone does NOT imply the user's broker can buy it.
    eligible = [asset for asset in inventory
                if asset.get("source") == "ALPACA_PAPER_ASSETS"
                and asset.get("broker_tradable_flag") is True
                and asset.get("venue") in US_LIT_VENUES]
    batches = plan_batches(eligible,batch_size=batch_size,batch_index=batch_index)
    chosen = batches["listings"]
    allowed=frozenset(row["symbol"] for row in chosen)
    if len(allowed)!=len(chosen):
        # Multiple asset IDs may share ticker; avoid duplicate history pull
        # and prohibit ambiguous source identity.
        raise ValueError("Ambiguous active Alpaca symbol in selected batch")
    scores=[]
    failures=0
    expected=("ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL" if feed=="sip"
              else "ALPACA_BASIC_IEX_ONLY_NOT_CONSOLIDATED")
    for row in chosen:
        symbol=row["symbol"]
        try:
            history=loader(symbol,as_of=as_of,feed=feed,allowed_symbols=allowed)
            if history.ticker!=symbol or history.source!=expected:
                raise AlpacaUnavailable("Unexpected returned price feed")
            scores.append(preliminary_iex_score(history,as_of=as_of))
        except AlpacaUnavailable:
            failures+=1
    # Never print derived per-company ranks or raw OHLCV (data-use rights).
    scores.sort(key=lambda r:(-r["score"],-r["momentum_60d_pct"],r["symbol"]))
    return {
        "mode":"PRIVATE_BATCHED_US_HISTORICAL_DISCOVERY",
        "status":"RESEARCH_ONLY_NO_ORDERS",
        "assets_in_inventory":len(inventory),
        "lit_venue_tradable_candidates":len(eligible),
        "batch_index":batch_index,
        "batch_count":batches["batch_count"],
        "attempted":len(chosen),
        "qualified_ranks":len(scores),
        "failed":failures,
        "private_top20_count":min(20,len(scores)),
        "data_feed":feed.upper(),
        "iex_is_not_consolidated_market_volume":feed=="iex",
        "eur_fx_verified":False,
        "trading212_available_verified":False,
        "annual_returns_proven":False,
        "broker_order_requests_made":False,
        "private_symbols_published":False,
        "paper_order_authorized":False,
        "real_order_authorized":False,
    }


def main() -> None:
    from argparse import ArgumentParser
    parser=ArgumentParser(description="Private, permission-gated US research")
    parser.add_argument("--batch-size",type=int,default=25)
    parser.add_argument("--batch-index",type=int,default=0)
    parser.add_argument("--feed",choices=("iex","sip"),default="iex")
    args=parser.parse_args()
    approved=os.getenv("ALPACA_PERSONAL_RESEARCH_OK","").lower()=="true"
    try:
        report=private_wide_us_scan(
            personal_research_data_rights_confirmed=approved,
            batch_size=args.batch_size,batch_index=args.batch_index,
            feed=args.feed)
        print(json.dumps(report))
    except (CatalogUnavailable,AlpacaUnavailable,ValueError) as exc:
        # Sanitized exceptions only; never print HTTP URLs/headers.
        parser.exit(2,str(exc)+"\n")


if __name__=="__main__":
    main()
