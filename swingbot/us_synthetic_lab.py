"""Pure offline, non-executable USD research lab for the curated US watchlist.

This module does NOT call Massive or Trading 212. By default only synthetic
test fixtures are permitted. Live licensed non-display data can be injected
only with explicit license confirmation. Nothing here enters the EUR portfolio.

Chronology: signals use yesterday's completed close, orders fill next open.
Stop fills may gap past the stop; trading frictions apply to both directions.
Train and holdout are separately restarted USD research simulations, and
all variants are frozen BEFORE looking at holdout outcomes. No tax model is
claimed for the USD simulations. No future prices enter an earlier signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import floor, isfinite
from statistics import mean
from typing import Mapping

from .massive_free import FreeMarketHistory
from .us_watchlist import US_WATCHLIST_50

START_USD = 5000.0
RISK_PER_POSITION = 0.01
MAX_POSITION = 0.20
DRAWDOWN_CIRCUIT = 0.25
FEE_BPS = 10.0
SLIPPAGE_BPS = 10.0
MAX_POSITIONS = 5
WARMUP = 210

@dataclass(frozen=True)
class Strategy:
    name: str
    breakout: int
    trend: int
    stop_atr: float
    max_bars: int | None
    sma200: bool

SPECS = (
    Strategy("A – perus", 20, 50, 2.0, None, False),
    Strategy("B – trendi", 15, 50, 2.5, 25, True),
    Strategy("C – aggressiivinen", 10, 30, 3.0, 18, True),
)


def _atr(rows) -> float:
    tr = []
    for i in range(len(rows)-14, len(rows)):
        b, prev = rows[i], rows[i-1]
        tr.append(max(b.high-b.low, abs(b.high-prev.close),
                      abs(b.low-prev.close)))
    return mean(tr)


def _signal(rows, cfg: Strategy):
    if len(rows) < WARMUP:
        return None
    last = rows[-1].close
    if last <= max(b.high for b in rows[-cfg.breakout-1:-1]):
        return None
    if last <= mean(x.close for x in rows[-cfg.trend:]):
        return None
    if cfg.sma200 and last <= mean(x.close for x in rows[-200:]):
        return None
    atr = _atr(rows)
    if atr <= 0 or atr/last > .12:
        return None
    momentum = last/rows[-61].close-1
    if momentum > .75:
        return None
    # Minimal historical turnover assumption; actual spread needs verification.
    turnover = mean(x.close*x.volume for x in rows[-20:])
    if turnover < 5_000_000:
        return None
    return (momentum, atr)


def _prepare(histories: Mapping[str, FreeMarketHistory], *,
             as_of: date, licensed_non_display_use: bool):
    if not histories:
        raise ValueError("At least one input history required")
    if len(histories)>len(US_WATCHLIST_50):
        raise ValueError("Too many tickers")
    if (not licensed_non_display_use and any(
        isinstance(v, FreeMarketHistory)
        and v.source!="SYNTHETIC_TEST_FIXTURE"
        for v in histories.values()
    )):
        raise PermissionError("Non-display investment-strategy data license is not verified")
    rows = {}
    for symbol, h in histories.items():
        if symbol not in US_WATCHLIST_50 or not isinstance(h, FreeMarketHistory):
            raise ValueError("Unknown or invalid watchlist ticker")
        if (h.ticker!=symbol or h.currency!="USD" or
            h.adjustment!="SPLIT_ADJUSTED_NOT_DIVIDEND_ADJUSTED"
            or h.paper_trade_authorized or h.broker_available_verified
            or h.fx_verified or h.spread_verified):
            raise ValueError("Historical source or flags invalid for research")
        selected = tuple(b for b in h.bars if b.day<as_of)
        if len(selected)<WARMUP+50:
            raise ValueError("At least 260 completed sessions required")
        if any(a.day>=b.day for a,b in zip(selected,selected[1:])):
            raise ValueError("Missing ascending chronological order")
        if not all(isfinite(x) and x>0 for b in selected
                   for x in (b.open,b.high,b.low,b.close,b.volume)):
            raise ValueError("Bad historical OHLCV")
        rows[symbol]=selected
    common = sorted(set.intersection(*(set(b.day for b in candles)
                                      for candles in rows.values())))
    if len(common)<WARMUP+50:
        raise ValueError("Insufficient common market calendar")
    # Strict common observations. No filling missing data with imagined bars.
    aligned = {
        symbol: tuple({b.day:b for b in candles}[d] for d in common)
        for symbol,candles in rows.items()
    }
    return common, aligned


def _simulation(aligned, dates, cfg: Strategy, start: int, end: int) -> dict:
    cash=START_USD
    peak=START_USD
    last_equity=START_USD
    positions={}
    trades=0
    fees_paid=0.0
    stop_exits=0
    halted=False
    max_dd=0.0
    equity_curve=[]
    sides = {"BUY": 0, "SELL": 0}
    closed_pnls=[]
    stop_gap_count=0
    exposed_sessions=0
    max_entry_planned_risk_pct=0.0
    max_open_position_count=0

    def exit_at(symbol, raw_price: float, reason: str):
        nonlocal cash, trades, fees_paid, stop_exits, stop_gap_count
        pos=positions.pop(symbol)
        fill=max(0, raw_price*(1-SLIPPAGE_BPS/10_000))
        gross=pos["quantity"]*fill
        fee=gross*FEE_BPS/10_000
        cash+=gross-fee
        closed_pnls.append(gross-fee-pos["entry_cost_including_fee"])
        fees_paid+=fee
        trades+=1
        sides["SELL"]+=1
        if reason=="STOP":
            stop_exits+=1
        if reason=="GAP_STOP":
            stop_exits+=1
            stop_gap_count+=1

    for idx in range(start,end):
        # Open fills occur BEFORE intraday high/low is known. Exits triggered
        # at the PREVIOUS close are filled first at today's open.
        exited_at_open=set()
        for symbol in tuple(positions):
            barseries=aligned[symbol]
            pos=positions[symbol]
            yesterday=barseries[idx-1]
            timed_out=(cfg.max_bars is not None and pos["bars"]>=cfg.max_bars)
            trend_exit=yesterday.close<mean(x.close for x in barseries[idx-cfg.trend:idx])
            if timed_out or trend_exit:
                exit_at(symbol,barseries[idx].open,"TIME_OR_TREND")
                exited_at_open.add(symbol)

        # Critical: if overnight gaps breach -25%, block opening new risk
        # TODAY, not after today's session has already ended.
        open_equity=cash+sum(
            p["quantity"]*aligned[sym][idx].open
            for sym,p in positions.items()
        )
        peak=max(peak,open_equity)
        if peak>0 and 1-open_equity/peak >= DRAWDOWN_CIRCUIT:
            halted=True

        if not halted:
            # Yesterday's closes are all we may use to generate candidate
            # entry signals; cash is taken from today's actual opening fills.
            equity_before=cash+sum(p["quantity"]*aligned[sym][idx-1].close
                                   for sym,p in positions.items())
            candidates=[]
            for symbol, barseries in aligned.items():
                if symbol in positions or symbol in exited_at_open:
                    continue
                sig=_signal(barseries[:idx],cfg)
                if sig:
                    candidates.append((sig[0],symbol,sig[1]))
            candidates.sort(key=lambda item:(-item[0],item[1]))
            for mom,symbol,atr in candidates:
                if len(positions)>=MAX_POSITIONS:
                    break
                today=aligned[symbol][idx]
                price=today.open*(1+SLIPPAGE_BPS/10_000)
                distance=cfg.stop_atr*atr
                if distance<=0 or price<=distance:
                    continue
                quantity=min(
                    floor(equity_before*MAX_POSITION/(price*(1+FEE_BPS/10_000))),
                    floor(equity_before*RISK_PER_POSITION/distance),
                    floor(cash/(price*(1+FEE_BPS/10_000))),
                )
                if quantity < 1:
                    continue
                fee=quantity*price*FEE_BPS/10_000
                max_entry_planned_risk_pct=max(
                    max_entry_planned_risk_pct,
                    100*quantity*distance/max(equity_before,0.01)
                )
                cash-=quantity*price+fee
                fees_paid+=fee
                trades+=1
                sides["BUY"]+=1
                positions[symbol]={
                    "quantity":quantity,"stop":price-distance,"bars":0,
                    "entry_cost_including_fee":quantity*price+fee
                }

        # Only AFTER all opening fills may today's actual low trigger stop
        # exits. Entry-day stops are conservatively handled without
        # knowing the intraday order of high and low.
        for symbol in tuple(positions):
            today=aligned[symbol][idx]
            if today.low<=positions[symbol]["stop"]:
                if today.open<positions[symbol]["stop"]:
                    exit_at(symbol,today.open,"GAP_STOP")
                else:
                    exit_at(symbol,positions[symbol]["stop"],"STOP")
        for symbol,pos in list(positions.items()):
            pos["bars"]+=1
            # Trailing stop computed after the close, never for today's fill.
            barseries=aligned[symbol]
            atr = _atr(barseries[:idx+1])
            pos["stop"]=max(pos["stop"],
                            barseries[idx].close-cfg.stop_atr*atr)
        exposed_sessions += bool(positions)
        max_open_position_count=max(max_open_position_count,len(positions))
        last_equity=cash+sum(p["quantity"]*aligned[s][idx].close
                             for s,p in positions.items())
        peak=max(peak,last_equity)
        dd=1-last_equity/peak if peak else 0
        max_dd=max(max_dd,dd)
        if dd >= DRAWDOWN_CIRCUIT:
            halted=True
        equity_curve.append((dates[idx].isoformat(),round(last_equity,2)))
    winners=[p for p in closed_pnls if p>0]
    losers=[p for p in closed_pnls if p<0]
    profit_factor=(round(sum(winners)/(-sum(losers)),3)
                   if losers else None)
    win_rate=(round(100*len(winners)/len(closed_pnls),2)
              if closed_pnls else None)
    daily_changes=[]
    prev_value=START_USD
    for _,value in equity_curve:
        if prev_value>0:
            daily_changes.append(100*(value/prev_value-1))
        prev_value=value
    return {
        "status":"SYNTHETIC_OR_LICENSED_RESEARCH_ONLY",
        "start": dates[start].isoformat(),
        "end": dates[end-1].isoformat(),
        "starting_usd": START_USD,
        "ending_mark_to_market_usd": round(last_equity,2),
        "return_pct": round(100*(last_equity/START_USD-1),2),
        "max_drawdown_pct": round(100*max_dd,2),
        "estimated_fees_usd": round(fees_paid,2),
        "round_trip_events": trades,  # legacy alias; events are NOT round trips
        "order_event_count":trades,
        "completed_round_trips":len(closed_pnls),
        "winning_closed_trades":len(winners),
        "losing_closed_trades":len(losers),
        "closed_trade_win_rate_pct":win_rate,
        "net_realized_closed_pnl_usd":round(sum(closed_pnls),2),
        "mean_closed_pnl_usd":(round(mean(closed_pnls),2)
                                if closed_pnls else None),
        "closed_trade_profit_factor":profit_factor,
        "worst_closed_trade_usd":(round(min(closed_pnls),2)
                                  if closed_pnls else None),
        "worst_day_pct":(round(min(daily_changes),2)
                         if daily_changes else None),
        "sessions_with_open_position_pct":round(100*exposed_sessions/(end-start),2),
        "maximum_concurrent_positions":max_open_position_count,
        "max_planned_stop_risk_pct_of_equity":round(max_entry_planned_risk_pct,4),
        "buy_events": sides["BUY"], "sell_events": sides["SELL"],
        "stop_exits": stop_exits,
        "overnight_gap_stop_exits":stop_gap_count,
        "open_positions_not_liquidated":len(positions),
        "halted_new_entries":halted,
        "real_order_authorized":False,
        "paper_order_authorized":False,
    }


def compare_abc_offline(
    histories: Mapping[str, FreeMarketHistory], *,
    as_of: date, licensed_non_display_use: bool=False,
) -> dict:
    """Train=first 65% of tradeable calendar, holdout=last 35%.

    Positions/cash are RESET at split: holdout is a new out-of-sample
    hypothetical run. Prior candles may ONLY warm up historical indicators.
    No source is automatically allowed for strategy/non-display research.
    """
    dates,aligned = _prepare(histories,as_of=as_of,
                             licensed_non_display_use=licensed_non_display_use)
    tradable=len(dates)-WARMUP
    split=WARMUP+int(tradable*.65)
    if split-WARMUP<20 or len(dates)-split<15:
        raise ValueError("Too little train/holdout time")
    variants=[]
    for cfg in SPECS:
        training=_simulation(aligned,dates,cfg,WARMUP,split)
        holdout=_simulation(aligned,dates,cfg,split,len(dates))
        variants.append({"strategy":cfg.name,"breakout_days":cfg.breakout,
                         "trend_days":cfg.trend,"stop_atr":cfg.stop_atr,
                         "training":training,"holdout":holdout})
    leader=max(variants,key=lambda v:(
        v["training"]["return_pct"]-
        1.5*v["training"]["max_drawdown_pct"],
        -v["training"]["max_drawdown_pct"],
        v["strategy"]
    ))
    return {
        "mode":"OFFLINE_USD_RESEARCH_NO_LIVE_ORDERS",
        "data_use_rights":("SEPARATE_LICENSE_CONFIRMED" if licensed_non_display_use
                           else "SYNTHETIC_TEST_FIXTURES_ONLY"),
        "symbol_count":len(histories),
        "calendar_sessions":len(dates),
        "training_end":dates[split-1].isoformat(),
        "holdout_start":dates[split].isoformat(),
        "variants":variants,
        "training_selected_strategy":leader["strategy"],
        "selected_holdout":leader["holdout"],
        "fee_bps_each_side":FEE_BPS,
        "slippage_bps_each_side":SLIPPAGE_BPS,
        "risk_per_trade_pct":RISK_PER_POSITION*100,
        "max_position_pct":MAX_POSITION*100,
        "halt_new_entries_at_drawdown_pct":DRAWDOWN_CIRCUIT*100,
        "warning":("USD only; no FX, spread, borrow fees, taxes, dividends "
                   "or trading venue confirmations. Fixed selected watchlist "
                   "has survivorship bias; synthetic tests have NO "
                   "predictive value. Strategy selection based on training ONLY."),
        "eur_paper_modified":False,
        "real_order_authorized":False,
    }
