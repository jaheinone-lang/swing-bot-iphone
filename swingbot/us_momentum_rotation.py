"""Frozen, return-seeking long-only USD stock momentum research variants.

Experimental hypotheses D and E explicitly differ from the legacy A/B/C:
there is NO percentage stop-risk budget, NO fixed 20% position sizing cap,
NO portfolio drawdown circuit and NO leverage. When qualifying signals are
present, the strategy attempts to invest the account equally in the top
3 stocks (D) or the top 1 stock (E); otherwise it holds cash. Full capital
can be lost. All trading is simulated, with no broker APIs.

Only yesterday's completed OHLCV determines today's OPEN rebalance.
Whole-share fills and fee/slippage on buys and sells are modeled; terminal
positions stay marked to market, and no funding, dividends, FX or tax is
assumed. The current 50-name survivor universe still has survivorship bias.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import floor, isfinite
from statistics import mean

from .us_synthetic_lab import START_USD,WARMUP


@dataclass(frozen=True)
class RotationSpec:
    name: str
    momentum_sessions: int
    rebalance_sessions: int
    max_names: int
    minimum_momentum: float
    require_breakout: bool


# Pre-registered before checking the full-year live-data variant returns.
# These are two distinct hypotheses, not an optimized parameter grid.
ROTATION_SPECS=(
    RotationSpec("D – 6kk momentum 3 osaketta",126,21,3,.05,False),
    RotationSpec("E – 3kk breakout 1 osake",63,5,1,.12,True),
)


def _rotation_choices(aligned, *, idx:int, spec:RotationSpec)->list[str]:
    """Use only [:idx] (yesterday and earlier), NEVER today's prices."""
    candidates=[]
    for symbol,series in aligned.items():
        if idx<200 or idx-1-spec.momentum_sessions<0:
            raise ValueError("Indicator warmup not complete")
        prior=series[idx-1]
        old=series[idx-1-spec.momentum_sessions]
        momentum=prior.close/old.close-1
        if momentum<spec.minimum_momentum or not isfinite(momentum):
            continue
        sma200=mean(b.close for b in series[idx-200:idx])
        sma50=mean(b.close for b in series[idx-50:idx])
        if not (prior.close>sma200 and sma50>sma200):
            continue
        turnover=mean(b.close*b.volume for b in series[idx-20:idx])
        if turnover<5_000_000:
            continue
        if spec.require_breakout and prior.close<=max(
            b.high for b in series[idx-21:idx-1]
        ):
            continue
        candidates.append((-momentum,symbol))
    candidates.sort()
    return [symbol for _,symbol in candidates[:spec.max_names]]


def simulate_rotation(aligned, days: list[date], spec:RotationSpec,
                      start:int,end:int, *, fee_bps:float=10.,
                      slippage_bps:float=10.) -> dict:
    """No fixed-% stop. Simulated next-open rotations, cash-only/no leverage."""
    if (not aligned or not days or start<WARMUP
            or end>len(days) or end<=start
            or any(len(bars)!=len(days) for bars in aligned.values())):
        raise ValueError("Bad aligned price calendar or simulation window")
    if (not all(type(x) in (float,int) and isfinite(x) and 0<=x<=500
                for x in (fee_bps,slippage_bps))):
        raise ValueError("Fees and slippage must be finite 0..500 bps")
    if spec not in ROTATION_SPECS:
        raise ValueError("Unregistered momentum strategy variant")
    cash=START_USD
    positions={}
    paid_fees=0.
    buys=sells=rebalance_count=0
    peak=START_USD
    max_dd=0.
    worst_daily=0.
    previous_equity=START_USD
    last_equity=START_USD
    exposed=0

    for idx in range(start,end):
        prices={sym:aligned[sym][idx].open for sym in aligned}
        if (idx-start)%spec.rebalance_sessions==0:
            chosen=_rotation_choices(aligned,idx=idx,spec=spec)
            rebalance_count+=1
            equity_before=cash+sum(qty*prices[s]
                                   for s,qty in positions.items())
            allocation=(equity_before/len(chosen)) if chosen else 0.

            # Sell undesired or overweight holdings at this OPEN, charging
            # transaction costs before using proceeds for any new buys.
            for symbol,qty in tuple(positions.items()):
                target_qty=(floor(allocation/(
                    prices[symbol]*(1+slippage_bps/10000)
                    *(1+fee_bps/10000)))
                    if symbol in chosen else 0)
                sell_qty=max(0,qty-target_qty)
                if sell_qty:
                    gross=sell_qty*prices[symbol]*(1-slippage_bps/10000)
                    fee=gross*fee_bps/10000
                    paid_fees+=fee
                    cash+=gross-fee
                    sells+=1
                    positions[symbol]-=sell_qty
                    if positions[symbol]==0:
                        del positions[symbol]

            for symbol in chosen:
                current=positions.get(symbol,0)
                buyprice=prices[symbol]*(1+slippage_bps/10000)
                unit_cost=buyprice*(1+fee_bps/10000)
                target=floor(allocation/unit_cost)
                available=floor(max(0,cash)/unit_cost)
                qty=max(0,min(target-current,available))
                if qty:
                    gross=qty*buyprice
                    fee=gross*fee_bps/10000
                    paid_fees+=fee
                    cash-=gross+fee
                    buys+=1
                    positions[symbol]=current+qty

        equity=cash+sum(qty*aligned[sym][idx].close
                        for sym,qty in positions.items())
        if not isfinite(equity) or equity<0:
            raise ValueError("Invalid account equity")
        peak=max(peak,equity)
        max_dd=max(max_dd,1-equity/peak if peak>0 else 0)
        if previous_equity>0:
            worst_daily=min(worst_daily,equity/previous_equity-1)
        last_equity=equity
        previous_equity=equity
        exposed+=bool(positions)

    return {
        "strategy":spec.name,
        "start":days[start].isoformat(),
        "end":days[end-1].isoformat(),
        "starting_usd":START_USD,
        "ending_mark_to_market_usd":round(last_equity,2),
        "return_pct":round(100*(last_equity/START_USD-1),2),
        "max_drawdown_pct":round(max_dd*100,2),
        "worst_day_pct":round(worst_daily*100,2),
        "estimated_fees_usd":round(paid_fees,2),
        "buy_events":buys,"sell_events":sells,
        "order_event_count":buys+sells,
        "rebalance_sessions":rebalance_count,
        "sessions_with_open_position_pct":round(100*exposed/(end-start),2),
        "terminal_open_positions":len(positions),
        "long_only_no_leverage":True,
        "fixed_percent_stop_or_drawdown_circuit":False,
        "fractional_shares_assumed":False,
        "broker_orders_enabled":False,
        "paper_orders_enabled":False,
    }
