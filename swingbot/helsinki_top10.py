"""Helsinki TOP10: strict read-only private EUR research, no broker orders.

Requires actual verified exchange/ISIN/broker mapping and split-adjusted OHLCV.
An EODHD free raw EOD successful fetch alone is NOT a validated ranking feed.
"""
from __future__ import annotations
from datetime import date
from .helsinki_watchlist import HELSINKI_40
from .universe_pipeline import rank_verified_eur_candidates

HELSINKI_SYMBOLS = frozenset(symbol for _, symbol in HELSINKI_40)

def rank_helsinki_top10(*, instruments: list[dict],
                        feeds: dict[str, dict], as_of: date) -> dict:
    # Never infer Trading 212's internal ticker from a display symbol:
    # a validated feed key must match an independently verified broker ID.
    verified = {}
    rejected = 0
    for broker_ticker, source in feeds.items():
        if not isinstance(source, dict):
            rejected += 1
            continue
        research_symbol = source.get("research_symbol")
        if (research_symbol not in HELSINKI_SYMBOLS
                or source.get("exchange") != "XHEL"
                or source.get("exact_broker_isin_venue_match") is not True
                or source.get("provider_currency_verified") is not True
                or source.get("personal_strategy_use_rights_verified") is not True):
            rejected += 1
            continue
        verified[broker_ticker] = source
    result = rank_verified_eur_candidates(
        instruments, verified, as_of=as_of, top_n=10
    )
    result.update({
        "mode":"HELSINKI_TOP10_PRIVATE_VERIFIED_ONLY",
        "watchlist_size":len(HELSINKI_40),
        "unverified_feed_rejections":rejected,
        "candidate_returns_claimed":False,
        "public_ticker_ranking_authorized":False,
        "orders_enabled":False,
    })
    # Individual ranking contains market-data-derived signals and broker IDs,
    # therefore do NOT publish the result to the public dashboard.
    return result
