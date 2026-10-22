"""Historical 5m Bitvavo pagination with strict no-imputation validation.

Bounded by calendar time, 1,000 candles per request (public GET only).
The API documents start/end UTC milliseconds; missing trade periods make gaps,
which are reported instead of being silently forward-filled.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from urllib.parse import urlencode

from .bitvavo_intraday import SYMBOLS
from .market_data import MarketDataError, _request_text

BAR_MS=300000
MAX_BARS=1000

def _rows(pair, start_ms, end_ms):
    url="https://api.bitvavo.com/v2/"+pair+"/candles?"+urlencode({
        "interval":"5m","start":start_ms,"end":end_ms,"limit":MAX_BARS})
    payload=json.loads(_request_text(url))
    if not isinstance(payload,list):
        raise MarketDataError("Expected array of OHLCV rows")
    result=[]
    for row in payload:
        if not isinstance(row,(list,tuple)) or len(row)<6:
            raise MarketDataError("Malformed OHLCV bar")
        ms=int(row[0])
        op,hi,lo,cl,vol=map(float,row[1:6])
        if (ms%BAR_MS or ms<start_ms or ms>=end_ms
                or not all(isfinite(v) for v in (op,hi,lo,cl,vol))
                or not 0<lo<=min(op,cl)<=max(op,cl)<=hi or vol<0):
            raise MarketDataError("Timestamp/price/volume outside request interval")
        result.append({"timestamp_ms":ms,"open":op,"high":hi,"low":lo,
                       "close":cl,"volume":vol})
    return result

def historical_five_minute(pair, *, days=30, now=None):
    if pair not in SYMBOLS:
        raise ValueError("Unsupported market")
    if not isinstance(days,int) or not 7<=days<=90:
        raise ValueError("Historical span must be 7..90 days")
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Timezone aware clock required")
    end_ms=int(clock.astimezone(timezone.utc).timestamp()*1000)//BAR_MS*BAR_MS
    count=days*24*12
    start_ms=end_ms-count*BAR_MS
    bars=[]
    for left in range(start_ms,end_ms,MAX_BARS*BAR_MS):
        right=min(end_ms,left+MAX_BARS*BAR_MS)
        part=_rows(pair,left,right)
        bars.extend(part)
    bars.sort(key=lambda b:b["timestamp_ms"])
    observed=[b["timestamp_ms"] for b in bars]
    expected=list(range(start_ms,end_ms,BAR_MS))
    if observed!=expected:
        missing=len(set(expected)-set(observed))
        duplicate=len(observed)-len(set(observed))
        raise MarketDataError(
            f"Historical coverage incomplete: expected {count}, got "
            f"{len(bars)}; missing={missing}, duplicate={duplicate}; no fill")
    return bars
