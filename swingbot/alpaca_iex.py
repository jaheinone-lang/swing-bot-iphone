"""Read-only Alpaca free IEX stock-bars adapter for US research.

Alpaca Trading API's Basic market-data tier supports historical US stock
bars and is explicitly documented as backtesting-capable. Free IEX bars
represent ONE venue only and its volumes must never be treated as the
consolidated US market volume. No trading endpoints, balances or orders.

The existing Trading 212 EUR paper portfolio is deliberately untouched.
Credentials go ONLY in GitHub Actions Secrets, never source, logs or URLs.
Source-derived per-symbol quotes/rankings must NOT be published publicly
without permission to redistribute. This module writes no artifacts.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from statistics import mean
from typing import Callable

from .equity_screen import DailyBar
from .massive_free import FreeMarketFeedUnavailable, FreeMarketHistory
from .us_watchlist import US_WATCHLIST_50

HOST = "https://data.alpaca.markets"
PATH = "/v2/stocks/{symbol}/bars"
ALLOWED_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
MAX_PAGES = 6
MAX_BYTES = 2_000_000


class AlpacaUnavailable(RuntimeError):
    pass


def parse_iex_pages(pages: list[dict], *, symbol: str, as_of: date,
                    feed: str="iex") -> FreeMarketHistory:
    """Reject incomplete/paginated, stale, duplicate or mismatched EOD bars."""
    if feed not in ("iex", "sip"):
        raise AlpacaUnavailable("Invalid historical feed")
    if not ALLOWED_SYMBOL.fullmatch(symbol) or symbol not in US_WATCHLIST_50:
        raise AlpacaUnavailable("Ticker outside 50-symbol allowlist")
    if not pages or len(pages) > MAX_PAGES:
        raise AlpacaUnavailable("Missing or excessive response pages")
    bars = []
    for idx, payload in enumerate(pages):
        if not isinstance(payload, dict):
            raise AlpacaUnavailable("Malformed Alpaca EOD response")
        # A matching symbol is supplied by URL, not by a trustworthy ticker
        # property in Alpaca's single-symbol response.
        next_token = payload.get("next_page_token")
        if idx < len(pages)-1 and not next_token:
            raise AlpacaUnavailable("Unexpected page boundary")
        if idx == len(pages)-1 and next_token:
            raise AlpacaUnavailable("Incomplete paginated history")
        records=payload.get("bars")
        if not isinstance(records, list) or len(records)>10000:
            raise AlpacaUnavailable("Malformed EOD records")
        for r in records:
            if not isinstance(r, dict):
                raise AlpacaUnavailable("Invalid IEX price bar")
            try:
                stamp=r["t"]
                if not isinstance(stamp,str) or len(stamp)<10:
                    raise ValueError("Invalid timestamp")
                # Date prefix of RFC-3339 timestamp describes market
                # session date; all requests here are 1Day historical bars.
                d=date.fromisoformat(stamp[:10])
                if d >= as_of:
                    continue  # never consider incomplete same-day bar
                fields=(float(r[k]) for k in ("o","h","l","c","v"))
                bar=DailyBar(d,*fields)
            except (ValueError, TypeError, OverflowError, KeyError):
                raise AlpacaUnavailable("Missing or invalid OHLCV bar") from None
            bars.append(bar)
    if len(bars) < 260:
        raise AlpacaUnavailable("Need >=260 completed IEX daily sessions")
    if any(a.day>=b.day for a,b in zip(bars,bars[1:])):
        raise AlpacaUnavailable("Unsorted or duplicate IEX bars")
    if not (1 <= (as_of-bars[-1].day).days <= 7):
        raise AlpacaUnavailable("IEX data stale or from the future")
    return FreeMarketHistory(
        ticker=symbol, currency="USD",
        source=("ALPACA_BASIC_IEX_ONLY_NOT_CONSOLIDATED" if feed=="iex"
                else "ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"),
        adjustment="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",
        bars=tuple(bars),
    )


def fetch_iex_bars(
    symbol: str, *,
    key_id: str | None=None, secret_key: str | None=None,
    as_of: date | None=None,
    feed: str="iex",
    urlopen: Callable=urllib.request.urlopen,
) -> FreeMarketHistory:
    """Only historical split-adjusted GETs, explicit feed, bounded pagination.

    Basic may access >=15-min-old SIP historical bars depending on account
    entitlements. A 403 must FAIL, never silently downgrade to IEX.
    """
    if feed not in ("iex", "sip"):
        raise AlpacaUnavailable("Invalid historical feed")
    key = (key_id if key_id is not None
           else os.getenv("ALPACA_DATA_KEY_ID","")).strip()
    secret = (secret_key if secret_key is not None
              else os.getenv("ALPACA_DATA_SECRET_KEY","")).strip()
    if not key or not secret:
        raise AlpacaUnavailable("Alpaca market-data API credentials missing")
    if symbol not in US_WATCHLIST_50 or not ALLOWED_SYMBOL.fullmatch(symbol):
        raise AlpacaUnavailable("Stock outside predeclared watchlist")
    now=as_of or datetime.now(timezone.utc).date()
    start=now-timedelta(days=850)
    end=now-timedelta(days=1)
    data=[]
    token=None
    seen=set()
    for _ in range(MAX_PAGES):
        query={
            "start":start.isoformat(),"end":end.isoformat(),
            "timeframe":"1Day","adjustment":"split",
            "feed":feed,"sort":"asc","limit":"10000",
        }
        if token:
            query["page_token"]=token
        # Never use next_page URL from an untrusted API response.
        url=HOST+PATH.format(symbol=symbol)+"?"+urllib.parse.urlencode(query)
        request=urllib.request.Request(
            url,method="GET",
            headers={
                "APCA-API-KEY-ID":key,
                "APCA-API-SECRET-KEY":secret,
                "User-Agent":"SwingBotPrivateUSDResearch/0.1",
                "Accept":"application/json",
            })
        try:
            with urlopen(request, timeout=25) as response:
                blob=response.read(MAX_BYTES+1)
            if len(blob)>MAX_BYTES:
                raise AlpacaUnavailable("IEX daily response too large")
            page=json.loads(blob)
        except urllib.error.HTTPError as e:
            # HTTP status ONLY: never log headers, bodies, URLs or secrets.
            raise AlpacaUnavailable(
                "Alpaca IEX request HTTP "+str(int(e.code))
            ) from None
        except (urllib.error.URLError, TimeoutError,
                ValueError, UnicodeError) as e:
            raise AlpacaUnavailable("Alpaca IEX response unavailable") from None
        if not isinstance(page,dict):
            raise AlpacaUnavailable("Alpaca IEX JSON is not an object")
        data.append(page)
        token=page.get("next_page_token")
        if not token:
            return parse_iex_pages(data,symbol=symbol,as_of=now,feed=feed)
        if (not isinstance(token,str) or not (1<=len(token)<=512)
            or token in seen):
            raise AlpacaUnavailable("Invalid/repeated pagination token")
        seen.add(token)
    raise AlpacaUnavailable("Too many response pages: incomplete history")


def preliminary_iex_score(
    feed: FreeMarketHistory, *, as_of: date
) -> dict:
    """Preliminary price-pattern ordering. NO full-market liquidity assertion.

    IEX venue volumes cannot support whole-US-market liquidity thresholds.
    No live/paper trade authorization and no transaction-cost backtest.
    """
    if (feed.source not in (
          "ALPACA_BASIC_IEX_ONLY_NOT_CONSOLIDATED",
          "ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL") or
        feed.currency!="USD" or
        feed.adjustment!="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED"):
        raise AlpacaUnavailable("Unexpected data source/currency/adjustment")
    h=feed.bars
    if (len(h)<260 or h[-1].day>=as_of or
        (as_of-h[-1].day).days>7 or
        any(a.day>=b.day for a,b in zip(h,h[1:]))):
        raise AlpacaUnavailable("Incomplete or stale historical bars")
    price=h[-1].close
    sma50=mean(b.close for b in h[-50:])
    sma200=mean(b.close for b in h[-200:])
    momentum60=price/h[-61].close-1
    breakout=price>max(b.high for b in h[-21:-1])
    true_ranges=[
        max(h[i].high-h[i].low,
            abs(h[i].high-h[i-1].close),
            abs(h[i].low-h[i-1].close))
        for i in range(len(h)-14,len(h))
    ]
    atrp=mean(true_ranges)/price
    trend=price>sma50>sma200
    score=(
        (40 if trend else 0)+
        (25 if breakout else 0)+
        (25 if .05<=momentum60<=.50 else 0)+
        (10 if .012<=atrp<=.08 else 0)
    )
    # Note: omit USD price and raw volume in public logs; use only
    # in-memory private ranking. Redistributable content not established.
    return {
        "symbol":feed.ticker,"score":score,
        "momentum_60d_pct":round(momentum60*100,2),
        "breakout":breakout,"trend":trend,
        "atr_14d_pct":round(atrp*100,2),
        "data_day":h[-1].day.isoformat(),
        "coverage":("DELAYED_SIP_CONSOLIDATED_US" if
                    feed.source=="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"
                    else "IEX_ONLY_PARTIAL_US_MARKET"),
        "consolidated_volume_verified":(
            feed.source=="ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"),
        "broker_tradability_verified":False,
        "fx_to_eur_verified":False,
        "paper_trade_authorized":False,
        "live_order_authorized":False,
    }


def private_iex_50_scan(*, today: date | None=None,
                        symbols: tuple[str,...]=US_WATCHLIST_50,
                        loader: Callable=fetch_iex_bars,
                        research_permission_confirmed: bool=False,
                        feed: str="iex") -> dict:
    """Aggregate statuses only. No per-symbol data committed or logged.

    Research is intended for PERSONAL noncommercial experimentation.
    Confirm account terms before enabling the actual 50-stock analysis.
    """
    if not research_permission_confirmed:
        return {
            "status":"AWAITING_ALPACA_PERSONAL_DATA_USE_CONFIRMATION",
            "attempted":0,"verified":0,"failed":0,
            "top20_count":0,"prices_published":False,
            "broker_orders_enabled":False,
        }
    as_of=today or datetime.now(timezone.utc).date()
    if feed not in ("iex","sip"):
        raise ValueError("Unrecognized historical feed")
    if len(set(symbols))!=len(symbols) or any(s not in US_WATCHLIST_50 for s in symbols):
        raise ValueError("Invalid research watchlist")
    ranks=[]
    attempted=0
    failures=0
    for symbol in symbols:
        attempted+=1
        try:
            history=(loader(symbol,as_of=as_of,feed=feed)
                     if loader is fetch_iex_bars
                     else loader(symbol,as_of=as_of))
            if history.ticker!=symbol:
                raise AlpacaUnavailable("Ticker mismatch")
            expected_source=(
                "ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL" if feed=="sip"
                else "ALPACA_BASIC_IEX_ONLY_NOT_CONSOLIDATED"
            )
            if history.source!=expected_source:
                raise AlpacaUnavailable("Wrong requested feed; no silent downgrade")
            ranks.append(preliminary_iex_score(history,as_of=as_of))
        except AlpacaUnavailable:
            failures+=1
    # Ordering is computed transiently, NOT saved or included in output.
    ranks.sort(key=lambda r:(-r["score"],-r["momentum_60d_pct"],r["symbol"]))
    return {
        "status":("SIP_HISTORICAL_RESEARCH_PRELIMINARY" if ranks and feed=="sip"
                  else "IEX_RESEARCH_PRELIMINARY" if ranks
                  else "PRICE_FEED_UNAVAILABLE"),
        "attempted":attempted,"verified":len(ranks),
        "failed":failures,
        "top20_count":min(len(ranks),20),
        "coverage":("DELAYED_SIP_CONSOLIDATED_US" if feed=="sip"
                    else "IEX_ONLY_PARTIAL_US_MARKET"),
        "consolidated_volume_verified":(bool(ranks) and feed=="sip"),
        # Even SIP historical trade volume does not prove live spread or fills.
        "full_us_liquidity_verified":False,
        "trading212_matched":False,
        "price_data_redistributed":False,
        "ranks_published":False,
        "eur_paper_portfolio_changed":False,
        "broker_orders_enabled":False,
    }


def main():
    approved=os.getenv("ALPACA_PERSONAL_RESEARCH_OK","").lower()=="true"
    requested_feed=os.getenv("ALPACA_HISTORICAL_FEED","iex").strip().lower()
    result=private_iex_50_scan(research_permission_confirmed=approved,
                              feed=requested_feed)
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
