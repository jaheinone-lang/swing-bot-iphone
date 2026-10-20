"""Daily read-only Trading 212 catalog research for the iPhone dashboard.

The broker grants instrument discovery, NOT OHLCV/financials.
Only aggregates are published. Ranking is possible only when a separate,
licensed, verified, split-adjusted EUR OHLCV feed is supplied. No fake
'best stocks' when there is no price data. No trade APIs or account access.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, date
from pathlib import Path

from .trading212_universe import load_demo_universe, summarize_universe
from .equity_screen import screen_equity, DailyBar
from .eu_watchlist import eu_isin_prefix_counts, eu_research_readiness
from .helsinki_broker_metadata import helsinki_broker_candidates


def rank_verified_eur_candidates(
    instruments: list[dict],
    validated_feeds: dict[str, dict],
    *, as_of: date,
    top_n: int = 20,
) -> dict:
    """Whitelist by exact broker ticker + currency + type; never infer listing.

    Each validated_feeds[ticker] must explicitly contain:
      candles: >=201 validated DailyBar objects
      source: nonempty source description
      adjusted_for_corporate_actions: True
      quote_currency: EUR
      verified_spread_bps: float or None

    Calling this function with no verified feeds is valid. A missing provider
    cannot silently turn broker metadata into a BUY signal.
    """
    if not (isinstance(top_n, int) and 1 <= top_n <= 100):
        raise ValueError("Invalid top_n")
    by_ticker = {r["ticker"]: r for r in instruments
                 if r.get("type") in {"STOCK", "ETF"}
                 and r.get("currencyCode") == "EUR"
                 and isinstance(r.get("ticker"), str)}
    results = []
    rejections = 0
    matched = 0
    for ticker, feed in sorted(validated_feeds.items()):
        if ticker not in by_ticker:
            rejections += 1
            continue
        if (not isinstance(feed, dict) or
            feed.get("quote_currency") != "EUR" or
            not feed.get("source") or
            feed.get("adjusted_for_corporate_actions") is not True or
            not isinstance(feed.get("candles"), (tuple, list)) or
            not all(isinstance(x, DailyBar) for x in feed["candles"])):
            rejections += 1
            continue
        matched += 1
        instrument = by_ticker[ticker]
        candidate = screen_equity(
            ticker, instrument["type"], "EUR", list(feed["candles"]),
            as_of=as_of, adjusted_for_corporate_actions=True,
            verified_spread_bps=feed.get("verified_spread_bps"),
        )
        if candidate["status"] in ("SCREENED", "WATCH_ONLY_NO_EXECUTION"):
            results.append(candidate)
        else:
            rejections += 1
    # Only screen candidates with completed data; no price guesses.
    # For the same point score, use the stable ticker order.
    results.sort(key=lambda r: (-r["points"], r["symbol"]))
    return {
        "feed_matched": matched,
        "feed_rejected_or_unmatched": rejections,
        "candidates_checked": len(results),
        "top_candidates": results[:top_n],
        "price_data_connected": matched > 0,
        "ranking_status": "PRICE_SCREEN_READY" if matched else "AWAITING_LICENSED_PRICE_DATA",
        "rank_is_investment_advice": False,
        "paper_order_authorized": False,
        "live_order_authorized": False,
    }


def build_catalog_report(
    instruments: list[dict], *,
    as_of: date | None = None,
    generated_at_utc: datetime | None = None,
    validated_feeds: dict[str, dict] | None = None,
) -> dict:
    if not instruments:
        raise ValueError("No validated broker instruments; keep prior report")
    generated = generated_at_utc or datetime.now(timezone.utc)
    if generated.tzinfo is None:
        raise ValueError("Report timestamp needs timezone")
    as_of = as_of or generated.date()
    counts = summarize_universe(instruments, as_of=as_of)
    # Public AGGREGATE ONLY: ISIN prefix is not proof of EU issuer
    # domicile or exchange, and no actual broker ticker is published.
    eu_counts = eu_isin_prefix_counts(instruments)
    eu_watch = eu_research_readiness()
    helsinki = helsinki_broker_candidates(instruments)
    # Source is private account metadata; publish only aggregated counts.
    screening = rank_verified_eur_candidates(
        instruments, validated_feeds or {}, as_of=as_of
    )
    return {
        "schema_version": 1,
        "generated_at_utc": generated.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "as_of": as_of.isoformat(),
        "status": "TRADING212_DEMO_METADATA_CONNECTED",
        "data_mode": "BROKER_INSTRUMENT_METADATA_ONLY",
        "instruments": {
            "stocks": counts["stock_instruments"],
            "etfs": counts["etf_instruments"],
            "total": counts["stock_instruments"] + counts["etf_instruments"],
            "unique_isins": counts["unique_isins"],
            "by_currency": counts["currencies"],
            "platform_additions_last_30d": counts["platform_additions_30d"],
        },
        "eu_stock_research": {
            "status": eu_counts["status"],
            "stocks_with_eu_isin_prefix": eu_counts["stocks_with_eu_isin_prefix"],
            "eur_quoted_eu_isin_prefix_stocks":
                eu_counts["eur_quoted_eu_isin_prefix_stocks"],
            "by_quote_currency": eu_counts["by_quote_currency"],
            "by_isin_prefix": eu_counts["by_isin_prefix"],
            "curated_watchlist_size": eu_watch["curated_listings"],
            "curated_countries": eu_watch["eu_countries_represented"],
            "curated_quote_currencies": eu_watch["sample_symbols_by_currency"],
            "requires_historical_fx": eu_watch["fx_history_required_for"],
            "eu_issuer_domicile_verified": False,
            "listing_venue_verified": False,
            "broker_matches_verified": 0,
            "price_history_verified": False,
            "eu_abc_backtest_ready": False,
            "orders_enabled": False,
        },
        "helsinki_research": helsinki,
        "screening": screening,
        "ipo_status": "NO_VERIFIED_EXCHANGE_IPO_FEED",
        "recent_platform_additions_are_ipos": False,
        "price_history_available_from_trading212": False,
        "fundamental_data_available_from_trading212": False,
        "catalog_is_full_market_data_scan": False,
        "private_instrument_list_published": False,
        "auto_trading_enabled": False,
        "note": (
            "Trading 212 Practice catalog matched once per day. "
            "addedOn means added to Trading 212, NOT exchange IPO. "
            "EU ISIN country prefix is not proof of issuer domicile or venue. "
            "Top-20 price/momentum ranking requires separate verified "
            "split-adjusted EUR OHLCV and liquidity data. "
            "No broker orders and no financial performance claims."
        ),
    }


def refresh_catalog(*, output: Path) -> dict:
    items = load_demo_universe()
    report = build_catalog_report(items)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only daily T212 demo research")
    parser.add_argument("--output", default="docs/universe_research.json")
    args = parser.parse_args()
    report = refresh_catalog(output=Path(args.output))
    # Aggregate-only logs; don't print instruments or secret data.
    print(json.dumps({
        "success": True,
        "generated_at": report["generated_at_utc"],
        "totals": report["instruments"],
        "price_ranking": report["screening"]["ranking_status"],
        "real_orders": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
