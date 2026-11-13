"""Literature-inspired USD equity pattern hypotheses: event studies, NOT orders.

Three distinct PREDECLARED, daily-data proxies:
  52W_HIGH: George & Hwang (2004), price near trailing 252-session high
  LEADER_BASE_BREAK: Kullamägi (2021) leading advance, contracting base, break
  GAP_VOLUME_PROXY: Kullamägi episodic pivot *proxy*; NOT earnings verified.

Primary original: https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/
Academic source: https://doi.org/10.1111/j.1540-6261.2004.00695.x

Episodic pivots normally require earnings/catalyst context and intraday
opening-range entries. We have only completed daily bars, so the proxy
MUST NEVER be marketed as identical to the original strategy.

For each signal known only after today's close, buy at next SESSION'S open,
and hypothetically sell at a later session OPEN. Charge fixed fees and
slippage on BOTH sides. No stop/limit execution is claimed. Compare signal
returns with SPY next-open to later-open returns over exact same dates,
when a separately verified SIP ETF bar series was supplied.

Returns for individual events are NOT a self-financing, executable
portfolio. Samples overlap across tickers, survivorship bias is severe,
SPY prices omit dividends, and any pre-2026-11-13 results are exploratory
AFTER these rules were inspired by observing earlier A/B/C failures.
No trading permissions, provider data redistribution or promised profits.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from math import isfinite
from statistics import mean, median
from typing import Mapping

from .equity_screen import DailyBar
from .massive_free import FreeMarketHistory

SYNTHETIC = "SYNTHETIC_TEST_FIXTURE"
SIP = "ALPACA_DELAYED_SIP_CONSOLIDATED_HISTORICAL"
PATTERNS = ("52W_HIGH","LEADER_BASE_BREAK","GAP_VOLUME_PROXY")
HORIZONS = (5,20)
LOOKBACK = 252
COOLDOWN = 20
BASE_FEES_BPS = 10.0
BASE_SLIPPAGE_BPS = 10.0
MIN_EVENT_SAMPLE = 30
MIN_TURNOVER_USD = 5_000_000.0


def _validate(feed: FreeMarketHistory, *, as_of: date,
              source: str) -> tuple[DailyBar,...]:
    if (not isinstance(feed,FreeMarketHistory) or
            feed.source!=source or feed.currency!="USD" or
            feed.adjustment!="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED" or
            feed.paper_trade_authorized or feed.broker_available_verified or
            feed.fx_verified or feed.spread_verified):
        raise ValueError("Invalid price data provenance or trade authorizations")
    bars=tuple(b for b in feed.bars if b.day<as_of)
    if len(bars)<LOOKBACK+1+max(HORIZONS)+1:
        raise ValueError("Need 252 lookback observations and future exits")
    if any(not isinstance(b,DailyBar) for b in bars):
        raise ValueError("Unrecognized daily price")
    if any(a.day>=b.day for a,b in zip(bars,bars[1:])):
        raise ValueError("OHLCV dates duplicated or unsorted")
    if not 1<=(as_of-bars[-1].day).days<=7:
        raise ValueError("Historical input stale or future dated")
    if not all(isfinite(v) and v>0 for bar in bars
               for v in (bar.open,bar.high,bar.low,bar.close,bar.volume)):
        raise ValueError("Bad historical OHLCV")
    return bars


def pattern_flags(bars: tuple[DailyBar,...], i: int) -> dict[str,bool]:
    """Decision after close at index i, *never* uses bars after i."""
    if i<LOOKBACK or i>=len(bars):
        raise ValueError("Pattern decision needs 252 completed observations")
    day=bars[i]
    p20=bars[i-20:i]
    # Both recent dollar turnover and volume comparisons use ONLY historical
    # completed observations. Current-day OHLCV is known after its close.
    liquid=mean(x.close*x.volume for x in p20)>=MIN_TURNOVER_USD
    ma50=mean(x.close for x in bars[i-49:i+1])
    ma200=mean(x.close for x in bars[i-199:i+1])
    prior_high_52w=max(x.high for x in bars[i-251:i+1])
    near_high=(
        liquid
        and day.close>=.98*prior_high_52w
        and day.close>ma50>ma200
        and day.close/bars[i-63].close>=1.10
    )
    base=bars[i-15:i]  # excludes today's breakout candle
    prior_impulse=bars[i-15].close/bars[i-75].close
    base_width=max(x.high for x in base)/min(x.low for x in base)
    base_early=mean((x.high-x.low)/x.close for x in base[:10])
    base_late=mean((x.high-x.low)/x.close for x in base[-5:])
    range_pos=(day.close-day.low)/(day.high-day.low) if day.high>day.low else 0.
    breakout=(
        liquid and prior_impulse>=1.25 and base_width<=1.20
        and base_late<=base_early*1.15
        and day.close>max(x.high for x in base)
        and day.volume>=1.5*mean(x.volume for x in p20)
        and day.close>=day.open and range_pos>=.70
    )
    # Opening gap + high volume approximates possible episodic pivots,
    # but we DO NOT have verified earnings/news or opening-range data.
    gap_proxy=(
        liquid and day.open>=1.10*bars[i-1].close
        and day.volume>=2.*mean(x.volume for x in p20)
        and day.close>=day.open and range_pos>=.70
    )
    return dict(zip(PATTERNS,(near_high,breakout,gap_proxy)))


def net_open_to_open_return(entry:float,exit:float, *,
                            fees_bps:float=BASE_FEES_BPS,
                            slippage_bps:float=BASE_SLIPPAGE_BPS) -> float:
    if (not all(isinstance(v,(float,int)) and isfinite(v)
                for v in (entry,exit,fees_bps,slippage_bps))
            or min(entry,exit)<=0 or not 0<=fees_bps<=500
            or not 0<=slippage_bps<=500):
        raise ValueError("Invalid entry/exit or transaction cost")
    # Proceeds net of sell friction / acquisition grossed by buy friction
    buy=entry*(1+(fees_bps+slippage_bps)/10000)
    sell=exit*(1-(fees_bps+slippage_bps)/10000)
    return 100*(sell/buy-1)


def study_pattern_events(histories: Mapping[str,FreeMarketHistory], *,
                         as_of:date, licensed_non_display_use:bool=False,
                         benchmark:FreeMarketHistory|None=None) -> dict:
    """No signal optimization, lookahead, orders or annual-return claims."""
    if (not isinstance(as_of,date) or not histories or
            len(histories)>500 or not isinstance(licensed_non_display_use,bool)):
        raise ValueError("Invalid study request")
    sources={h.source for h in histories.values()
             if isinstance(h,FreeMarketHistory)}
    if len(sources)!=1 or len(sources)!=len({
        SYNTHETIC if not licensed_non_display_use else SIP
    }):
        raise PermissionError("Synthetic-only by default, SIP only when approved")
    source=next(iter(sources))
    if source!=(SIP if licensed_non_display_use else SYNTHETIC):
        raise PermissionError("Unlicensed or mixed price histories")
    if any(not isinstance(k,str) or not k for k in histories):
        raise ValueError("Invalid symbol")
    if benchmark is not None:
        if benchmark.ticker in histories or benchmark.ticker!="SPY":
            raise ValueError("Independent SPY benchmark series required")
        b_rows=_validate(benchmark,as_of=as_of,source=source)
        b_days={b.day:b.open for b in b_rows}
    else:
        b_days={}

    event_returns=defaultdict(list)
    benchmark_returns=defaultdict(list)
    events_by_year=defaultdict(Counter)
    symbols_with_events=defaultdict(set)
    unmatched=defaultdict(int)
    data_start=None
    data_end=None
    signal_dates=[]
    for ticker,feed in sorted(histories.items()):
        if feed.ticker!=ticker:
            raise ValueError("Ticker mismatched its source")
        bars=_validate(feed,as_of=as_of,source=source)
        data_start=min(data_start,bars[0].day) if data_start else bars[0].day
        data_end=max(data_end,bars[-1].day) if data_end else bars[-1].day
        last={name:-100_000 for name in PATTERNS}
        # Max forward horizon has been completed; no final-day hindsight.
        for i in range(LOOKBACK,len(bars)-max(HORIZONS)-1):
            signal=pattern_flags(bars,i)
            for name in PATTERNS:
                if not signal[name] or i-last[name]<COOLDOWN:
                    continue
                last[name]=i
                signals_key=(name,bars[i].day.year)
                events_by_year[name][bars[i].day.year]+=1
                symbols_with_events[name].add(ticker)
                # Stock must be entered at tomorrow's open, NEVER at
                # today's close after observing today's price/volume.
                for horizon in HORIZONS:
                    day_in=bars[i+1].day
                    day_out=bars[i+1+horizon].day
                    gross=net_open_to_open_return(
                        bars[i+1].open,bars[i+1+horizon].open
                    )
                    key=(name,horizon)
                    event_returns[key].append(gross)
                    if day_in in b_days and day_out in b_days:
                        spy=net_open_to_open_return(
                            b_days[day_in],b_days[day_out]
                        )
                        # Paired comparison, strictly matching entry/exit
                        # session dates for stock and SPY.
                        benchmark_returns[key].append((gross,spy))
                    else:
                        unmatched[key]+=1

    reports=[]
    for name in PATTERNS:
        horizons=[]
        for horizon in HORIZONS:
            key=(name,horizon)
            values=event_returns[key]
            matched=benchmark_returns[key]
            count=len(values)
            mean_stock=round(mean(values),3) if values else None
            mean_spy=round(mean(p[1] for p in matched),3) if matched else None
            mean_excess=round(mean(a-b for a,b in matched),3) if matched else None
            horizons.append({
                "holding_sessions":horizon,
                "events":count,
                "mean_net_event_return_pct":mean_stock,
                "median_net_event_return_pct":(
                    round(median(values),3) if values else None
                ),
                "positive_net_events_pct":(
                    round(100*sum(v>0 for v in values)/count,2)
                    if values else None
                ),
                "matched_spy_event_count":len(matched),
                "mean_spy_matched_return_pct":mean_spy,
                "mean_stock_excess_over_spy_pct_points":mean_excess,
                "unmatched_spy_events":unmatched[key],
                "evidence_insufficient_if_fewer_than_30_events":
                    count<MIN_EVENT_SAMPLE,
            })
        reports.append({
            "pattern":name,
            "signal_events":sum(events_by_year[name].values()),
            "distinct_tickers":len(symbols_with_events[name]),
            "events_by_calendar_year":dict(sorted(events_by_year[name].items())),
            "horizons":horizons,
        })
    return {
        "status":"EXPLORATORY_PRICE_PATTERN_EVENT_STUDY",
        "source":"ALPACA_DELAYED_SIP" if source==SIP else SYNTHETIC,
        "as_of":as_of.isoformat(),
        "data_first_date":data_start.isoformat(),
        "data_last_date":data_end.isoformat(),
        "stocks_analyzed":len(histories),
        "patterns":reports,
        "event_holding_periods_sessions":list(HORIZONS),
        "friction_per_side_fee_bps":BASE_FEES_BPS,
        "friction_per_side_slippage_bps":BASE_SLIPPAGE_BPS,
        "signal_after_day_close_entry_next_open":True,
        "no_intraday_episodic_pivot_or_earnings_confirmation":True,
        "event_returns_not_compounded_portfolio":True,
        "historical_results_not_independent_forward_validation":True,
        "lookahead_survivorship_and_issuer_mapping_not_proven_clean":True,
        "annual_100pct_cagr_goal_proven":False,
        "historical_alpha_proven":False,
        "stock_symbols_or_prices_published":False,
        "paper_orders_enabled":False,
        "real_orders_enabled":False,
    }
