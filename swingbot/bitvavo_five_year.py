"""Bounded public Bitvavo 5m BTC/EUR and ETH/EUR five-calendar-year download.

Pages use up to 1440 completed 5m candles (Bitvavo published API maximum).
Limited concurrency and >=0.20sec shared start spacing avoid public IP bans.
No authenticated calls, no trading, no interpolated candles.
Time window frozen to completed UTC midnights for reproducibility.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from math import isfinite
from threading import Lock
from time import monotonic, sleep
from urllib.parse import urlencode
import json

from .market_data import MarketDataError, _request_text

BAR_MS=300000
PAGE_BARS=1440
# 300 requests/min at most, safely below Bitvavo's default 1000
MIN_SPACING_SECONDS=.20

class PublicPacer:
    def __init__(self,spacing=MIN_SPACING_SECONDS):
        self.spacing=spacing
        self.lock=Lock()
        self.next_start=0.
    def wait(self):
        with self.lock:
            now=monotonic()
            planned=max(now,self.next_start)
            self.next_start=planned+self.spacing
        delay=planned-now
        if delay>0: sleep(delay)


def _five_minute_page(pair,lo,hi,*,fetch=_request_text,pacer=None):
    if pacer is not None: pacer.wait()
    url="https://api.bitvavo.com/v2/"+pair+"/candles?"+urlencode({
        "interval":"5m","start":lo,"end":hi,"limit":PAGE_BARS})
    data=json.loads(fetch(url))
    if not isinstance(data,list):
        raise MarketDataError("Bitvavo did not return historical candle array")
    rows=[]
    for row in data:
        if not isinstance(row,(list,tuple)) or len(row)<6:
            raise MarketDataError("Invalid historical candlestick")
        t=int(row[0])
        op,high,low,close,vol=map(float,row[1:6])
        if (t%BAR_MS!=0 or not lo<=t<hi
            or not all(isfinite(v) for v in (op,high,low,close,vol))
            or not (0<low<=min(op,close)<=max(op,close)<=high)
            or vol<0):
            raise MarketDataError("Invalid market data, range or OHLCV")
        rows.append({"timestamp_ms":t,"open":op,"high":high,"low":low,
                     "close":close,"volume":vol})
    return rows


def five_year_history(*,start=datetime(2021,10,23,tzinfo=timezone.utc),
                       end=datetime(2026,10,23,tzinfo=timezone.utc),
                       pairs=("BTC-EUR","ETH-EUR"),
                       max_workers=5, fetch=_request_text,
                       pacer=None):
    """Retrieve exact 5-year UTC window. Retry transient request errors.

    Fail closed on unrecoverable data/provider failure. Never substitute
    other exchanges or timeframes, silently zero-fill or compress holes.
    """
    if (not (start.tzinfo and end.tzinfo) or end<=start
        or (end-start).days>1830
        or start.timestamp()*1000%BAR_MS
        or end.timestamp()*1000%BAR_MS):
        raise ValueError("Provide completed aligned <=5 year UTC window")
    if set(pairs)!={"BTC-EUR","ETH-EUR"}:
        raise ValueError("Exactly BTC-EUR and ETH-EUR, no fiat substitution")
    if not 1<=max_workers<=7:
        raise ValueError("Bound thread count to max 7")
    lo=int(start.timestamp()*1000)
    hi=int(end.timestamp()*1000)
    jobs=[(pair,x,min(hi,x+PAGE_BARS*BAR_MS))
          for pair in pairs for x in range(lo,hi,PAGE_BARS*BAR_MS)]
    pacer=pacer if pacer is not None else PublicPacer()
    def job(args):
        pair,a,b=args
        # Retry on short-lived exchange/network disruptions. An HTTP 429
        # block must never trigger a retry storm: caller gets a hard error.
        last=None
        for attempt in range(3):
            try:
                return pair,_five_minute_page(
                    pair,a,b,fetch=fetch,pacer=pacer)
            except MarketDataError as exc:
                last=exc
                if "HTTPError" in str(exc):
                    # _request_text masks detailed status; fail closed
                    # rather than accidentally retrying an exchange ban.
                    raise
                if attempt < 2:sleep((attempt+1)*1.5)
        raise MarketDataError("Public OHLC download failed after 3 attempts") from last

    joined={p:[] for p in pairs}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        tasks=[pool.submit(job,j) for j in jobs]
        for fut in as_completed(tasks):
            pair,rows=fut.result()
            joined[pair].extend(rows)
    count=(hi-lo)//BAR_MS
    report={}
    for pair,rows in joined.items():
        rows.sort(key=lambda x:x["timestamp_ms"])
        ts=[x["timestamp_ms"] for x in rows]
        if len(set(ts))!=len(ts):
            raise MarketDataError("Duplicate historical timestamps")
        report[pair]={
            "expected":count,
            "observed":len(ts),
            "missing":count-len(ts),
            "coverage_pct":round(len(ts)/count*100,3),
            "earliest":ts[0] if ts else None,
            "latest":ts[-1] if ts else None}
        if len(ts)<365*288:
            raise MarketDataError(
                f"Insufficient real historical data for five-year evaluation: {pair}")
    return joined,{
        "requested_start_utc":start.isoformat(),
        "requested_end_utc_exclusive":end.isoformat(),
        "expected_bars_per_pair":count,
        "page_count":len(jobs),
        "per_pair":report,
        "public_read_only":True,
        "zero_filled":False,
    }
