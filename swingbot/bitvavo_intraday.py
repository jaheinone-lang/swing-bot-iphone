"""Read-only completed Bitvavo intraday candle retrieval.

5m candles only; currently unfinished UTC interval is ALWAYS removed.
No API secrets, no live orders. Bitvavo endpoint supports capped history;
never claim this provides a multi-year minute backtest.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from .market_data import MarketDataError, _request_text

SYMBOLS = frozenset(("BTC-EUR","ETH-EUR","SOL-EUR"))


def intraday_candles(pair: str, *, interval: str = "5m",
                     limit: int = 1000, now: datetime | None = None) -> list[dict]:
    if pair not in SYMBOLS or interval not in ("1m","5m"):
        raise ValueError("Only listed EUR crypto pairs and 1m/5m intervals")
    if not (30 <= limit <= 1000):
        raise ValueError("Limit must be between 30 and 1000")
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Timezone-aware UTC time required")
    clock=clock.astimezone(timezone.utc)
    length = 60 if interval == "1m" else 300
    cutoff = int(clock.timestamp()) // length * length
    url="https://api.bitvavo.com/v2/"+pair+"/candles?"+urlencode({
        "interval":interval,"limit":limit})
    try:
        rows=json.loads(_request_text(url))
        if not isinstance(rows,list):
            raise ValueError("Candle response must be an array")
        bars=[]
        for row in rows:
            timestamp_ms=int(row[0])
            ts=timestamp_ms//1000
            op, hi, lo, cl=map(float,row[1:5])
            volume=float(row[5])
            if not (volume >= 0 and volume < float("inf")):
                raise ValueError("Invalid volume")
            if not (0 < lo <= min(op,cl) <= max(op,cl) <= hi):
                raise ValueError("Invalid OHLC")
            if ts >= cutoff:
                continue
            if ts % length:
                raise ValueError("Misaligned exchange candle start")
            bars.append({"timestamp_ms":timestamp_ms, "open":op,"high":hi,
                         "low":lo,"close":cl,"volume":volume})
        bars.sort(key=lambda b:b["timestamp_ms"])
        if len(bars)<30 or any(a["timestamp_ms"]>=b["timestamp_ms"]
                              for a,b in zip(bars,bars[1:])):
            raise ValueError("Insufficient or duplicate completed candles")
        if any((b["timestamp_ms"]-a["timestamp_ms"])!=length*1000
               for a,b in zip(bars,bars[1:])):
            raise ValueError("Missing intraday candles; refuse to impute")
        return bars
    except (IndexError,TypeError,ValueError,OverflowError) as exc:
        raise MarketDataError("Invalid, partial or gapped Bitvavo intraday data") from exc
