"""PIT technical/fundamental watchlist scoring for share/ETF candidates.

Research-only: does not fetch entire broker market data. Requires >=201
completed OHLCV rows from a trusted/licensed, adjusted EUR-quote feed.
Earnings-surprise signals require a *separately validated* expectations source,
which is not currently configured. Financial quality data is not fabricated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from statistics import mean, median


@dataclass(frozen=True)
class DailyBar:
    day:date
    open:float
    high:float
    low:float
    close:float
    volume:float

    def __post_init__(self):
        if not all(isfinite(x) and x>0 for x in
                   (self.open,self.high,self.low,self.close,self.volume)):
            raise ValueError("Invalid price/volume values")
        if self.low>min(self.open,self.close) or self.high<max(self.open,self.close):
            raise ValueError("OHLC inconsistency")


def _atr(candles:list[DailyBar],count:int=14)->float:
    if len(candles)<count+1:
        raise ValueError("Not enough ATR candles")
    values=[]
    for i in range(len(candles)-count,len(candles)):
        b,p=candles[i],candles[i-1]
        values.append(max(b.high-b.low,abs(b.high-p.close),abs(b.low-p.close)))
    return mean(values)


def screen_equity(ticker:str,asset_type:str,currency:str,
                  candles:list[DailyBar], *, as_of:date,
                  adjusted_for_corporate_actions:bool,
                  verified_spread_bps:float|None,
                  sec_fundamentals:dict|None=None) -> dict:
    """Point-in-time score. Do not conflate ticker with CIK/ISIN."""
    result={
        "symbol":ticker,"asset_type":asset_type,"status":"REJECTED",
        "signal":"NO_DATA","points":None,
        "reason":"Insufficient validated feed; research only",
        "paper_trade_authorized":False,
        "live_order_authorized":False,
        "source_quality":"REQUIRED",
    }
    if asset_type not in ("STOCK","ETF") or currency!="EUR":
        result["reason"]="EUR-listed physical STOCK/ETF only; verify FX separately"
        return result
    if not adjusted_for_corporate_actions:
        result["reason"]="Need split-adjusted corporate actions to avoid false momentum"
        return result
    if verified_spread_bps is None or not isfinite(verified_spread_bps):
        result["reason"]="Missing contemporaneous observed bid/ask spread"
        return result
    if verified_spread_bps<0 or verified_spread_bps>40:
        result["reason"]="Too wide a verified trading spread (> 0.40%)"
        return result
    if len(candles)<201 or candles[-1].day>=as_of:
        result["reason"]="Need >=201 completed sessions strictly before as_of"
        return result
    if any(a.day>=b.day for a,b in zip(candles,candles[1:])):
        result["reason"]="Price dates invalid or duplicated"
        return result
    latest=candles[-1]
    if (as_of-latest.day).days>7:
        result["reason"]="Feed stale"
        return result
    avg20_turnover=median(b.close*b.volume for b in candles[-20:])
    if avg20_turnover<2_000_000:
        result["reason"]="Below EUR 2m median 20-day daily turnover"
        return result
    close=latest.close
    trend50=mean(x.close for x in candles[-50:])
    trend200=mean(x.close for x in candles[-200:])
    prior_high20=max(x.high for x in candles[-21:-1])
    momentum60=close/candles[-61].close-1
    atrp=_atr(candles)/close
    breakout=close>prior_high20
    moving=trend50>trend200 and close>trend50
    if atrp>.12:
        result["reason"]="Excessive 14-bar ATR (>12% of price)"
        return result
    if momentum60>.75:
        result["reason"]="60-day momentum >75%; chase-risk review required"
        return result
    points=0
    points+=25 if moving else 0
    points+=20 if breakout else 0
    points+=15 if .05<=momentum60<=.5 else 0
    points+=15 if 0.012<=atrp<=.07 else 0
    points+=10 if verified_spread_bps<=10 else 0
    points+=10 if avg20_turnover>=10_000_000 else 0
    fundamental_status="NO_VERIFIED_FUNDAMENTALS"
    # ETF holdings/methodology require different, fund-specific research.
    if asset_type=="STOCK" and sec_fundamentals:
        fundamental_status=sec_fundamentals.get("fundamentals_status","INSUFFICIENT")
        if fundamental_status=="PARTIAL":
            reported_as_of=date.fromisoformat(sec_fundamentals["as_of"])
            filed=date.fromisoformat(sec_fundamentals["revenue_filed"])
            if reported_as_of>latest.day or filed>latest.day:
                result["reason"]="Fundamental report not yet public by signal day"
                return result
            # Unverified country/CIK mapping means no fundamentals bonus.
            if sec_fundamentals.get("source_url"):
                points+=min(15,max(0,sec_fundamentals.get("points",0)))
    result.update({
        "status":"SCREENED",
        "signal":"RESEARCH_CANDIDATE" if points>=65 and moving and breakout
                  else "WATCH",
        "points":round(points,1),
        "max_points":120,
        "reason":"Point-in-time EUR technical screen; no order permission",
        "source_quality":"OHLCV_ADJUSTED_EUR",
        "fundamental_status":fundamental_status,
        "latest_close_eur":round(close,6),
        "data_day":latest.day.isoformat(),
        "momentum60_pct":round(momentum60*100,2),
        "atr14_pct":round(atrp*100,2),
        "average_daily_turnover_eur":round(avg20_turnover,2),
        "spread_bps":round(verified_spread_bps,2),
        "close_above_50_above_200":moving,
        "twenty_day_high_breakout":breakout,
    })
    return result
