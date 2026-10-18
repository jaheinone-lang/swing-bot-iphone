"""Curated 50-name US large-cap research universe and offline ranking.

This module contains no network calls, broker connection, or broker orders.
It is for licensed or SYNTHETIC, injected USD price data only. The Massive
Stocks Basic personal-use terms prohibit non-display strategy/derived work
without suitable permission; do not wire this ranking to the Massive API
or publish per-symbol provider-derived results without authorization.
"""
from __future__ import annotations

from datetime import date
from math import isfinite
from typing import Mapping

from .massive_free import FreeMarketHistory, FreeMarketFeedUnavailable, private_us_research_score

# Hand-picked research selection, NOT a Trading 212 verified universe,
# not survivorship-bias-free and NOT a historical index membership snapshot.
US_WATCHLIST_50 = (
    # Technology / communication
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "AMD",
    "ORCL", "CRM", "ADBE", "NOW", "CSCO", "QCOM", "TXN", "AMAT",
    # Financial
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP",
    # Healthcare
    "UNH", "JNJ", "PFE", "ABBV", "MRK", "LLY", "TMO", "AMGN",
    # Industrial
    "CAT", "DE", "GE", "HON", "UNP", "RTX",
    # Consumer
    "WMT", "COST", "HD", "LOW", "MCD", "NKE", "KO", "PEP",
    # Energy
    "XOM", "CVX", "COP", "SLB",
)


def rank_us_research(
    histories: Mapping[str, FreeMarketHistory], *,
    as_of: date, limit: int = 20, licensed_non_display_use: bool = False,
) -> dict:
    """Score only exact, validated, USD split-adjusted WATCHLIST-50 histories.

    This does not attest Trading 212 membership, spread, FX, or orderability.
    Call only on appropriately LICENSED inputs or deliberately synthetic tests.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("Ranking size must be in 1..50")
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    if not licensed_non_display_use and any(
        history.source != "SYNTHETIC_TEST_FIXTURE"
        for history in histories.values() if isinstance(history, FreeMarketHistory)
    ):
        raise PermissionError(
            "Market-data non-display/strategy research license not verified; "
            "only synthetic offline inputs allowed by default"
        )
    if any(symbol not in US_WATCHLIST_50 for symbol in histories):
        raise ValueError("Input contains ticker outside predeclared watchlist")
    results = []
    rejected = 0
    for symbol, history in sorted(histories.items()):
        if (not isinstance(history, FreeMarketHistory)
            or history.ticker != symbol
            or history.currency != "USD"
            or history.adjustment != "SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED"
            or history.paper_trade_authorized
            or history.broker_available_verified
            or history.fx_verified
            or history.spread_verified
            or len(history.bars) < 201
            or any(x.day >= y.day for x,y in zip(history.bars, history.bars[1:]))
            or not all(isfinite(v) and v>0
                       for b in history.bars for v in
                       (b.open,b.high,b.low,b.close,b.volume))):
            rejected += 1
            continue
        try:
            score = private_us_research_score(
                history, as_of=as_of,
                licensed_non_display_use=licensed_non_display_use)
            if not score["liquidity_gate_ok"]:
                rejected += 1
                continue
            results.append(score)
        except (FreeMarketFeedUnavailable, ValueError, OverflowError, ZeroDivisionError):
            rejected += 1
    results.sort(key=lambda x: (-x["score"], -x["momentum_60d_pct"], x["symbol"]))
    return {
        "mode": "PRIVATE_OFFLINE_USD_RESEARCH",
        "as_of": as_of.isoformat(),
        "watchlist_nominal": len(US_WATCHLIST_50),
        "received": len(histories),
        "eligible": len(results),
        "rejected": rejected,
        "ranking": results[:limit],
        "price_data_provenance": (
            "LICENSED_NON_DISPLAY_RESEARCH" if licensed_non_display_use
            else "SYNTHETIC_TEST_FIXTURE_ONLY"
        ),
        "trading212_availability_checked": False,
        "eur_account_compatible": False,
        "paper_trade_authorized": False,
        "real_order_authorized": False,
    }
