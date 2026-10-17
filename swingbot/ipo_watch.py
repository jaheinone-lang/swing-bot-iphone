"""New listing / IPO research scanner: NO instant first-day buys.

IPO event date MUST come from an exchange/issuer filing, not from broker
'addedOn'. Native-currency OHLCV only; FX conversion must be validated
before EUR-paper execution. No trading endpoint exists in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from statistics import median


@dataclass(frozen=True)
class IpoBar:
    day:date
    open:float
    high:float
    low:float
    close:float
    volume:float

    def __post_init__(self):
        if (not all(isfinite(x) and x>0 for x in
                    (self.open,self.high,self.low,self.close,self.volume))
                or not self.low<=min(self.open,self.close)
                or not self.high>=max(self.open,self.close)):
            raise ValueError("Invalid OHLCV IPO bar")


def ipo_setup(*, ticker:str, confirmed_exchange_debut:date|None,
              candles:list[IpoBar],currency:str,
              verified_listing_source:str|None,
              broker_available:bool=False,
              spread_bps:float|None=None,
              fx_conversion_verified:bool=False,
              daily_dollar_volume_threshold:float=5_000_000.0)->dict:
    """Signal is deliberately a watchlist only, never automatic BUY."""
    result={
        "ticker":ticker,"mode":"IPO_WATCH_ONLY","signal":"NO_DATA",
        "eligible_for_real_orders":False,
        "reason":"no confirmed listing / data",
    }
    if (not confirmed_exchange_debut or not verified_listing_source
            or not verified_listing_source.startswith("https://")):
        return result
    if not isinstance(currency,str) or currency not in ("USD","EUR","GBP"):
        return result
    bars=sorted([b for b in candles if b.day>=confirmed_exchange_debut],
                key=lambda b:b.day)
    if len({b.day for b in bars})!=len(bars):
        result["reason"]="Duplicate trading dates"
        return result
    if len(bars)<6:
        result.update(signal="WAIT_5_DAYS",reason="Observe five complete trading sessions")
        return result
    if len(bars)>30:
        result.update(signal="OLD_LISTING",reason="IPO watch window has ended")
        return result
    first_five_high=max(b.high for b in bars[:5])
    last=bars[-1]
    result.update({
        "days_traded":len(bars),
        "first_five_high":round(first_five_high,6),
        "last_close":round(last.close,6),
        "last_day":last.day.isoformat(),
        "quote_currency":currency,
        "listing_source":verified_listing_source,
    })
    if spread_bps is None or not isfinite(spread_bps):
        result.update(signal="NO_SPREAD",reason="Measured live bid/ask spread missing")
        return result
    if spread_bps<0 or spread_bps>40:
        result.update(signal="SKIP_SPREAD",reason="Spread exceeds 0.40% cutoff")
        return result
    if currency!="EUR" and not fx_conversion_verified:
        result.update(signal="NEEDS_FX",reason="Validate EUR FX conversion for paper account")
        return result
    if not broker_available:
        result.update(signal="NOT_AT_BROKER",reason="Listing absent from verified Trading 212 metadata")
        return result
    previous=bars[-6:-1]
    normal_volume=median(b.volume for b in previous)
    dollar_volume=last.close*last.volume
    if dollar_volume<daily_dollar_volume_threshold:
        result.update(signal="SKIP_LIQUIDITY",reason="Below native USD/EUR/GBP turnover threshold")
        return result
    if last.open>previous[-1].close*1.12:
        result.update(signal="SKIP_GAP",reason="Opening gap exceeds 12%: do not chase")
        return result
    # Can trade only after the completed close above first 5-session high;
    # this 'breakout' is an observation, not a retrospective fill.
    if last.close<=first_five_high:
        result.update(signal="WATCH",reason="No confirmed opening-range breakout")
        return result
    if last.volume<1.20*normal_volume:
        result.update(signal="WATCH",reason="Breakout has insufficient relative volume")
        return result
    result.update(signal="IPO_BREAKOUT_WATCH",
                  reason="5-day range broken with volume and liquidity; manual risk review")
    return result
