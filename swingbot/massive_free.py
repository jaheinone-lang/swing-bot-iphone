"""Massive US Stocks Basic (free) EOD adapter for private swing research.

Provider free tier: US equities only, approx 5 requests/minute, 2-year
historical window. Split-adjusted OHLCV, not dividend-adjusted. These are
USD securities; they are NEVER eligible for the existing EUR paper book
without independent FX and broker membership checks.

DO NOT publish licensed prices / per-symbol rankings to the public Pages site.
Output only aggregate source readiness in public GitHub workflow logs.
This file contains no Trading 212 trading/order operations.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import mean, median
from typing import Callable

from .equity_screen import DailyBar

WATCHLIST_USD = ("AAPL", "MSFT", "NVDA", "AMZN", "JPM", "XOM", "CAT", "UNH")
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
HOST = "https://api.massive.com"
MIN_CALL_GAP_SEC = 13.0   # 5 requests/min allows <= 1 per 12 sec.


class FreeMarketFeedUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class FreeMarketHistory:
    ticker: str
    currency: str
    source: str
    adjustment: str
    bars: tuple[DailyBar, ...]
    broker_available_verified: bool = False
    fx_verified: bool = False
    spread_verified: bool = False
    paper_trade_authorized: bool = False


def parse_massive_daily(payload: object, *, ticker: str,
                        as_of: date) -> FreeMarketHistory:
    """Strict validation of a completed, split-adjusted USD time series."""
    if not _SYMBOL.fullmatch(ticker):
        raise FreeMarketFeedUnavailable("Unsupported stock symbol")
    if (not isinstance(payload, dict) or payload.get("ticker") != ticker
            or payload.get("status") not in ("OK", "DELAYED")):
        raise FreeMarketFeedUnavailable("Unexpected stock data response")
    if payload.get("adjusted") is not True:
        raise FreeMarketFeedUnavailable("Split adjustment not verified")
    if payload.get("next_url"):
        # Do not silently score a truncated paginated time series.
        raise FreeMarketFeedUnavailable("Time-series pagination not supported")
    records = payload.get("results")
    if not isinstance(records, list) or len(records) > 2000:
        raise FreeMarketFeedUnavailable("Invalid or excessive EOD data")
    bars = []
    for r in records:
        if not isinstance(r, dict):
            raise FreeMarketFeedUnavailable("Invalid EOD row")
        try:
            ts = r["t"]
            if not isinstance(ts, int) or isinstance(ts, bool):
                raise ValueError("Invalid timestamp")
            d = datetime.fromtimestamp(ts/1000, timezone.utc).date()
            if d >= as_of:
                continue  # NEVER use still-forming current session
            if r.get("otc", False):
                raise ValueError("OTC excluded")
            b = DailyBar(d, float(r["o"]), float(r["h"]),
                         float(r["l"]), float(r["c"]), float(r["v"]))
        except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
            raise FreeMarketFeedUnavailable("Malformed or non-positive EOD row") from None
        bars.append(b)
    bars.sort(key=lambda x: x.day)
    if len(bars) < 201:
        raise FreeMarketFeedUnavailable("Need 201 completed sessions")
    if any(x.day >= y.day for x,y in zip(bars,bars[1:])):
        raise FreeMarketFeedUnavailable("Duplicate or invalid trading days")
    if not (0 < (as_of-bars[-1].day).days <= 7):
        raise FreeMarketFeedUnavailable("Data incomplete, stale or from future")
    return FreeMarketHistory(ticker, "USD", "Massive US Stocks Basic EOD",
                             "SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED",
                             tuple(bars))


def fetch_massive_us_daily(symbol: str, *, api_key: str | None = None,
                           as_of: date | None = None) -> FreeMarketHistory:
    """GET with Authorization header, never put a secret in URL/logs."""
    key = api_key if api_key is not None else os.getenv("MASSIVE_API_KEY", "")
    key = key.strip()
    if not key:
        raise FreeMarketFeedUnavailable("MASSIVE_API_KEY not configured")
    if not _SYMBOL.fullmatch(symbol):
        raise FreeMarketFeedUnavailable("Unsupported stock symbol")
    now = as_of or datetime.now(timezone.utc).date()
    start = now - timedelta(days=540)
    end = now - timedelta(days=1)
    path = ("/v2/aggs/ticker/"+urllib.parse.quote(symbol)+"/range/1/day/"
            +start.isoformat()+"/"+end.isoformat())
    q = urllib.parse.urlencode({"adjusted":"true","sort":"asc","limit":"50000"})
    req = urllib.request.Request(HOST+path+"?"+q,headers={
        "Authorization": "Bearer "+key,
        "Accept": "application/json",
        "User-Agent": "SwingBotPrivateResearch/0.1"
    },method="GET")
    try:
        with urllib.request.urlopen(req,timeout=22) as response:
            raw=response.read(1_500_001)
            if len(raw)>1_500_000:
                raise FreeMarketFeedUnavailable("EOD payload too large")
        payload=json.loads(raw)
    except urllib.error.HTTPError as exc:
        # Provider errors may embed keys in URLs; discard all exception detail.
        raise FreeMarketFeedUnavailable(
            "Massive EOD request rejected (HTTP "+str(int(exc.code))+")"
        ) from None
    except (urllib.error.URLError,TimeoutError,ValueError,UnicodeError) as exc:
        raise FreeMarketFeedUnavailable("Massive EOD unavailable") from None
    return parse_massive_daily(payload,ticker=symbol,as_of=now)


def private_us_research_score(feed: FreeMarketHistory, *, as_of: date) -> dict:
    """Technical momentum rank; USD watchlist only, never an order signal."""
    h=feed.bars
    if feed.currency!="USD" or len(h)<201 or h[-1].day>=as_of:
        raise FreeMarketFeedUnavailable("US research history invalid")
    if (as_of-h[-1].day).days>7:
        raise FreeMarketFeedUnavailable("US research history stale")
    close=h[-1].close
    sma50=mean(x.close for x in h[-50:])
    sma200=mean(x.close for x in h[-200:])
    m60=close/h[-61].close-1
    breakout=close>max(x.high for x in h[-21:-1])
    turnover=median(x.close*x.volume for x in h[-20:])
    trs=[]
    for i in range(len(h)-14,len(h)):
        cur,prev=h[i],h[i-1]
        trs.append(max(cur.high-cur.low,abs(cur.high-prev.close),
                       abs(cur.low-prev.close)))
    atr_pct=mean(trs)/close
    trend=close>sma50>sma200
    liquid=turnover>=5_000_000
    points=(35 if trend else 0)+(25 if breakout else 0) + (
        20 if .05<=m60<=.50 else 0) + (
        10 if .012<=atr_pct<=.08 else 0) + (10 if liquid else 0)
    return {
        "symbol":feed.ticker, "currency":"USD", "date":h[-1].day.isoformat(),
        "score":points, "max_score":100,
        "momentum_60d_pct":round(m60*100,2),
        "atr_14d_pct":round(atr_pct*100,2),
        "breakout_20d":breakout, "trend_50_above_200":trend,
        "median_usd_turnover_20d":round(turnover,2),
        "liquidity_gate_ok":liquid,
        "research_status":"WATCHLIST_ONLY_NO_BROKER_OR_FX_VERIFICATION",
        "source_adjustment":feed.adjustment,
        "broker_available_verified":False, "fx_verified":False,
        "spread_verified":False, "paper_trade_authorized":False,
        "real_order_authorized":False,
    }


def check_free_feed(*, api_key: str | None = None,
                    today: date | None = None,
                    sleep: Callable[[float], None] = time.sleep,
                    symbols: tuple[str, ...] = WATCHLIST_USD) -> dict:
    """Check curated 8-share watchlist with 13s pacing; no public symbol results."""
    key=api_key if api_key is not None else os.getenv("MASSIVE_API_KEY","")
    if not key.strip():
        return {"status":"AWAITING_MASSIVE_FREE_API_KEY",
                "attempted":0,"validated":0,"failed":0,
                "raw_data_published":False,"trades_enabled":False}
    now=today or datetime.now(timezone.utc).date()
    checked=0
    valid=0
    missing=0
    for i, symbol in enumerate(symbols):
        if i:
            sleep(MIN_CALL_GAP_SEC)
        checked+=1
        try:
            feed=fetch_massive_us_daily(symbol,api_key=key,as_of=now)
            if feed.ticker != symbol:
                raise FreeMarketFeedUnavailable("Price response mismatch")
            _=private_us_research_score(feed,as_of=now)
            valid+=1
        except FreeMarketFeedUnavailable:
            missing+=1
    return {
        "status":"USD_RESEARCH_FEED_TESTED" if valid else "PRICE_FEED_NOT_READY",
        "attempted":checked, "validated":valid, "failed":missing,
        "private_price_history_published":False,
        "broker_membership_verified":False,
        "real_time":False,
        "trades_enabled":False,
    }


def main() -> None:
    # Deliberately only aggregate readiness to public GitHub Actions logs.
    report=check_free_feed()
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
